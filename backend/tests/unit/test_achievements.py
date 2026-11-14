import uuid
from datetime import UTC, date, datetime, timedelta

from app.api.progress import SessionScores
from app.pipeline.summary import SessionSummary
from app.schemas.user import Goals
from app.services.achievements import compute, streaks, tz_or_utc

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)


def metrics(**kw: float) -> SessionSummary:
    base = dict(
        words=200,
        speaking_s=90.0,
        wpm=140.0,
        fillers_per_min=2.0,
        filler_count=3,
        clarity_pct=90.0,
        pitch_variation_st=3.0,
        monotone=False,
        pause_ratio=0.2,
        eye_contact_pct=70.0,
        gestures_per_min=5.0,
        script_coverage_pct=None,
    )
    base.update(kw)
    return SessionSummary(**base)  # type: ignore[arg-type]


def row(days_ago: float, overall: float, mode: str = "free_talk", **kw: float) -> SessionScores:
    return SessionScores(
        id=uuid.uuid4(),
        title="t",
        created_at=NOW - timedelta(days=days_ago),
        duration_s=90,
        overall=overall,
        categories={},
        mode=mode,
        metrics=metrics(**kw),
    )


def test_streaks() -> None:
    d = date(2026, 11, 14)
    days = {d, d - timedelta(1), d - timedelta(2), d - timedelta(5)}
    assert streaks(days, d) == (3, 3)
    assert streaks({d - timedelta(1)}, d) == (1, 1)  # yesterday still counts
    assert streaks({d - timedelta(3)}, d) == (0, 1)


def test_achievements_and_goals() -> None:
    rows = [
        row(3, 60, wpm=180, fillers_per_min=5),
        row(2, 72, mode="impromptu"),
        row(1, 85, mode="interview", fillers_per_min=0.5, eye_contact_pct=85),
        row(0, 80, mode="script", script_coverage_pct=95, clarity_pct=97),
    ]
    a = compute(rows, Goals(sessions_per_week=3, min_score=75), tz_or_utc("Europe/Berlin"), NOW)
    earned = {x.id for x in a.achievements if x.earned}
    assert {"first_session", "streak_3", "score_80", "low_fillers", "eye_contact_pro"} <= earned
    assert {"script_master", "clear_speaker", "explorer", "improver", "steady_pace"} <= earned
    assert "five_sessions" not in earned and "polyglot" not in earned
    assert a.streak.current == 4
    goals = {g.id: g for g in a.goals}
    assert goals["fillers"].met and goals["pace"].met and goals["score"].met
    assert goals["sessions_per_week"].current == a.week_sessions


def test_bad_timezone_falls_back_to_utc() -> None:
    assert str(tz_or_utc("Mars/Olympus")) == "UTC"


def test_achievements_endpoint(client) -> None:  # type: ignore[no-untyped-def]
    res = client.get("/api/progress/achievements?tz=Asia/Karachi")
    assert res.status_code == 200
    body = res.json()
    assert body["streak"]["current"] == 0 and body["achievements"][0]["id"] == "first_session"
