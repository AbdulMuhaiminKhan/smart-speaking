"""Step 3b: pitch, volume and energy with Praat (parselmouth), plus a tone label.

Only frames inside spoken words count, so silences do not drag the averages
down. All thresholds are documented in docs/scoring.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from app.schemas.metrics import PacingMetrics, TimePoint, VoiceMetrics
from app.schemas.transcript import Transcript

FloatArray = npt.NDArray[np.float64]

PITCH_FLOOR_HZ = 75.0
PITCH_CEILING_HZ = 500.0
FRAME_S = 0.01
MONOTONE_STD_ST = 2.0  # below this pitch spread, speech sounds monotone
QUIET_DROP_DB = 10.0  # seconds this far below the median count as too quiet
OUTLIER_ST = 12.0  # pitch frames more than an octave from the median are tracking errors
TREND_MIN_SECONDS = 60  # energy trend needs a minute of speech to mean anything


@dataclass
class Contours:
    times: FloatArray
    pitch_hz: FloatArray  # 0 where unvoiced
    intensity_times: FloatArray
    intensity_db: FloatArray


def extract_contours(audio_path: Path) -> Contours:
    import parselmouth

    snd = parselmouth.Sound(str(audio_path))
    pitch = snd.to_pitch(
        time_step=FRAME_S, pitch_floor=PITCH_FLOOR_HZ, pitch_ceiling=PITCH_CEILING_HZ
    )
    intensity = snd.to_intensity(minimum_pitch=PITCH_FLOOR_HZ, time_step=FRAME_S)
    return Contours(
        times=np.asarray(pitch.xs(), dtype=np.float64),
        pitch_hz=np.asarray(pitch.selected_array["frequency"], dtype=np.float64),
        intensity_times=np.asarray(intensity.xs(), dtype=np.float64),
        intensity_db=np.asarray(intensity.values[0], dtype=np.float64),
    )


def speech_mask(times: FloatArray, spans: list[tuple[float, float]]) -> npt.NDArray[np.bool_]:
    mask = np.zeros(times.shape, dtype=bool)
    for start, end in spans:
        mask |= (times >= start) & (times <= end)
    return mask


def to_semitones(hz: FloatArray, reference_hz: float) -> FloatArray:
    return 12.0 * np.log2(hz / reference_hz)


def per_second(
    times: FloatArray,
    values: FloatArray,
    valid: npt.NDArray[np.bool_],
    duration: float,
    how: str,
    min_frames: int = 5,
) -> list[TimePoint]:
    points: list[TimePoint] = []
    for sec in range(int(np.ceil(duration))):
        sel = valid & (times >= sec) & (times < sec + 1)
        if sel.sum() < min_frames:
            points.append(TimePoint(t=sec + 0.5, value=None))
            continue
        v = float(np.median(values[sel]) if how == "median" else np.mean(values[sel]))
        points.append(TimePoint(t=sec + 0.5, value=round(v, 1)))
    return points


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def classify_tone(
    *,
    pitch_std_st: float | None,
    intensity_std_db: float | None,
    pacing: PacingMetrics,
    fillers_per_min: float,
) -> tuple[str, dict[str, float], list[str]]:
    """Heuristic tone label. Each score is 0..1; the highest wins, if it is clear enough."""
    minutes = max(pacing.speaking_time_s / 60, 1e-6)
    hesitations_per_min = sum(p.kind == "hesitation" for p in pacing.pauses) / minutes
    std = pitch_std_st if pitch_std_st is not None else 3.0
    ist = intensity_std_db if intensity_std_db is not None else 5.0

    rushed = 0.7 * _clamp((pacing.wpm_overall - 160) / 40) + 0.3 * _clamp(
        (0.08 - pacing.pause_ratio) / 0.08
    )
    flat = 0.7 * _clamp((2.5 - std) / 1.5) + 0.3 * _clamp((3.0 - ist) / 3.0)
    nervous = (
        0.5 * _clamp(fillers_per_min / 6)
        + 0.3 * _clamp(hesitations_per_min / 4)
        + 0.2 * _clamp(pacing.wpm_variability / 0.4)
    )
    scores = {"rushed": round(rushed, 3), "flat": round(flat, 3), "nervous": round(nervous, 3)}
    worst = max(scores, key=lambda k: scores[k])
    scores["confident"] = round(1.0 - scores[worst], 3)

    reasons: list[str] = []
    if pacing.wpm_overall > 160:
        reasons.append(f"fast pace ({pacing.wpm_overall:.0f} words per minute)")
    if pacing.pause_ratio < 0.08:
        reasons.append("very few pauses")
    if std < 2.5:
        reasons.append(f"narrow pitch range ({std:.1f} semitones)")
    if fillers_per_min >= 3:
        reasons.append(f"{fillers_per_min:.1f} filler words per minute")
    if hesitations_per_min >= 2:
        reasons.append(f"{hesitations_per_min:.1f} mid-sentence hesitations per minute")

    label = worst if scores[worst] >= 0.4 else "confident"
    if label == "confident":
        reasons = reasons or ["steady pace, varied pitch and few fillers"]
    return label, scores, reasons


def analyze(
    contours: Contours,
    transcript: Transcript,
    pacing: PacingMetrics,
    fillers_per_min: float,
) -> VoiceMetrics:
    """Pure analysis on extracted contours, so it can be tested without audio files."""
    spans = [(w.start, w.end) for w in transcript.words]
    duration = transcript.duration_s

    in_speech = speech_mask(contours.times, spans)
    voiced = in_speech & (contours.pitch_hz > 0)
    n_speech = int(in_speech.sum())
    voiced_ratio = int(voiced.sum()) / n_speech if n_speech else 0.0

    pitch_median: float | None = None
    pitch_std: float | None = None
    pitch_range: float | None = None
    pitch_series: list[TimePoint] = []
    if voiced.sum() >= 20:
        pitch_median = float(np.median(contours.pitch_hz[voiced]))
        st = np.zeros_like(contours.pitch_hz)
        st[voiced] = to_semitones(contours.pitch_hz[voiced], pitch_median)
        voiced &= np.abs(st) <= OUTLIER_ST
        pitch_std = float(np.std(st[voiced]))
        p5, p95 = np.percentile(st[voiced], [5, 95])
        pitch_range = float(p95 - p5)
        pitch_series = per_second(contours.times, contours.pitch_hz, voiced, duration, "median")

    i_speech = speech_mask(contours.intensity_times, spans) & np.isfinite(contours.intensity_db)
    intensity_mean: float | None = None
    intensity_std: float | None = None
    volume_series: list[TimePoint] = []
    quiet_ratio = 0.0
    trend: float | None = None
    if i_speech.sum() >= 20:
        db = contours.intensity_db[i_speech]
        intensity_mean = float(np.mean(db))
        volume_series = per_second(
            contours.intensity_times,
            contours.intensity_db,
            i_speech,
            duration,
            "median",
            # Need 0.3 s of speech in a second, or a word clipped at its edge looks "quiet".
            min_frames=int(0.3 / FRAME_S),
        )
        secs = [(p.t, p.value) for p in volume_series if p.value is not None]
        if secs:
            med = float(np.median([v for _, v in secs]))
            quiet_ratio = sum(v < med - QUIET_DROP_DB for _, v in secs) / len(secs)
            # Spread of second-by-second loudness: how consistent the volume is.
            # Frame-level spread mostly measures consonants vs vowels, not delivery.
            # A robust spread (MAD) keeps one mistimed word over silence from dominating.
            levels = np.array([v for _, v in secs])
            intensity_std = float(1.4826 * np.median(np.abs(levels - np.median(levels))))
        if len(secs) >= TREND_MIN_SECONDS:
            ts = np.array([t for t, _ in secs])
            vs = np.array([v for _, v in secs])
            trend = float(np.polyfit(ts / 60.0, vs, 1)[0])

    tone, scores, reasons = classify_tone(
        pitch_std_st=pitch_std,
        intensity_std_db=intensity_std,
        pacing=pacing,
        fillers_per_min=fillers_per_min,
    )

    def r(x: float | None, nd: int = 2) -> float | None:
        return None if x is None else round(x, nd)

    return VoiceMetrics(
        voiced_ratio=round(voiced_ratio, 3),
        pitch_median_hz=r(pitch_median, 1),
        pitch_std_semitones=r(pitch_std),
        pitch_range_semitones=r(pitch_range),
        monotone=pitch_std is not None and pitch_std < MONOTONE_STD_ST,
        pitch_series=pitch_series,
        intensity_mean_db=r(intensity_mean, 1),
        intensity_std_db=r(intensity_std),
        volume_series=volume_series,
        quiet_ratio=round(quiet_ratio, 3),
        energy_trend_db_per_min=r(trend),
        tone=tone,
        tone_scores=scores,
        tone_reasons=reasons,
    )


def run(
    audio_path: Path, transcript: Transcript, pacing: PacingMetrics, fillers_per_min: float
) -> VoiceMetrics:
    return analyze(extract_contours(audio_path), transcript, pacing, fillers_per_min)
