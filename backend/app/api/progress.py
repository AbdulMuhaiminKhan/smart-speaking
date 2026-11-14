"""Progress across sessions for the dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbDep, UserDep
from app.db.models import AnalysisResult, PracticeSession, SessionStatus
from app.pipeline.summary import SessionSummary, from_results

# Steps needed to rebuild a summary for sessions analyzed before summaries existed.
SUMMARY_STEPS = ("report", "summary", "transcript", "pacing", "language", "voice", "body")

router = APIRouter(prefix="/api/progress", tags=["progress"])


class SessionScores(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    duration_s: float | None
    overall: float | None
    categories: dict[str, float | None]
    mode: str = "free_talk"
    language: str = "en"
    metrics: SessionSummary | None = None


class Progress(BaseModel):
    sessions: list[SessionScores]  # oldest first
    count: int
    average: float | None
    best: float | None
    latest: float | None
    change: float | None  # latest minus the one before
    category_change: dict[str, float | None]  # latest minus the average of earlier sessions


def summarize(rows: list[SessionScores]) -> Progress:
    scores = [r.overall for r in rows if r.overall is not None]
    latest = rows[-1] if rows else None
    change = round(scores[-1] - scores[-2], 1) if len(scores) >= 2 else None
    cat_change: dict[str, float | None] = {}
    if latest and len(rows) >= 2:
        for cat, value in latest.categories.items():
            earlier = [r.categories.get(cat) for r in rows[:-1]]
            vals = [v for v in earlier if v is not None]
            cat_change[cat] = (
                round(value - sum(vals) / len(vals), 1) if value is not None and vals else None
            )
    return Progress(
        sessions=rows,
        count=len(rows),
        average=round(sum(scores) / len(scores), 1) if scores else None,
        best=max(scores) if scores else None,
        latest=scores[-1] if scores else None,
        change=change,
        category_change=cat_change,
    )


@router.get("", response_model=Progress)
def progress(db: DbDep, user: UserDep) -> Progress:
    return summarize(session_rows(db, user.id))


def session_rows(db: DbDep, user_id: uuid.UUID) -> list[SessionScores]:
    """Completed sessions with a report, oldest first, with their headline metrics."""
    sessions = db.scalars(
        select(PracticeSession)
        .where(
            PracticeSession.user_id == user_id, PracticeSession.status == SessionStatus.completed
        )
        .order_by(PracticeSession.created_at)
    ).all()
    ids = [ps.id for ps in sessions]
    results: dict[uuid.UUID, dict[str, dict[str, Any]]] = {i: {} for i in ids}
    if ids:
        for r in db.scalars(
            select(AnalysisResult).where(
                AnalysisResult.session_id.in_(ids), AnalysisResult.step.in_(SUMMARY_STEPS)
            )
        ):
            results[r.session_id][r.step] = r.data
    rows: list[SessionScores] = []
    for ps in sessions:
        res = results[ps.id]
        report = res.get("report")
        if report is None:
            continue
        rows.append(
            SessionScores(
                id=ps.id,
                title=ps.title,
                created_at=ps.created_at,
                duration_s=ps.duration_s,
                overall=report.get("overall"),
                categories={k: v.get("score") for k, v in report["scores"]["categories"].items()},
                mode=ps.mode.value,
                language=ps.language,
                metrics=from_results(res),
            )
        )
    return rows
