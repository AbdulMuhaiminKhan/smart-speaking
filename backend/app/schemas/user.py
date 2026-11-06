import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserSettings(BaseModel):
    language: Literal["en"] = "en"  # more languages can be added with a lexicon file
    model_preset: Literal["fast", "balanced", "accurate"] = "balanced"
    auto_delete_video: bool = False


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
