"""Request and response models for the HTTP API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import InputSource, SessionMode, SessionStatus


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source: InputSource
    mode: SessionMode
    target_seconds: int | None
    language: str
    model_preset: str
    original_filename: str
    size_bytes: int
    duration_s: float | None
    media_deleted: bool
    status: SessionStatus
    stage: str | None
    progress: float
    error_code: str | None
    error_message: str | None
    warnings: list[str]
    created_at: datetime
    completed_at: datetime | None


class HealthOut(BaseModel):
    status: str
    database: bool
    redis: bool
    ffmpeg: bool


class ErrorOut(BaseModel):
    code: str
    message: str
