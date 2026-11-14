"""Streaks, weekly goals and achievements, computed from finished sessions.

Nothing is stored: everything is derived from the sessions, so deleting a
session also takes back what it earned.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel

from app.api.progress import SessionScores
from app.schemas.user import Goals


class Achievement(BaseModel):
    id: str
    earned: bool
    earned_at: datetime | None = None
    session_id: str | None = None
    progress: float = 0.0  # 0..1 toward earning it


class Streak(BaseModel):
    current: int  # consecutive days with practice, ending today or yesterday
    best: int
    days: list[date]  # practice days in the last 5 weeks (local time), oldest first


class GoalStatus(BaseModel):
    id: str  # sessions_per_week | fillers | pace | score
    target: str  # human-readable target, e.g. "3" or "120-160"
    current: float | None
    met: bool


class Achievements(BaseModel):
    streak: Streak
    week_sessions: int
    goals: list[GoalStatus]
    achievements: list[Achievement]


def tz_or_utc(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name) if name else ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def streaks(days: set[date], today: date) -> tuple[int, int]:
    """(current, best) runs of consecutive practice days."""
    best = run = 0
    prev: date | None = None
    for d in sorted(days):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    current = 0
    d = today if today in days else today - timedelta(days=1)
    while d in days:
        current += 1
        d -= timedelta(days=1)
    return current, best


Check = Callable[[SessionScores], bool]


def _m(s: SessionScores, field: str) -> float | None:
    if s.metrics is None:
        return None
    v = getattr(s.metrics, field)
    return float(v) if v is not None else None


def _speaking(s: SessionScores) -> float:
    return s.metrics.speaking_s if s.metrics else 0.0


PER_SESSION: dict[str, Check] = {
    "score_80": lambda s: (s.overall or 0) >= 80,
    "score_90": lambda s: (s.overall or 0) >= 90,
    "low_fillers": lambda s: _speaking(s) >= 60 and (_m(s, "fillers_per_min") or 99) <= 1,
    "steady_pace": lambda s: 120 <= (_m(s, "wpm") or 0) <= 160 and _speaking(s) >= 60,
    "clear_speaker": lambda s: (_m(s, "clarity_pct") or 0) >= 95,
    "eye_contact_pro": lambda s: (_m(s, "eye_contact_pct") or 0) >= 80,
    "script_master": lambda s: (_m(s, "script_coverage_pct") or 0) >= 90,
}


def compute(rows: list[SessionScores], goals: Goals, tz: ZoneInfo, now: datetime) -> Achievements:
    local = [(s, s.created_at.astimezone(tz)) for s in rows]
    today = now.astimezone(tz).date()
    days = {d.date() for _, d in local}
    current, best = streaks(days, today)
    since = today - timedelta(days=34)
    week_start = today - timedelta(days=today.weekday())
    week = [s for s, d in local if d.date() >= week_start]

    out: list[Achievement] = []

    def nth(n: int, aid: str) -> None:
        hit = rows[n - 1] if len(rows) >= n else None
        out.append(
            Achievement(
                id=aid,
                earned=hit is not None,
                earned_at=hit.created_at if hit else None,
                session_id=str(hit.id) if hit else None,
                progress=min(1.0, len(rows) / n),
            )
        )

    nth(1, "first_session")
    nth(5, "five_sessions")
    nth(20, "twenty_sessions")
    for n in (3, 7):
        out.append(Achievement(id=f"streak_{n}", earned=best >= n, progress=min(1.0, best / n)))
    for aid, check in PER_SESSION.items():
        hit = next((s for s in rows if check(s)), None)
        out.append(
            Achievement(
                id=aid,
                earned=hit is not None,
                earned_at=hit.created_at if hit else None,
                session_id=str(hit.id) if hit else None,
                progress=1.0 if hit else 0.0,
            )
        )
    modes = {s.mode for s in rows}
    out.append(
        Achievement(id="explorer", earned=len(modes) >= 4, progress=min(1.0, len(modes) / 4))
    )
    langs = {s.language for s in rows}
    out.append(
        Achievement(id="polyglot", earned=len(langs) >= 2, progress=min(1.0, len(langs) / 2))
    )
    scored = [s.overall for s in rows if s.overall is not None]
    gain = (max(scored[1:]) - scored[0]) if len(scored) >= 2 else 0.0
    out.append(
        Achievement(id="improver", earned=gain >= 10, progress=max(0.0, min(1.0, gain / 10)))
    )

    # Goals, judged on this week's sessions (or the latest session for per-talk targets).
    statuses: list[GoalStatus] = []
    if goals.sessions_per_week:
        statuses.append(
            GoalStatus(
                id="sessions_per_week",
                target=str(goals.sessions_per_week),
                current=len(week),
                met=len(week) >= goals.sessions_per_week,
            )
        )
    latest = rows[-1] if rows else None
    if goals.max_fillers_per_min is not None:
        v = _m(latest, "fillers_per_min") if latest else None
        statuses.append(
            GoalStatus(
                id="fillers",
                target=f"{goals.max_fillers_per_min:g}",
                current=v,
                met=v is not None and v <= goals.max_fillers_per_min,
            )
        )
    if goals.wpm_low is not None and goals.wpm_high is not None:
        v = _m(latest, "wpm") if latest else None
        statuses.append(
            GoalStatus(
                id="pace",
                target=f"{goals.wpm_low}-{goals.wpm_high}",
                current=v,
                met=v is not None and goals.wpm_low <= v <= goals.wpm_high,
            )
        )
    if goals.min_score is not None:
        v = latest.overall if latest else None
        statuses.append(
            GoalStatus(
                id="score",
                target=str(goals.min_score),
                current=v,
                met=v is not None and v >= goals.min_score,
            )
        )

    return Achievements(
        streak=Streak(current=current, best=best, days=sorted(d for d in days if d >= since)),
        week_sessions=len(week),
        goals=statuses,
        achievements=out,
    )
