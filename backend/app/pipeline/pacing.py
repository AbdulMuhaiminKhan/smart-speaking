"""Step 3a: speaking rate and pauses, computed from Whisper word timestamps.

All thresholds are documented in docs/scoring.md.
"""

from __future__ import annotations

import statistics

from app.schemas.metrics import PacingMetrics, Pause, TimePoint
from app.schemas.transcript import Transcript, Word

MIN_PAUSE_S = 0.3  # gaps shorter than this are ordinary word spacing
HESITATION_MIN_S = 0.6  # mid-sentence gaps from here on read as searching for words
AWKWARD_PAUSE_S = 2.5  # gaps this long feel awkward anywhere
WINDOW_S = 20.0  # rolling window for WPM over time
STEP_S = 5.0
FAST_WPM = 170.0
SLOW_WPM = 110.0

SENTENCE_END = (".", "?", "!")
CLAUSE_END = (",", ";", ":", "—", "-")


def _ends_sentence(word: Word) -> bool:
    return word.text.rstrip("\"')]").endswith(SENTENCE_END)


def _ends_clause(word: Word) -> bool:
    return word.text.rstrip("\"')]").endswith(CLAUSE_END)


def find_pauses(words: list[Word]) -> list[Pause]:
    pauses: list[Pause] = []
    for prev, nxt in zip(words, words[1:], strict=False):
        gap = round(nxt.start - prev.end, 3)
        if gap < MIN_PAUSE_S:
            continue
        boundary = _ends_sentence(prev) or _ends_clause(prev)
        if gap >= AWKWARD_PAUSE_S:
            kind = "awkward"
        elif boundary:
            kind = "effective"
        elif gap >= HESITATION_MIN_S:
            kind = "hesitation"
        else:
            continue  # a short mid-sentence breath, not worth reporting
        pauses.append(
            Pause(
                start=prev.end,
                end=nxt.start,
                duration=gap,
                kind=kind,
                after_sentence=_ends_sentence(prev),
            )
        )
    return pauses


def wpm_series(
    words: list[Word], window_s: float = WINDOW_S, step_s: float = STEP_S
) -> list[TimePoint]:
    """Words per minute in a rolling window, sampled every step_s seconds.

    Each point is labelled with the centre of its window.
    """
    if not words:
        return []
    start, end = words[0].start, words[-1].end
    span = end - start
    mids = [(w.start + w.end) / 2 for w in words]
    if span <= window_s:
        return [TimePoint(t=round(start + span / 2, 2), value=round(len(words) / span * 60, 1))]

    points: list[TimePoint] = []
    t = start
    while t + window_s <= end + 1e-6:
        count = sum(1 for m in mids if t <= m < t + window_s)
        points.append(
            TimePoint(t=round(t + window_s / 2, 2), value=round(count / window_s * 60, 1))
        )
        t += step_s
    return points


def run(transcript: Transcript, target_seconds: int | None = None) -> PacingMetrics:
    words = sorted(transcript.words, key=lambda w: w.start)
    if not words:
        raise ValueError("pacing needs at least one word")

    speaking_time = max(words[-1].end - words[0].start, 0.001)
    pauses = find_pauses(words)
    pause_total = sum(p.duration for p in pauses)
    series = wpm_series(words)
    values = [p.value for p in series if p.value is not None]
    mean = statistics.fmean(values) if values else 0.0
    variability = statistics.pstdev(values) / mean if len(values) > 1 and mean else 0.0

    return PacingMetrics(
        word_count=len(words),
        speaking_time_s=round(speaking_time, 2),
        wpm_overall=round(len(words) / speaking_time * 60, 1),
        wpm_articulation=round(len(words) / max(speaking_time - pause_total, 0.001) * 60, 1),
        wpm_series=series,
        wpm_variability=round(variability, 3),
        fast_ratio=round(sum(v > FAST_WPM for v in values) / len(values), 3) if values else 0.0,
        slow_ratio=round(sum(v < SLOW_WPM for v in values) / len(values), 3) if values else 0.0,
        pauses=pauses,
        pause_count=len(pauses),
        awkward_pause_count=sum(p.kind == "awkward" for p in pauses),
        effective_pause_count=sum(p.kind == "effective" for p in pauses),
        pause_ratio=round(pause_total / speaking_time, 3),
        longest_pause_s=max((p.duration for p in pauses), default=0.0),
        target_seconds=target_seconds,
        duration_delta_s=(
            round(speaking_time - target_seconds, 1) if target_seconds is not None else None
        ),
    )
