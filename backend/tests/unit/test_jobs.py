"""The job runner, with the transcription model replaced by a stub."""

from pathlib import Path

import pytest

from app.db.models import AnalysisResult, PracticeSession, SessionStatus
from app.db.session import get_or_create_local_user, get_sessionmaker
from app.pipeline import body, pronunciation, transcribe, voice_emotion
from app.schemas.metrics import PronunciationMetrics
from app.schemas.transcript import Segment, Transcript, Word
from app.worker import jobs
from tests.conftest import make_test_video, requires_ffmpeg


def make_session(media: Path) -> str:
    db = get_sessionmaker()()
    user = get_or_create_local_user(db)
    ps = PracticeSession(
        user_id=user.id,
        title="t",
        source="upload",
        mode="free_talk",
        original_filename=media.name,
        media_path=str(media),
        size_bytes=media.stat().st_size,
        status=SessionStatus.queued,
        warnings=[],
    )
    db.add(ps)
    db.commit()
    sid = str(ps.id)
    db.close()
    return sid


def fake_transcribe(audio_path: Path, **kwargs: object) -> Transcript:
    on_progress = kwargs.get("on_progress")
    if callable(on_progress):
        on_progress(1.0)
    return Transcript(
        language="en",
        duration_s=6.0,
        model="stub",
        segments=[
            Segment(
                id=0,
                start=0,
                end=1,
                text="Hello.",
                words=[Word(text="Hello.", start=0, end=1, probability=0.9)],
            )
        ],
    )


@requires_ffmpeg
def test_job_completes_and_stores_results(
    settings_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(transcribe, "run", fake_transcribe)
    monkeypatch.setenv("SS_LLM_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(body, "run", lambda *a, **k: body.aggregate([], body.SAMPLE_FPS, 6.0))
    monkeypatch.setattr(voice_emotion, "run", lambda *a, **k: voice_emotion.summarize([], []))
    monkeypatch.setattr(
        pronunciation,
        "run",
        lambda *a, **k: PronunciationMetrics(
            method="phonemes",
            words_checked=3,
            mean_similarity=0.9,
            low_confidence_ratio=0.0,
            unclear_per_100_words=0.0,
            unclear_words=[],
        ),
    )
    sid = make_session(make_test_video(settings_env / "clip.mp4"))

    jobs.analyze_session(sid)

    db = get_sessionmaker()()
    ps = db.get(PracticeSession, __import__("uuid").UUID(sid))
    assert ps is not None
    assert ps.status == SessionStatus.completed
    assert ps.progress == 1.0
    assert ps.duration_s == pytest.approx(6.0, abs=0.2)
    steps = {r.step for r in db.query(AnalysisResult).filter_by(session_id=ps.id)}
    assert steps == {
        "media",
        "transcript",
        "pacing",
        "language",
        "voice",
        "pronunciation",
        "voice_emotion",
        "body",
        "report",
    }


@requires_ffmpeg
def test_job_reports_input_errors(settings_env: Path) -> None:
    bad = settings_env / "bad.mp4"
    bad.write_bytes(b"nope")
    sid = make_session(bad)

    jobs.analyze_session(sid)

    db = get_sessionmaker()()
    ps = db.get(PracticeSession, __import__("uuid").UUID(sid))
    assert ps is not None
    assert ps.status == SessionStatus.failed
    assert ps.error_code == "unsupported_format"


def test_job_ignores_deleted_session(settings_env: Path) -> None:
    jobs.analyze_session("00000000-0000-0000-0000-000000000000")


@requires_ffmpeg
def test_auto_delete_video_setting(settings_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid as _uuid

    monkeypatch.setattr(transcribe, "run", fake_transcribe)
    monkeypatch.setenv("SS_LLM_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(body, "run", lambda *a, **k: body.aggregate([], body.SAMPLE_FPS, 6.0))
    monkeypatch.setattr(
        pronunciation,
        "run",
        lambda *a, **k: PronunciationMetrics(
            method="phonemes",
            words_checked=0,
            mean_similarity=None,
            low_confidence_ratio=0.0,
            unclear_per_100_words=0.0,
            unclear_words=[],
        ),
    )
    clip = make_test_video(settings_env / "clip.mp4")
    sid = make_session(clip)
    db = get_sessionmaker()()
    ps = db.get(PracticeSession, _uuid.UUID(sid))
    assert ps is not None
    ps.user.settings = {"auto_delete_video": True}
    db.commit()
    db.close()

    jobs.analyze_session(sid)

    db = get_sessionmaker()()
    ps = db.get(PracticeSession, _uuid.UUID(sid))
    assert ps is not None and ps.status == SessionStatus.completed and ps.media_deleted
    assert not clip.exists()
    assert db.get(AnalysisResult, (ps.id, "report")) is not None
