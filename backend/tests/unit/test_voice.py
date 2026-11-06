import numpy as np
import pytest

from app.pipeline import pacing, voice
from tests.helpers import transcript_from, words_from


def contours(pitch_fn, db_fn, duration: float = 30.0) -> voice.Contours:  # type: ignore[no-untyped-def]
    t = np.arange(0, duration, voice.FRAME_S)
    return voice.Contours(times=t, pitch_hz=pitch_fn(t), intensity_times=t, intensity_db=db_fn(t))


def setup(duration: float = 30.0):  # type: ignore[no-untyped-def]
    words = words_from(" ".join(["word"] * int(duration / 0.4)))
    t = transcript_from(words, duration=duration)
    return t, pacing.run(t)


def test_monotone_voice_detected() -> None:
    t, p = setup()
    c = contours(lambda x: np.full_like(x, 120.0) + np.sin(x) * 2, lambda x: np.full_like(x, 65.0))
    m = voice.analyze(c, t, p, fillers_per_min=0)
    assert m.monotone
    assert m.pitch_std_semitones is not None and m.pitch_std_semitones < 1
    assert m.tone == "flat"


def test_expressive_voice() -> None:
    t, p = setup()
    c = contours(lambda x: 180 * 2 ** (4 * np.sin(x * 1.3) / 12), lambda x: 65 + 4 * np.sin(x))
    m = voice.analyze(c, t, p, fillers_per_min=0)
    assert not m.monotone
    assert m.pitch_std_semitones == pytest.approx(4 / np.sqrt(2), abs=0.3)
    assert m.pitch_median_hz == pytest.approx(180, rel=0.05)
    assert m.tone == "confident"


def test_unvoiced_frames_and_octave_errors_are_ignored() -> None:
    t, p = setup()

    def pitch(x):  # type: ignore[no-untyped-def]
        out = 150 * 2 ** (3 * np.sin(x) / 12)
        out[::10] = 0  # unvoiced
        out[5::50] = 600  # tracking errors far above the median
        return out

    m = voice.analyze(contours(pitch, lambda x: np.full_like(x, 60.0)), t, p, 0)
    assert m.pitch_std_semitones == pytest.approx(3 / np.sqrt(2), abs=0.3)
    assert 0.85 < m.voiced_ratio < 0.95


def test_trailing_off_and_quiet_stretch() -> None:
    t, p = setup(60)

    def db(x):  # type: ignore[no-untyped-def]
        out = 70 - x * 0.15  # falls 9 dB over the minute
        out[(x > 20) & (x < 26)] = 45
        return out

    m = voice.analyze(contours(lambda x: 150 * 2 ** (3 * np.sin(x) / 12), db, 60), t, p, 0)
    assert m.energy_trend_db_per_min is not None and m.energy_trend_db_per_min < -5
    assert m.quiet_ratio > 0.05


def test_no_voiced_audio_gives_none() -> None:
    t, p = setup()
    m = voice.analyze(contours(np.zeros_like, lambda x: np.full_like(x, 60.0)), t, p, 0)
    assert m.pitch_std_semitones is None and not m.monotone


def test_tone_rushed_and_nervous() -> None:
    _, p = setup()
    fast = p.model_copy(update={"wpm_overall": 210.0, "pause_ratio": 0.0})
    label, _, reasons = voice.classify_tone(
        pitch_std_st=3.5, intensity_std_db=5, pacing=fast, fillers_per_min=0
    )
    assert label == "rushed" and any("fast pace" in r for r in reasons)
    label, _, _ = voice.classify_tone(
        pitch_std_st=3.5, intensity_std_db=5, pacing=p, fillers_per_min=9
    )
    assert label == "nervous"
