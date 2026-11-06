"""Shared fixtures. Unit tests use SQLite and a fake queue; no Redis or Postgres needed."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import session as db_session
from app.db.models import Base
from app.services import queue


@pytest.fixture()
def settings_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("SS_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SS_MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("SS_MODELS_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_sessionmaker.cache_clear()
    Base.metadata.create_all(db_session.get_engine())
    yield tmp_path
    db_session.get_engine().dispose()
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_sessionmaker.cache_clear()


@pytest.fixture()
def enqueued() -> list[str]:
    return []


@pytest.fixture()
def client(settings_env: Path, enqueued: list[str]) -> Iterator[TestClient]:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[queue.get_enqueuer] = lambda: enqueued.append
    with TestClient(app) as c:
        yield c


requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg is not installed"
)


def make_test_video(
    path: Path, seconds: float = 6.0, *, audio: bool = True, video: bool = True
) -> Path:
    """Generate a small synthetic clip (test pattern + tone) with ffmpeg."""
    args = ["ffmpeg", "-y", "-v", "error"]
    if video:
        args += ["-f", "lavfi", "-i", f"testsrc=size=320x240:rate=15:duration={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}"]
    args += ["-shortest"] if audio and video else []
    if video:
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "aac"]
    args.append(str(path))
    subprocess.run(args, check=True, capture_output=True)
    return path
