import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Language = Literal["en", "de", "ur"]


class Goals(BaseModel):
    """Personal targets shown on the dashboard. None switches a target off."""

    sessions_per_week: int | None = Field(default=3, ge=1, le=21)
    max_fillers_per_min: float | None = Field(default=3.0, ge=0, le=30)
    wpm_low: int | None = Field(default=120, ge=60, le=250)
    wpm_high: int | None = Field(default=160, ge=60, le=250)
    min_score: int | None = Field(default=None, ge=1, le=100)


class UserSettings(BaseModel):
    language: Language = "en"  # language you speak in recordings
    ui_language: Language = "en"  # language of the app and the written coaching
    model_preset: Literal["fast", "balanced", "accurate"] = "balanced"
    auto_delete_video: bool = False
    goals: Goals = Goals()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    settings: UserSettings
    created_at: datetime


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    name: str | None = Field(default=None, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


class DeleteAccountIn(BaseModel):
    password: str = Field(max_length=200)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=8, max_length=200)
