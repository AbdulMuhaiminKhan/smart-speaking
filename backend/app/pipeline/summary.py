"""A few headline numbers per session, for trend charts, goals and achievements.

Stored as the "summary" result so the dashboard does not have to load every
transcript. `from_results` rebuilds it for sessions analyzed before it existed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.metrics import BodyMetrics, LanguageMetrics, PacingMetrics, VoiceMetrics
from app.schemas.transcript import Transcript

CLEAR_WORD_PROBABILITY = 0.5  # Whisper confidence at or above this counts as clearly heard


class SessionSummary(BaseModel):
    words: int
    speaking_s: float
    wpm: float | None
    fillers_per_min: float | None
    filler_count: int
    clarity_pct: float | None  # share of words Whisper heard clearly
    pitch_variation_st: float | None
    monotone: bool | None
    pause_ratio: float | None
    eye_contact_pct: float | None
    gestures_per_min: float | None
    script_coverage_pct: float | None


def clarity(transcript: Transcript) -> float | None:
    words = transcript.words
    if not words:
        return None
    clear = sum(w.probability >= CLEAR_WORD_PROBABILITY for w in words)
    return round(100 * clear / len(words), 1)


def build(
    transcript: Transcript,
    pacing: PacingMetrics,
    language: LanguageMetrics,
    voice: VoiceMetrics | None,
    body: BodyMetrics | None,
) -> SessionSummary:
    return SessionSummary(
        words=pacing.word_count,
        speaking_s=pacing.speaking_time_s,
        wpm=round(pacing.wpm_overall, 1) if pacing.word_count else None,
        fillers_per_min=language.fillers_per_min,
        filler_count=len(language.fillers),
        clarity_pct=clarity(transcript),
        pitch_variation_st=voice.pitch_std_semitones if voice else None,
        monotone=voice.monotone if voice else None,
        pause_ratio=pacing.pause_ratio,
        eye_contact_pct=(
            round(100 * body.eye_contact_ratio, 1)
            if body and body.eye_contact_ratio is not None
            else None
        ),
        gestures_per_min=body.gestures_per_min if body else None,
        script_coverage_pct=(
            round(100 * language.script.coverage, 1) if language.script is not None else None
        ),
    )


def from_results(results: dict[str, dict[str, Any]]) -> SessionSummary | None:
    """The stored summary, or one rebuilt from the step results of an older session."""
    if "summary" in results:
        return SessionSummary.model_validate(results["summary"])
    if not {"transcript", "pacing", "language"} <= results.keys():
        return None
    return build(
        Transcript.model_validate(results["transcript"]),
        PacingMetrics.model_validate(results["pacing"]),
        LanguageMetrics.model_validate(results["language"]),
        VoiceMetrics.model_validate(results["voice"]) if "voice" in results else None,
        BodyMetrics.model_validate(results["body"]) if "body" in results else None,
    )
