import io
from pathlib import Path

from fastapi.testclient import TestClient


def upload(
    client: TestClient, data: bytes = b"fake video bytes", name: str = "talk.mp4", **form: str
) -> dict:
    res = client.post(
        "/api/sessions", files={"file": (name, io.BytesIO(data), "video/mp4")}, data=form
    )
    return {"status": res.status_code, "body": res.json()}


def test_upload_creates_queued_session(client: TestClient, enqueued: list[str]) -> None:
    r = upload(client, title="Pitch practice")
    assert r["status"] == 201
    body = r["body"]
    assert body["status"] == "queued"
    assert body["title"] == "Pitch practice"
    assert enqueued == [body["id"]]


def test_upload_rejects_unsupported_extension(client: TestClient, enqueued: list[str]) -> None:
    res = client.post(
        "/api/sessions", files={"file": ("notes.txt", io.BytesIO(b"x"), "text/plain")}
    )
    assert res.status_code == 415
    assert res.json()["code"] == "unsupported_format"
    assert enqueued == []


def test_upload_rejects_empty_file(client: TestClient) -> None:
    assert upload(client, data=b"")["body"]["code"] == "empty_file"


def test_live_blob_uses_mime_type(client: TestClient) -> None:
    res = client.post(
        "/api/sessions",
        data={"source": "live"},
        files={"file": ("blob", io.BytesIO(b"x"), "video/webm;codecs=vp9")},
    )
    assert res.status_code == 201
    assert res.json()["source"] == "live"


def test_script_mode_requires_script(client: TestClient) -> None:
    r = upload(client, mode="script")
    assert r["status"] == 422 and r["body"]["code"] == "script_required"


def test_upload_too_large(client: TestClient, monkeypatch, settings_env: Path) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 10)
    r = upload(client, data=b"x" * 11)
    assert r["status"] == 413
    assert not any((settings_env / "media").glob("*/original.mp4"))


def test_list_get_and_delete(client: TestClient, settings_env: Path) -> None:
    sid = upload(client)["body"]["id"]
    assert [s["id"] for s in client.get("/api/sessions").json()] == [sid]
    assert client.get(f"/api/sessions/{sid}").json()["id"] == sid
    assert (settings_env / "media" / sid).exists()

    assert client.delete(f"/api/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sessions/{sid}").status_code == 404
    assert not (settings_env / "media" / sid).exists()


def test_result_not_ready(client: TestClient) -> None:
    sid = upload(client)["body"]["id"]
    res = client.get(f"/api/sessions/{sid}/results/transcript")
    assert res.status_code == 404 and res.json()["code"] == "not_ready"
