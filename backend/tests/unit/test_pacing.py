import pytest

from app.pipeline import pacing
from tests.helpers import transcript_from, words_from


def test_wpm_overall_matches_even_speech() -> None:
    # 0.3 s word + 0.1 s gap = 0.4 s per word -> 150 words per minute
    words = words_from(" ".join(["word"] * 150))
    m = pacing.run(transcript_from(words))
    assert m.wpm_overall == pytest.approx(150, rel=0.02)
    assert m.word_count == 150
    assert m.pause_count == 0


def test_pause_classification() -> None:
    text = "Hello everyone. Today we start the talk now and then we finish"
    # index: 0 Hello 1 everyone. 2 Today 3 we 4 start 5 the 6 talk 7 now 8 and ...
    words = words_from(text, gaps={2: 0.8, 5: 0.9, 8: 3.0})
    kinds = [(round(p.duration, 1), p.kind) for p in pacing.find_pauses(words)]
    assert kinds == [(0.9, "effective"), (1.0, "hesitation"), (3.1, "awkward")]
    assert pacing.find_pauses(words)[0].after_sentence


def test_short_mid_sentence_gaps_are_ignored() -> None:
    words = words_from("one two three", gaps={1: 0.3})
    assert pacing.find_pauses(words) == []


def test_wpm_series_detects_fast_section() -> None:
    slow = words_from(" ".join(["a"] * 40), word_s=0.5, gap_s=0.25)  # 80 wpm, 30 s
    fast = words_from(" ".join(["b"] * 120), start=30.5, word_s=0.2, gap_s=0.1)  # 200 wpm, 36 s
    m = pacing.run(transcript_from(slow + fast))
    first, last = m.wpm_series[0].value, m.wpm_series[-1].value
    assert first is not None and last is not None
    assert first < 100 and last > 180
    assert 0 < m.fast_ratio < 1
    assert m.wpm_variability > 0.2


def test_short_talk_gives_single_series_point() -> None:
    m = pacing.run(transcript_from(words_from("just a few words here")))
    assert len(m.wpm_series) == 1


def test_target_delta() -> None:
    words = words_from(" ".join(["w"] * 150))  # about 60 s
    m = pacing.run(transcript_from(words), target_seconds=60)
    assert m.duration_delta_s == pytest.approx(0, abs=1)


def test_empty_transcript_raises() -> None:
    from app.schemas.transcript import Transcript

    with pytest.raises(ValueError):
        pacing.run(Transcript(language="en", duration_s=1, model="t", segments=[]))
