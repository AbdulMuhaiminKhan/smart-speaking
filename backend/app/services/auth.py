"""Passwords (argon2), cookie sessions and a small login rate limiter."""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Protocol

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AuthSession, User

COOKIE_NAME = "ss_session"
SESSION_DAYS = 30
MIN_PASSWORD = 8
LOGIN_LIMIT = 10  # failed attempts per window, per email
LOGIN_WINDOW_S = 15 * 60

_hasher = PasswordHasher()  # argon2id with the library's recommended parameters


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    """Store a new session and return the raw token for the cookie."""
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=_digest(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    s = db.get(AuthSession, _digest(token))
    if s is None:
        return None
    expires = s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        db.delete(s)
        db.commit()
        return None
    return s.user


def end_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _digest(token)))
        db.commit()


def find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


class _Counter(Protocol):
    def incr(self, key: str) -> int: ...
    def expire(self, key: str, seconds: int) -> object: ...
    def get(self, key: str) -> object: ...
    def delete(self, key: str) -> object: ...


class MemoryCounter:
    """Fallback when Redis is not reachable; good enough for one process."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}

    def incr(self, key: str) -> int:
        n, exp = self._data.get(key, (0, time.time() + LOGIN_WINDOW_S))
        if exp < time.time():
            n, exp = 0, time.time() + LOGIN_WINDOW_S
        self._data[key] = (n + 1, exp)
        return n + 1

    def expire(self, key: str, seconds: int) -> object:
        return None

    def get(self, key: str) -> object:
        n, exp = self._data.get(key, (0, 0.0))
        return n if exp >= time.time() else 0

    def delete(self, key: str) -> object:
        return self._data.pop(key, None)


class LoginLimiter:
    def __init__(self, store: _Counter) -> None:
        self.store = store

    @staticmethod
    def _key(email: str) -> str:
        return f"login-fail:{email.strip().lower()}"

    def blocked(self, email: str) -> bool:
        value = self.store.get(self._key(email))
        raw = value.decode() if isinstance(value, bytes) else value  # Redis returns bytes
        count = int(str(raw)) if raw else 0
        return count >= LOGIN_LIMIT

    def failed(self, email: str) -> None:
        key = self._key(email)
        if self.store.incr(key) == 1:
            self.store.expire(key, LOGIN_WINDOW_S)

    def reset(self, email: str) -> None:
        self.store.delete(self._key(email))
