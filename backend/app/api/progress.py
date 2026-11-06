"""Progress across sessions for the dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbDep, UserDep
from app.db.models import AnalysisResult, PracticeSession, SessionStatus

router = APIRouter(prefix="/api/progress", tags=["progress"])


class SessionScores(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    duration_s: float | None
    overall: float | None
    categories: dict[str, float | None]


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
    q = (
        select(PracticeSession, AnalysisResult.data)
        .join(
            AnalysisResult,
            (AnalysisResult.session_id == PracticeSession.id) & (AnalysisResult.step == "report"),
        )
        .where(
            PracticeSession.user_id == user.id, PracticeSession.status == SessionStatus.completed
        )
        .order_by(PracticeSession.created_at)
    )
    rows = [
        SessionScores(
            id=ps.id,
            title=ps.title,
            created_at=ps.created_at,
            duration_s=ps.duration_s,
            overall=data.get("overall"),
            categories={k: v.get("score") for k, v in data["scores"]["categories"].items()},
        )
        for ps, data in db.execute(q).all()
    ]
    return summarize(rows)
