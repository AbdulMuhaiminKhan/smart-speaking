"""Engine and session factory."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import User

LOCAL_USER_EMAIL = "local@smartspeaking.local"


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs = {"connect_args": {"check_same_thread": False}}
    return create_engine(url, **kwargs)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def get_or_create_local_user(db: Session) -> User:
    """Single built-in user until real auth arrives in Phase 6."""
    user = db.scalar(select(User).where(User.email == LOCAL_USER_EMAIL))
    if user is None:
        user = User(email=LOCAL_USER_EMAIL)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
