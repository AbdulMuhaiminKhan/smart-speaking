"""Accounts: register, sign in and out, settings, change password, delete account."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import DbDep, UserDep, get_limiter
from app.config import Settings, get_settings
from app.db.models import User
from app.db.session import LOCAL_USER_EMAIL
from app.schemas.user import (
    ChangePasswordIn,
    DeleteAccountIn,
    LoginIn,
    RegisterIn,
    UserOut,
    UserSettings,
)
from app.services import auth, storage
from app.services.auth import LoginLimiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
LimiterDep = Annotated[LoginLimiter, Depends(get_limiter)]


def _error(code: int, key: str, message: str) -> Exception:
    from fastapi import HTTPException

    return HTTPException(code, detail={"code": key, "message": message})


def _set_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        token,
        max_age=auth.SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def _out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        settings=UserSettings.model_validate(user.settings or {}),
        created_at=user.created_at,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response, db: DbDep, settings: SettingsDep) -> UserOut:
    email = body.email.strip().lower()
    if auth.find_user(db, email):
        raise _error(409, "email_taken", "An account with this email already exists.")

    # The first real account takes over recordings made before accounts existed.
    legacy = auth.find_user(db, LOCAL_USER_EMAIL)
    real_users = db.scalar(
        select(func.count()).select_from(User).where(User.email != LOCAL_USER_EMAIL)
    )
    if legacy is not None and real_users == 0:
        user = legacy
        user.email = email
    else:
        user = User(email=email)
        db.add(user)
    user.name = (body.name or "").strip() or None
    user.password_hash = auth.hash_password(body.password)
    user.settings = UserSettings().model_dump()
    db.commit()
    db.refresh(user)
    _set_cookie(response, auth.create_session(db, user), settings)
    return _out(user)


@router.post("/login", response_model=UserOut)
def login(
    body: LoginIn, response: Response, db: DbDep, settings: SettingsDep, limiter: LimiterDep
) -> UserOut:
    if limiter.blocked(body.email):
        raise _error(429, "too_many_attempts", "Too many failed sign-ins. Try again in 15 minutes.")
    user = auth.find_user(db, body.email)
    if user is None or not auth.verify_password(user.password_hash, body.password):
        limiter.failed(body.email)
        raise _error(401, "bad_credentials", "Wrong email or password.")
    limiter.reset(body.email)
    _set_cookie(response, auth.create_session(db, user), settings)
    return _out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbDep) -> None:
    auth.end_session(db, request.cookies.get(auth.COOKIE_NAME))
    response.delete_cookie(auth.COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: UserDep) -> UserOut:
    return _out(user)


@router.put("/me/settings", response_model=UserOut)
def update_settings(body: UserSettings, user: UserDep, db: DbDep) -> UserOut:
    user.settings = body.model_dump()
    db.commit()
    return _out(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, user: UserDep, db: DbDep) -> None:
    if not auth.verify_password(user.password_hash, body.current_password):
        raise _error(403, "bad_password", "Your current password is not correct.")
    user.password_hash = auth.hash_password(body.new_password)
    db.commit()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    body: DeleteAccountIn, response: Response, user: UserDep, db: DbDep, settings: SettingsDep
) -> None:
    """Delete the account, every session, every report and every file. Cannot be undone."""
    if not auth.verify_password(user.password_hash, body.password):
        raise _error(403, "bad_password", "Your password is not correct.")
    session_ids = [s.id for s in user.sessions]
    db.delete(user)
    db.commit()
    for sid in session_ids:
        storage.delete_session_files(settings.media_dir, sid)
    response.delete_cookie(auth.COOKIE_NAME, path="/")
