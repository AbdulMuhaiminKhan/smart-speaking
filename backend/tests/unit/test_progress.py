import uuid
from datetime import UTC, datetime, timedelta

from app.api.progress import SessionScores, summarize


def row(i: int, overall: float | None, voice: float | None) -> SessionScores:
    return SessionScores(
        id=uuid.uuid4(),
        title=f"t{i}",
        created_at=datetime.now(UTC) + timedelta(days=i),
        duration_s=60,
        overall=overall,
        categories={"voice": voice, "posture": None},
    )


def test_summary_tracks_change() -> None:
    p = summarize([row(0, 60, 50), row(1, 70, 60), row(2, 75, 80)])
    assert p.count == 3 and p.best == 75 and p.latest == 75
    assert p.change == 5
    assert p.average == 68.3
    assert p.category_change["voice"] == 25  # 80 vs the average of 50 and 60
    assert p.category_change["posture"] is None


def test_summary_empty_and_single() -> None:
    assert summarize([]).latest is None
    one = summarize([row(0, 70, 70)])
    assert one.change is None and one.category_change == {}


def test_progress_endpoint_empty(client) -> None:  # type: ignore[no-untyped-def]
    res = client.get("/api/progress")
    assert res.status_code == 200 and res.json()["count"] == 0
