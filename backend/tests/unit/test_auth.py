import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.services import auth

CREDS = {"email": "Ana@Example.com", "password": "a long password"}


def test_password_hashing() -> None:
    h = auth.hash_password("secret pass")
    assert h.startswith("$argon2id$") and "secret" not in h
    assert auth.verify_password(h, "secret pass")
    assert not auth.verify_password(h, "wrong")
    assert not auth.verify_password(None, "x")


def test_register_login_logout(anon_client: TestClient) -> None:
    res = anon_client.post("/api/auth/register", json=CREDS)
    assert res.status_code == 201
    assert res.json()["email"] == "ana@example.com"
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert anon_client.get("/api/auth/me").status_code == 200

    assert anon_client.post("/api/auth/logout").status_code == 204
    assert anon_client.get("/api/auth/me").status_code == 401

    assert anon_client.post("/api/auth/login", json=CREDS).status_code == 200
    assert anon_client.get("/api/auth/me").json()["settings"]["model_preset"] == "balanced"


def test_register_validation_and_duplicates(anon_client: TestClient) -> None:
    assert (
        anon_client.post("/api/auth/register", json={**CREDS, "password": "short"}).status_code
        == 422
    )
    assert (
        anon_client.post("/api/auth/register", json={**CREDS, "email": "nope"}).status_code == 422
    )
    assert anon_client.post("/api/auth/register", json=CREDS).status_code == 201
    dup = anon_client.post("/api/auth/register", json={**CREDS, "email": "ana@example.com"})
    assert dup.status_code == 409 and dup.json()["code"] == "email_taken"


def test_wrong_password_and_rate_limit(anon_client: TestClient) -> None:
    anon_client.post("/api/auth/register", json=CREDS)
    anon_client.post("/api/auth/logout")
    bad = {**CREDS, "password": "wrong password"}
    for _ in range(auth.LOGIN_LIMIT):
        assert anon_client.post("/api/auth/login", json=bad).status_code == 401
    res = anon_client.post("/api/auth/login", json=CREDS)
    assert res.status_code == 429 and res.json()["code"] == "too_many_attempts"


def test_sessions_require_sign_in(anon_client: TestClient) -> None:
    assert anon_client.get("/api/sessions").status_code == 401
    res = anon_client.post(
        "/api/sessions", files={"file": ("a.mp4", io.BytesIO(b"x"), "video/mp4")}
    )
    assert res.status_code == 401 and res.json()["code"] == "not_signed_in"


def test_users_cannot_see_each_other(anon_client: TestClient) -> None:
    anon_client.post("/api/auth/register", json=CREDS)
    sid = anon_client.post(
        "/api/sessions", files={"file": ("a.mp4", io.BytesIO(b"x"), "video/mp4")}
    ).json()["id"]
    anon_client.post("/api/auth/logout")
    anon_client.post(
        "/api/auth/register", json={"email": "bo@example.com", "password": "another password"}
    )
    assert anon_client.get(f"/api/sessions/{sid}").status_code == 404
    assert anon_client.get("/api/sessions").json() == []


def test_settings_update(client: TestClient) -> None:
    res = client.put(
        "/api/auth/me/settings",
        json={"language": "en", "model_preset": "fast", "auto_delete_video": True},
    )
    assert res.status_code == 200 and res.json()["settings"]["auto_delete_video"] is True
    assert client.put("/api/auth/me/settings", json={"model_preset": "huge"}).status_code == 422


def test_change_password(client: TestClient) -> None:
    body = {"current_password": "wrong", "new_password": "new long password"}
    assert client.post("/api/auth/me/password", json=body).status_code == 403
    body["current_password"] = "correct horse"
    assert client.post("/api/auth/me/password", json=body).status_code == 204
    client.post("/api/auth/logout")
    ok = client.post(
        "/api/auth/login", json={"email": "speaker@example.com", "password": "new long password"}
    )
    assert ok.status_code == 200


def test_delete_account_removes_everything(client: TestClient, settings_env: Path) -> None:
    sid = client.post(
        "/api/sessions", files={"file": ("a.mp4", io.BytesIO(b"x"), "video/mp4")}
    ).json()["id"]
    assert (settings_env / "media" / sid).exists()
    assert client.request("DELETE", "/api/auth/me", json={"password": "wrong"}).status_code == 403
    assert (
        client.request("DELETE", "/api/auth/me", json={"password": "correct horse"}).status_code
        == 204
    )
    assert not (settings_env / "media" / sid).exists()
    assert client.get("/api/auth/me").status_code == 401
    login = client.post(
        "/api/auth/login", json={"email": "speaker@example.com", "password": "correct horse"}
    )
    assert login.status_code == 401


def test_first_account_adopts_pre_account_sessions(anon_client: TestClient) -> None:
    from app.db.models import PracticeSession, SessionStatus
    from app.db.session import get_or_create_local_user, get_sessionmaker

    db = get_sessionmaker()()
    legacy = get_or_create_local_user(db)
    db.add(
        PracticeSession(
            user_id=legacy.id,
            title="old talk",
            source="upload",
            mode="free_talk",
            original_filename="a.mp4",
            media_path="/x",
            size_bytes=1,
            status=SessionStatus.completed,
            warnings=[],
        )
    )
    db.commit()
    db.close()
    anon_client.post("/api/auth/register", json=CREDS)
    assert [s["title"] for s in anon_client.get("/api/sessions").json()] == ["old talk"]


def test_live_websocket_requires_sign_in(anon_client: TestClient) -> None:
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect), anon_client.websocket_connect("/api/live/ws") as ws:
        ws.receive_json()


def test_limiter_works_with_redis() -> None:
    import fakeredis

    limiter = auth.LoginLimiter(fakeredis.FakeRedis())
    for _ in range(auth.LOGIN_LIMIT):
        assert not limiter.blocked("a@b.c")
        limiter.failed("a@b.c")
    assert limiter.blocked("A@B.C")
    limiter.reset("a@b.c")
    assert not limiter.blocked("a@b.c")
