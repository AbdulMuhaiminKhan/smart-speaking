"""Metric outputs of the analysis steps. These are what the report and the LLM see."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Category = Literal[
    "voice", "pacing", "language", "pronunciation", "eye_contact", "posture", "body_language"
]
Severity = Literal["info", "minor", "major"]


class Issue(BaseModel):
    """One timestamped problem shown on the mistakes timeline."""

    id: str  # stable within a report, e.g. "filler-3"
    category: Category
    kind: str  # e.g. "filler", "awkward_pause", "too_fast"
    start: float
    end: float
    severity: Severity
    message: str
    text: str | None = None  # the words involved, when there are any


class TimePoint(BaseModel):
    t: float
    value: float | None


# ---- Pacing -----------------------------------------------------------------


class Pause(BaseModel):
    start: float
    end: float
    duration: float
    kind: Literal["effective", "awkward", "hesitation"]
    after_sentence: bool


class PacingMetrics(BaseModel):
    word_count: int
    speaking_time_s: float  # first word start to last word end
    wpm_overall: float
    wpm_articulation: float  # words per minute excluding pauses
    wpm_series: list[TimePoint]
    wpm_variability: float  # coefficient of variation of the series
    fast_ratio: float  # share of windows above the fast threshold
    slow_ratio: float
    pauses: list[Pause]
    pause_count: int
    awkward_pause_count: int
    effective_pause_count: int
    pause_ratio: float  # share of speaking time spent in pauses
    longest_pause_s: float
    target_seconds: int | None
    duration_delta_s: float | None  # actual minus target, for timed pitches


# ---- Voice ------------------------------------------------------------------


class VoiceMetrics(BaseModel):
    voiced_ratio: float
    pitch_median_hz: float | None
    pitch_std_semitones: float | None
    pitch_range_semitones: float | None  # 5th to 95th percentile
    monotone: bool
    pitch_series: list[TimePoint]  # median Hz per second, None when unvoiced
    intensity_mean_db: float | None
    intensity_std_db: float | None
    volume_series: list[TimePoint]  # mean dB per second while speaking
    quiet_ratio: float  # share of speaking seconds much quieter than the median
    energy_trend_db_per_min: float | None  # negative means trailing off
    tone: Literal["confident", "nervous", "flat", "rushed"]
    tone_scores: dict[str, float]
    tone_reasons: list[str]


# ---- Language ---------------------------------------------------------------


class Occurrence(BaseModel):
    phrase: str
    start: float
    end: float
    word_index: int


class ScriptComparison(BaseModel):
    coverage: float  # share of script words that were said, in order
    extra_ratio: float  # share of spoken words not in the script
    skipped: list[str]  # script passages that were left out
    added: list[str]  # spoken passages that were not in the script


class LanguageMetrics(BaseModel):
    word_count: int
    fillers: list[Occurrence]
    filler_counts: dict[str, int]
    fillers_per_min: float
    hedges: list[Occurrence]
    hedge_counts: dict[str, int]
    repetitions: list[Occurrence]  # "the the", "I I I"
    overused_words: dict[str, int]
    vocabulary_mattr: float  # moving-average type-token ratio, 0..1
    unique_words: int
    sentence_count: int
    avg_sentence_words: float
    long_sentences: list[Occurrence]  # phrase holds the first words of the sentence
    script: ScriptComparison | None


# ---- Body language ----------------------------------------------------------


class Segment(BaseModel):
    # looking_away, head_down, slouch, arms_crossed, hands_hidden, face_touch, fidget, sway, tense
    kind: str
    start: float
    end: float


class BodyMetrics(BaseModel):
    sample_fps: float
    frames_analyzed: int
    face_detected_ratio: float
    pose_detected_ratio: float
    too_dark_ratio: float  # frames under the brightness threshold

    # Eye contact (only frames with a face)
    eye_contact_ratio: float | None
    eye_contact_series: list[TimePoint]  # share of frames with eye contact per 5 s

    # Posture (only frames with shoulders visible)
    slouch_ratio: float | None
    head_down_ratio: float | None
    shoulder_tilt_deg: float | None  # median absolute tilt
    tilt_ratio: float | None
    lean_ratio: float | None

    # Body language
    hands_visible_ratio: float | None
    gestures_per_min: float | None
    open_gesture_ratio: float | None  # of frames with visible hands, open palms
    arms_crossed_ratio: float | None
    face_touch_count: int
    fidget_ratio: float | None
    sway_ratio: float | None
    smile_ratio: float | None
    tense_ratio: float | None
    neutral_ratio: float | None

    segments: list[Segment]
