import shutil
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import HealthOut
from app.services.queue import get_redis

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(db: Annotated[Session, Depends(get_db)]) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        redis_ok = bool(get_redis().ping())
    except Exception:
        redis_ok = False
    ffmpeg_ok = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
    ok = db_ok and redis_ok and ffmpeg_ok
    return HealthOut(
        status="ok" if ok else "degraded", database=db_ok, redis=redis_ok, ffmpeg=ffmpeg_ok
    )
