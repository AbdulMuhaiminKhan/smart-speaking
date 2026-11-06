from dataclasses import dataclass, field

import pytest

from app.pipeline import transcribe
from app.pipeline.errors import NoSpeechError


@dataclass
class W:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class S:
    id: int
    start: float
    end: float
    text: str
    words: list[W] = field(default_factory=list)
    avg_logprob: float = -0.2
    no_speech_prob: float = 0.01


def test_build_transcript_keeps_fillers_and_timestamps() -> None:
    segs = [
        S(
            0,
            0.0,
            2.0,
            " Um, hello everyone.",
            [
                W(" Um,", 0.0, 0.4, 0.6),
                W(" hello", 0.5, 0.9, 0.98),
                W(" everyone.", 1.0, 1.8, 0.95),
            ],
        ),
        S(
            1,
            2.5,
            4.0,
            " So, uh, welcome.",
            [W(" So,", 2.5, 2.8, 0.9), W(" uh,", 2.9, 3.1, 0.5), W(" welcome.", 3.2, 4.0, 0.97)],
        ),
    ]
    progress: list[float] = []
    t = transcribe.build_transcript(
        segs,
        language="en",
        language_probability=0.99,
        duration_s=8.0,
        model="small",
        on_progress=progress.append,
    )
    assert [w.text for w in t.words] == ["Um,", "hello", "everyone.", "So,", "uh,", "welcome."]
    assert t.text == "Um, hello everyone. So, uh, welcome."
    assert t.segments[1].words[1].start == 2.9
    assert progress == [0.25, 0.5]


def test_build_transcript_clamps_probability_and_drops_empty_words() -> None:
    segs = [S(0, 0, 1, "hi", [W(" ", 0, 0.1, 0.5), W(" hi", 0.1, 0.5, 1.7)])]
    t = transcribe.build_transcript(
        segs, language="en", language_probability=None, duration_s=1, model="tiny"
    )
    assert len(t.words) == 1
    assert t.words[0].probability == 1.0


def test_build_transcript_without_words_means_no_speech() -> None:
    with pytest.raises(NoSpeechError):
        transcribe.build_transcript(
            [S(0, 0, 1, "")], language="en", language_probability=None, duration_s=10, model="tiny"
        )


def test_filler_prompt_mentions_core_fillers() -> None:
    prompt = transcribe.FILLER_PROMPT.lower()
    for filler in ["um", "uh", "like", "you know", "basically"]:
        assert filler in prompt


def test_detect_device_forced_cpu() -> None:
    assert transcribe.detect_device("cpu") == ("cpu", "int8")
