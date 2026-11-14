import io

from fastapi.testclient import TestClient


def make_session(client: TestClient) -> str:
    res = client.post(
        "/api/sessions", files={"file": ("talk.mp4", io.BytesIO(b"video"), "video/mp4")}
    )
    assert res.status_code == 201
    return str(res.json()["id"])


def test_notes_crud_sorted_by_time(client: TestClient) -> None:
    sid = make_session(client)
    base = f"/api/sessions/{sid}/annotations"
    late = client.post(base, json={"t": 42.5, "text": "  Great story here  "}).json()
    client.post(base, json={"t": 3, "text": "Slow the opening down"})
    notes = client.get(base).json()
    assert [n["t"] for n in notes] == [3.0, 42.5]
    assert notes[1]["text"] == "Great story here"

    edited = client.put(f"{base}/{late['id']}", json={"t": 40, "text": "Story"}).json()
    assert edited["t"] == 40 and edited["text"] == "Story"
    assert client.delete(f"{base}/{late['id']}").status_code == 204
    assert len(client.get(base).json()) == 1


def test_notes_validate_and_stay_private(client: TestClient) -> None:
    sid = make_session(client)
    base = f"/api/sessions/{sid}/annotations"
    assert client.post(base, json={"t": -1, "text": "x"}).status_code == 422
    assert client.post(base, json={"t": 1, "text": ""}).status_code == 422
    missing = "/api/sessions/00000000-0000-0000-0000-000000000000/annotations"
    assert client.get(missing).status_code == 404


def test_deleting_a_session_deletes_its_notes(client: TestClient) -> None:
    sid = make_session(client)
    client.post(f"/api/sessions/{sid}/annotations", json={"t": 1, "text": "note"})
    assert client.delete(f"/api/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sessions/{sid}/annotations").status_code == 404
