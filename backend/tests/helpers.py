"""Builders for synthetic transcripts used across unit tests."""

from app.schemas.transcript import Segment, Transcript, Word


def words_from(
    text: str,
    *,
    start: float = 0.0,
    word_s: float = 0.3,
    gap_s: float = 0.1,
    gaps: dict[int, float] | None = None,
    probability: float = 0.95,
) -> list[Word]:
    """One Word per token, evenly spaced, with optional extra gaps before given indices."""
    out: list[Word] = []
    t = start
    for i, tok in enumerate(text.split()):
        if gaps and i in gaps:
            t += gaps[i]
        out.append(
            Word(text=tok, start=round(t, 3), end=round(t + word_s, 3), probability=probability)
        )
        t += word_s + gap_s
    return out


def transcript_from(words: list[Word], duration: float | None = None) -> Transcript:
    end = words[-1].end if words else 0.0
    return Transcript(
        language="en",
        duration_s=duration or end + 1,
        model="test",
        segments=[
            Segment(
                id=0,
                start=words[0].start if words else 0,
                end=end,
                text=" ".join(w.text for w in words),
                words=words,
            )
        ],
    )
