"""SQLAlchemy models. Types are portable so unit tests can run on SQLite."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SessionStatus(enum.StrEnum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SessionMode(enum.StrEnum):
    free_talk = "free_talk"
    timed_pitch = "timed_pitch"
    script = "script"


class InputSource(enum.StrEnum):
    upload = "upload"
    live = "live"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Null only for the legacy built-in local user from before accounts existed.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sessions: Mapped[list[PracticeSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    """A signed-in browser. Only a SHA-256 hash of the cookie token is stored."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="auth_sessions")


class PracticeSession(Base):
    """One recording and everything computed from it."""

    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    source: Mapped[InputSource] = mapped_column(Enum(InputSource, native_enum=False))
    mode: Mapped[SessionMode] = mapped_column(Enum(SessionMode, native_enum=False))
    target_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    model_preset: Mapped[str] = mapped_column(String(16), default="balanced")

    original_filename: Mapped[str] = mapped_column(String(255))
    media_path: Mapped[str] = mapped_column(String(1024))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    media_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False), default=SessionStatus.uploaded
    )
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JsonType, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    results: Mapped[list[AnalysisResult]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class AnalysisResult(Base):
    """Output of one pipeline step (e.g. 'media', 'transcript'), stored as JSON."""

    __tablename__ = "analysis_results"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    step: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[PracticeSession] = relationship(back_populates="results")
