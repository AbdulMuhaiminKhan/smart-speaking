"""Transcript produced by the speech-to-text step, shared by later steps."""

from pydantic import BaseModel, Field


class Word(BaseModel):
    text: str
    start: float
    end: float
    probability: float = Field(ge=0.0, le=1.0)


class Segment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: list[Word]
    avg_logprob: float | None = None
    no_speech_prob: float | None = None


class Transcript(BaseModel):
    language: str
    language_probability: float | None = None
    duration_s: float
    model: str
    segments: list[Segment]

    @property
    def words(self) -> list[Word]:
        return [w for s in self.segments for w in s.words]

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments).strip()
