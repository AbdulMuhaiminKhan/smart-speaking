"""Local media storage. Each session gets one folder; deleting it removes everything."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.pipeline.preprocess import ACCEPTED_EXTENSIONS

CHUNK = 1024 * 1024


class UploadTooLargeError(Exception):
    pass


class UnsupportedExtensionError(Exception):
    pass


def session_dir(media_dir: Path, session_id: uuid.UUID) -> Path:
    return media_dir / str(session_id)


def safe_extension(filename: str, content_type: str | None = None) -> str:
    ext = Path(filename).suffix.lower()
    if ext in ACCEPTED_EXTENSIONS:
        return ext
    # Live recordings arrive as blobs; trust the browser's MIME type there.
    if content_type:
        if content_type.startswith("video/webm") or content_type.startswith("audio/webm"):
            return ".webm"
        if content_type.startswith("video/mp4"):
            return ".mp4"
        if content_type.startswith("video/quicktime"):
            return ".mov"
    raise UnsupportedExtensionError(ext or "none")


def save_upload(src: BinaryIO, dest: Path, max_bytes: int) -> int:
    """Copy an upload to disk in chunks, stopping as soon as it exceeds max_bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with dest.open("wb") as out:
            while chunk := src.read(CHUNK):
                written += len(chunk)
                if written > max_bytes:
                    raise UploadTooLargeError()
                out.write(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return written


def delete_session_files(media_dir: Path, session_id: uuid.UUID) -> None:
    shutil.rmtree(session_dir(media_dir, session_id), ignore_errors=True)
