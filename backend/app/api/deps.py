"""Shared FastAPI dependencies: database session and the signed-in user."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services import auth

DbDep = Annotated[Session, Depends(get_db)]


def current_user(request: Request, db: DbDep) -> User:
    user = auth.user_for_token(db, request.cookies.get(auth.COOKIE_NAME))
    if user is None:
        raise HTTPException(401, detail={"code": "not_signed_in", "message": "Please sign in."})
    return user


UserDep = Annotated[User, Depends(current_user)]


@lru_cache
def _limiter() -> auth.LoginLimiter:
    from app.services.queue import get_redis

    try:
        r = get_redis()
        r.ping()
        return auth.LoginLimiter(r)
    except Exception:
        return auth.LoginLimiter(auth.MemoryCounter())


def get_limiter() -> auth.LoginLimiter:
    return _limiter()
