"""Practice session endpoints: upload, status, transcript, media, delete."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import UserDep
from app.config import MODEL_PRESETS, Settings, get_settings
from app.db.models import (
    AnalysisResult,
    InputSource,
    PracticeSession,
    SessionMode,
    SessionStatus,
    User,
)
from app.db.session import get_db
from app.schemas.api import SessionOut
from app.services import storage
from app.services.queue import Enqueuer, get_enqueuer

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

DbDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def get_owned_session(session_id: uuid.UUID, db: Session, user: User) -> PracticeSession:
    ps = db.get(PracticeSession, session_id)
    if ps is None or ps.user_id != user.id:
        raise error(status.HTTP_404_NOT_FOUND, "not_found", "Session not found.")
    return ps


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    db: DbDep,
    user: UserDep,
    settings: SettingsDep,
    enqueue: Annotated[Enqueuer, Depends(get_enqueuer)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(max_length=200)] = None,
    source: Annotated[InputSource, Form()] = InputSource.upload,
    mode: Annotated[SessionMode, Form()] = SessionMode.free_talk,
    target_seconds: Annotated[int | None, Form(ge=30, le=900)] = None,
    script_text: Annotated[str | None, Form(max_length=50_000)] = None,
    language: Annotated[str, Form(max_length=8)] = "en",
    model_preset: Annotated[str, Form()] = "balanced",
) -> PracticeSession:
    if model_preset not in MODEL_PRESETS:
        raise error(422, "bad_preset", f"model_preset must be one of {sorted(MODEL_PRESETS)}.")
    if mode == SessionMode.script and not (script_text and script_text.strip()):
        raise error(422, "script_required", "Script mode needs the script text.")

    filename = file.filename or "recording"
    try:
        ext = storage.safe_extension(filename, file.content_type)
    except storage.UnsupportedExtensionError:
        raise error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "unsupported_format",
            "Please upload an mp4, webm or mov video.",
        ) from None

    sid = uuid.uuid4()
    dest = storage.session_dir(settings.media_dir, sid) / f"original{ext}"
    try:
        size = storage.save_upload(file.file, dest, settings.max_upload_bytes)
    except storage.UploadTooLargeError:
        storage.delete_session_files(settings.media_dir, sid)
        raise error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "too_large",
            f"The file is larger than {settings.max_upload_bytes // 1024**2} MB.",
        ) from None
    if size == 0:
        storage.delete_session_files(settings.media_dir, sid)
        raise error(422, "empty_file", "The uploaded file is empty.")

    ps = PracticeSession(
        id=sid,
        user_id=user.id,
        title=(title or "").strip() or filename.rsplit(".", 1)[0][:200] or "Practice session",
        source=source,
        mode=mode,
        target_seconds=target_seconds if mode == SessionMode.timed_pitch else None,
        script_text=script_text if mode == SessionMode.script else None,
        language=language,
        model_preset=model_preset,
        original_filename=filename[:255],
        media_path=str(dest),
        size_bytes=size,
        status=SessionStatus.queued,
        warnings=[],
    )
    db.add(ps)
    db.commit()

    try:
        enqueue(str(sid))
    except Exception:
        ps.status = SessionStatus.failed
        ps.error_code = "queue_unavailable"
        ps.error_message = "The analysis worker is not reachable. Is Redis running?"
        db.commit()
    db.refresh(ps)
    return ps


@router.get("", response_model=list[SessionOut])
def list_sessions(db: DbDep, user: UserDep) -> list[PracticeSession]:
    rows = db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user.id)
        .order_by(PracticeSession.created_at.desc())
    )
    return list(rows)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: uuid.UUID, db: DbDep, user: UserDep) -> PracticeSession:
    return get_owned_session(session_id, db, user)


@router.get("/{session_id}/results/{step}")
def get_result(session_id: uuid.UUID, step: str, db: DbDep, user: UserDep) -> dict[str, Any]:
    get_owned_session(session_id, db, user)
    result = db.get(AnalysisResult, (session_id, step))
    if result is None:
        raise error(404, "not_ready", f"No '{step}' result for this session yet.")
    return result.data


@router.get("/{session_id}/media")
def get_media(session_id: uuid.UUID, db: DbDep, user: UserDep) -> FileResponse:
    ps = get_owned_session(session_id, db, user)
    if ps.media_deleted:
        raise error(410, "video_deleted", "The video was deleted after analysis (see Settings).")
    return FileResponse(ps.media_path, filename=ps.original_filename)


@router.get("/{session_id}/report.pdf")
def get_report_pdf(session_id: uuid.UUID, db: DbDep, user: UserDep) -> Response:
    from app.pipeline.report import Report
    from app.schemas.transcript import Transcript
    from app.services import pdf

    ps = get_owned_session(session_id, db, user)
    results = {r.step: r.data for r in ps.results}
    if "report" not in results:
        raise error(404, "not_ready", "The report is not ready yet.")
    transcript = (
        Transcript.model_validate(results["transcript"]) if "transcript" in results else None
    )
    html = pdf.render_html(
        Report.model_validate(results["report"]),
        title=ps.title,
        created=ps.created_at.strftime("%d %b %Y, %H:%M"),
        duration_s=ps.duration_s,
        transcript_text=transcript.text if transcript else "",
        pacing=results.get("pacing"),
        voice=results.get("voice"),
        body=results.get("body"),
        voice_emotion=results.get("voice_emotion"),
    )
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in ps.title).strip() or "report"
    return Response(
        content=pdf.render_pdf(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="SmartSpeaking - {safe}.pdf"'},
    )


@router.post("/{session_id}/retry", response_model=SessionOut)
def retry_session(
    session_id: uuid.UUID,
    db: DbDep,
    user: UserDep,
    enqueue: Annotated[Enqueuer, Depends(get_enqueuer)],
) -> PracticeSession:
    ps = get_owned_session(session_id, db, user)
    if ps.status not in {SessionStatus.failed, SessionStatus.completed}:
        raise error(409, "busy", "This session is still being analyzed.")
    ps.status = SessionStatus.queued
    ps.progress = 0.0
    ps.stage = None
    ps.error_code = None
    ps.error_message = None
    db.commit()
    enqueue(str(ps.id))
    db.refresh(ps)
    return ps


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: uuid.UUID, db: DbDep, user: UserDep, settings: SettingsDep) -> None:
    ps = get_owned_session(session_id, db, user)
    db.delete(ps)
    db.commit()
    storage.delete_session_files(settings.media_dir, session_id)
