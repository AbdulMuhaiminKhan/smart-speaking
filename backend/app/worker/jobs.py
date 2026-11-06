"""The analysis job. Runs each pipeline step in order and records progress.

Steps run one at a time so only one large model is in memory at once.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import MODEL_PRESETS, get_settings
from app.db.models import AnalysisResult, PracticeSession, SessionStatus
from app.db.session import get_sessionmaker
from app.pipeline import (
    body,
    language,
    pacing,
    preprocess,
    pronunciation,
    report,
    report_llm,
    scoring,
    transcribe,
    voice,
)
from app.pipeline import issues as issues_mod
from app.pipeline.errors import PipelineError
from app.schemas.metrics import BodyMetrics, PronunciationMetrics
from app.services.storage import session_dir

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stage:
    name: str
    start: float  # overall progress when the stage begins, 0..1
    end: float


# Later phases add stages here (voice, language, pronunciation, body, scoring, report).
STAGES = {
    "preprocess": Stage("preprocess", 0.0, 0.04),
    "transcribe": Stage("transcribe", 0.04, 0.55),
    "language": Stage("language", 0.55, 0.57),
    "voice": Stage("voice", 0.57, 0.62),
    "pronunciation": Stage("pronunciation", 0.62, 0.72),
    "body": Stage("body", 0.72, 0.85),
    "report": Stage("report", 0.85, 0.86),
    "coaching": Stage("coaching", 0.86, 1.0),
}


class ProgressReporter:
    """Writes progress to the DB, at most every 0.5 s, so the UI can show a bar."""

    def __init__(self, db: Session, ps: PracticeSession, min_interval_s: float = 0.5) -> None:
        self.db = db
        self.ps = ps
        self.min_interval_s = min_interval_s
        self._last = 0.0

    def stage(self, name: str) -> None:
        self.ps.stage = name
        self.ps.progress = STAGES[name].start
        self.db.commit()
        self._last = time.monotonic()

    def update(self, name: str, fraction: float) -> None:
        st = STAGES[name]
        value = st.start + (st.end - st.start) * max(0.0, min(1.0, fraction))
        now = time.monotonic()
        if now - self._last >= self.min_interval_s and value > self.ps.progress:
            self.ps.progress = round(value, 4)
            self.db.commit()
            self._last = now


def save_result(db: Session, session_id: uuid.UUID, step: str, data: dict[str, Any]) -> None:
    existing = db.get(AnalysisResult, (session_id, step))
    if existing is None:
        db.add(AnalysisResult(session_id=session_id, step=step, data=data))
    else:
        existing.data = data
    db.commit()


def analyze_session(session_id: str) -> None:
    settings = get_settings()
    sid = uuid.UUID(session_id)
    db = get_sessionmaker()()
    try:
        ps = db.get(PracticeSession, sid)
        if ps is None:
            log.warning("session %s was deleted before analysis started", session_id)
            return

        ps.status = SessionStatus.processing
        ps.error_code = None
        ps.error_message = None
        db.commit()
        progress = ProgressReporter(db, ps)
        work = session_dir(settings.media_dir, sid)

        try:
            progress.stage("preprocess")
            info, audio_path, warnings, playable = preprocess.run(
                Path(ps.media_path), work, settings.min_duration_s, settings.max_duration_s
            )
            if playable != Path(ps.media_path):
                # Keep only the repaired copy so the video can be seeked in the report.
                Path(ps.media_path).unlink(missing_ok=True)
                ps.media_path = str(playable)
            ps.duration_s = info.duration_s
            ps.warnings = warnings
            save_result(db, sid, "media", info.model_dump())

            progress.stage("transcribe")
            model_size = MODEL_PRESETS.get(ps.model_preset, MODEL_PRESETS["balanced"])
            transcript = transcribe.run(
                audio_path,
                model_size=model_size,
                models_dir=settings.models_dir,
                language=ps.language or None,
                device_pref=settings.whisper_device,
                on_progress=lambda f: progress.update("transcribe", f),
            )
            save_result(db, sid, "transcript", transcript.model_dump())

            progress.stage("language")
            pacing_m = pacing.run(transcript, target_seconds=ps.target_seconds)
            save_result(db, sid, "pacing", pacing_m.model_dump())
            language_m = language.run(
                transcript,
                speaking_time_s=pacing_m.speaking_time_s,
                language=ps.language,
                script_text=ps.script_text,
            )
            save_result(db, sid, "language", language_m.model_dump())

            progress.stage("voice")
            voice_m = voice.run(audio_path, transcript, pacing_m, language_m.fillers_per_min)
            save_result(db, sid, "voice", voice_m.model_dump())

            progress.stage("pronunciation")
            pron_m: PronunciationMetrics | None = None
            try:
                pron_m = pronunciation.run(
                    audio_path, transcript, settings.models_dir, ps.language or "en"
                )
                save_result(db, sid, "pronunciation", pron_m.model_dump())
            except Exception:
                log.exception("pronunciation analysis failed for session %s", session_id)

            body_m: BodyMetrics | None = None
            if info.has_video:
                progress.stage("body")
                try:
                    body_m = body.run(
                        Path(ps.media_path),
                        settings.models_dir,
                        info.duration_s,
                        on_progress=lambda f: progress.update("body", f),
                    )
                    save_result(db, sid, "body", body_m.model_dump())
                    if body_m.too_dark_ratio > 0.5:
                        ps.warnings = [
                            *ps.warnings,
                            "bad_lighting: The video is very dark, so body tracking may be "
                            "less accurate. Face a window or a lamp next time.",
                        ]
                except Exception:
                    log.exception("body analysis failed for session %s", session_id)

            progress.stage("report")
            not_scored = scoring.body_not_scored(body_m, info.has_video)
            if pron_m is None:
                not_scored["pronunciation"] = "Pronunciation analysis failed for this recording."
            elif pron_m.words_checked < 20:
                not_scored["pronunciation"] = (
                    "Too few words to judge pronunciation fairly (at least 20 are needed)."
                )
            scores = scoring.score(
                pacing=pacing_m,
                voice=voice_m,
                language=language_m,
                body=body_m,
                pronunciation=pron_m,
                duration_s=info.duration_s,
                not_scored=not_scored,
            )
            issue_list = issues_mod.build(
                pacing_m,
                voice_m,
                language_m,
                body_m,
                skip_categories=set(not_scored),
                pronunciation=pron_m,
            )
            rep = report.build(
                scores=scores,
                issues=issue_list,
                pacing=pacing_m,
                voice=voice_m,
                language=language_m,
                body=body_m,
                pronunciation=pron_m,
            )
            save_result(db, sid, "report", rep.model_dump())  # template version first

            if settings.llm_enabled:
                progress.stage("coaching")
                rep = report_llm.run(
                    rep, transcript.text, url=settings.ollama_url, model=settings.ollama_model
                )
                save_result(db, sid, "report", rep.model_dump())

            if (ps.user.settings or {}).get("auto_delete_video"):
                # Privacy setting: keep the report, delete the recording and audio.
                Path(ps.media_path).unlink(missing_ok=True)
                audio_path.unlink(missing_ok=True)
                ps.media_deleted = True

            ps.status = SessionStatus.completed
            ps.stage = None
            ps.progress = 1.0
            ps.completed_at = datetime.now(UTC)
            db.commit()
        except PipelineError as exc:
            db.rollback()
            _fail(db, sid, exc.code, exc.message)
        except Exception:
            log.exception("analysis failed for session %s", session_id)
            db.rollback()
            _fail(
                db,
                sid,
                "internal_error",
                "Something went wrong while analyzing this recording. Please try again.",
            )
    finally:
        db.close()


def _fail(db: Session, sid: uuid.UUID, code: str, message: str) -> None:
    ps = db.get(PracticeSession, sid)
    if ps is None:
        return
    ps.status = SessionStatus.failed
    ps.error_code = code
    ps.error_message = message
    db.commit()
