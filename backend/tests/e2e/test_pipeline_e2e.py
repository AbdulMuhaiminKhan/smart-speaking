"""End to end: upload a real clip through the API, run the job with real Whisper.

Slow (downloads Whisper tiny on first run). Run with: uv run pytest -m e2e
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.worker import jobs

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_speech.mp4"


@pytest.mark.e2e
def test_upload_to_transcript(
    client: TestClient, enqueued: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(jobs.MODEL_PRESETS, "fast", "tiny")
    with FIXTURE.open("rb") as fh:
        res = client.post(
            "/api/sessions",
            files={"file": ("sample.mp4", fh, "video/mp4")},
            data={"model_preset": "fast"},
        )
    assert res.status_code == 201
    sid = res.json()["id"]

    jobs.analyze_session(enqueued.pop())

    session = client.get(f"/api/sessions/{sid}").json()
    assert session["status"] == "completed", session
    assert session["duration_s"] == pytest.approx(16.0, abs=0.5)

    transcript = client.get(f"/api/sessions/{sid}/results/transcript").json()
    words = [w["text"].lower().strip(",.") for s in transcript["segments"] for w in s["words"]]
    assert "public" in words and "speaking" in words
    assert all(w["end"] >= w["start"] for s in transcript["segments"] for w in s["words"])
