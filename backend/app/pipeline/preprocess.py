"""Step 1: probe the media file, validate it, and extract a 16 kHz mono WAV.

Video frames are not written to disk here. The body-language step (Phase 3)
decodes frames on the fly at its own sample rate, which avoids writing
thousands of JPEGs for a 15 minute talk.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.pipeline.errors import NoAudioError, TooLongError, TooShortError, UnsupportedFormatError

AUDIO_SAMPLE_RATE = 16_000

# Container formats ffprobe reports for the uploads we accept.
ACCEPTED_FORMATS = {"mov", "mp4", "m4a", "3gp", "3g2", "mj2", "matroska", "webm"}
ACCEPTED_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}


class MissingDurationError(UnsupportedFormatError):
    """The container has no duration header (typical for browser MediaRecorder webm)."""

    def __init__(self) -> None:
        super().__init__("no duration")


class MediaInfo(BaseModel):
    duration_s: float
    format_name: str
    has_video: bool
    has_audio: bool
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    audio_codec: str | None = None
    video_codec: str | None = None


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"'{name}' is not installed or not on PATH")
    return path


def _parse_rate(rate: str | None) -> float | None:
    if not rate or rate in {"0/0", "0"}:
        return None
    if "/" in rate:
        num, den = rate.split("/", 1)
        try:
            n, d = float(num), float(den)
        except ValueError:
            return None
        return n / d if d else None
    try:
        return float(rate)
    except ValueError:
        return None


def parse_probe(probe: dict[str, Any]) -> MediaInfo:
    """Turn ffprobe JSON into MediaInfo. Pure function, unit tested."""
    fmt = probe.get("format") or {}
    streams: list[dict[str, Any]] = probe.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # Cover images in audio files show up as a video stream with attached_pic set.
    if video is not None and (video.get("disposition") or {}).get("attached_pic"):
        video = None

    duration = fmt.get("duration")
    if duration is None:
        durations = [float(s["duration"]) for s in streams if s.get("duration")]
        duration = max(durations) if durations else None
    if duration is None:
        raise MissingDurationError()

    return MediaInfo(
        duration_s=float(duration),
        format_name=str(fmt.get("format_name", "")),
        has_video=video is not None,
        has_audio=audio is not None,
        width=video.get("width") if video else None,
        height=video.get("height") if video else None,
        fps=_parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        if video
        else None,
        audio_codec=audio.get("codec_name") if audio else None,
        video_codec=video.get("codec_name") if video else None,
    )


def validate_media(info: MediaInfo, min_s: float, max_s: float) -> list[str]:
    """Raise for input we cannot analyze; return warnings for input we can."""
    formats = set(info.format_name.split(","))
    if not formats & ACCEPTED_FORMATS:
        raise UnsupportedFormatError(info.format_name or "unknown container")
    if not info.has_audio:
        raise NoAudioError()
    if info.duration_s < min_s:
        raise TooShortError(info.duration_s, min_s)
    if info.duration_s > max_s:
        raise TooLongError(info.duration_s, max_s)

    warnings: list[str] = []
    if not info.has_video:
        warnings.append("no_video: Only audio was found, so body language will not be scored.")
    elif info.height is not None and info.height < 240:
        warnings.append(
            "low_resolution: The video is very small, so body tracking may be less accurate."
        )
    if info.fps is not None and info.fps < 10:
        warnings.append(
            "low_fps: The video has a low frame rate, so movement analysis may be less accurate."
        )
    return warnings


def probe(path: Path) -> MediaInfo:
    ffprobe = require_binary("ffprobe")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise UnsupportedFormatError(
            result.stderr.strip().splitlines()[-1] if result.stderr else ""
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise UnsupportedFormatError("unreadable probe output") from exc
    return parse_probe(data)


def extract_audio(src: Path, dest: Path) -> Path:
    """Write a 16 kHz mono 16-bit WAV, the format Whisper and wav2vec2 expect."""
    ffmpeg = require_binary("ffmpeg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(AUDIO_SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0 or not dest.exists():
        raise UnsupportedFormatError("audio could not be extracted")
    return dest


def repair_container(src: Path, dest: Path) -> Path:
    """Rewrite the container without re-encoding so it gets a duration and seek index.

    Browsers record webm as a live stream, so the file has no duration and
    cannot be seeked. A stream copy fixes both in a second or two.
    """
    ffmpeg = require_binary("ffmpeg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-fflags",
            "+genpts",
            "-i",
            str(src),
            "-c",
            "copy",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0 or not dest.exists():
        raise UnsupportedFormatError("the recording could not be repaired")
    return dest


def run(
    src: Path, work_dir: Path, min_s: float, max_s: float
) -> tuple[MediaInfo, Path, list[str], Path]:
    """Returns (info, audio wav, warnings, playable media path)."""
    try:
        info = probe(src)
    except MissingDurationError:
        src = repair_container(src, work_dir / f"playable{src.suffix or '.webm'}")
        info = probe(src)
    warnings = validate_media(info, min_s, max_s)
    audio = extract_audio(src, work_dir / "audio.wav")
    return info, audio, warnings, src
