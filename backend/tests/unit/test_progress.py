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


def test_session_summary_and_rebuild_for_old_sessions() -> None:
    from app.pipeline import language, pacing, summary
    from tests.helpers import transcript_from, words_from

    words = words_from("Um hello everyone this is a short talk about um practice", probability=0.9)
    words[3].probability = 0.2  # one unclear word
    t = transcript_from(words)
    p = pacing.run(t)
    lang = language.run(t, speaking_time_s=p.speaking_time_s)
    s = summary.build(t, p, lang, None, None)
    assert s.filler_count == 2 and s.clarity_pct == 90.9 and s.eye_contact_pct is None

    rebuilt = summary.from_results(
        {"transcript": t.model_dump(), "pacing": p.model_dump(), "language": lang.model_dump()}
    )
    assert rebuilt == s
    assert summary.from_results({"report": {}}) is None
