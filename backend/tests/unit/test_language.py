import pytest

from app.pipeline import language
from tests.helpers import transcript_from, words_from


def run(text: str, **kw: object) -> language.LanguageMetrics:
    t = transcript_from(words_from(text))
    return language.run(t, speaking_time_s=60, **kw)  # type: ignore[arg-type]


def test_counts_core_fillers_with_timestamps() -> None:
    m = run(
        "Um, hello everyone. Today I want to talk about, uh, public speaking. "
        "It is, like, a skill you can practice. So, basically, let's begin. You know what I mean?"
    )
    assert m.filler_counts == {
        "um": 1,
        "uh": 1,
        "like": 1,
        "so": 1,
        "basically": 1,
        "you know": 1,
        "i mean": 1,
    }
    assert m.fillers[0].start == 0.0
    assert m.fillers_per_min == 7.0


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I would like to thank you.", 0),
        ("It looks like rain.", 0),
        ("I like dogs.", 0),
        ("And I was like, no way.", 1),
        ("It was, like, huge.", 1),
        ("So we went home.", 0),  # "so" without a comma is ordinary
        ("We were tired, so we left.", 0),
        ("Well, here we go.", 1),
    ],
)
def test_contextual_fillers(text: str, expected: int) -> None:
    assert len(run(text).fillers) == expected


def test_hedges_prefer_longest_phrase() -> None:
    m = run("I think maybe we should go. It is sort of good. I think it works.")
    assert m.hedge_counts == {"i think maybe": 1, "sort of": 1, "i think": 1}


def test_repetitions() -> None:
    m = run("The the plan is I was I was going to go to the store.")
    assert [r.phrase for r in m.repetitions] == ["the the", "i was i was"]


def test_repetitions_ignore_fillers() -> None:
    assert run("um um hello").repetitions == []


def test_mattr() -> None:
    assert language.mattr(["a", "b", "c"]) == 1.0
    assert language.mattr(["a"] * 100) == pytest.approx(0.02)
    varied = [f"w{i}" for i in range(200)]
    assert language.mattr(varied) == 1.0


def test_sentences_and_long_sentences() -> None:
    long = " ".join(["word"] * 35) + "."
    m = run(f"Short one. Another short one. {long}")
    assert m.sentence_count == 3
    assert len(m.long_sentences) == 1
    assert m.avg_sentence_words == pytest.approx((2 + 3 + 35) / 3, abs=0.1)


def test_overused_words() -> None:
    m = run(" ".join(["innovation is key."] * 6))
    assert m.overused_words.get("innovation") == 6


def test_script_comparison() -> None:
    script = "Good morning. Today I will show three ideas about saving energy at home."
    spoken = "Um, good morning. Today I will show three ideas. Let me tell a quick story first."
    m = run(spoken, script_text=script)
    assert m.script is not None
    assert 0.4 < m.script.coverage < 0.7
    assert any("saving energy" in s for s in m.script.skipped)
    assert any("quick story" in a for a in m.script.added)


def test_unknown_language_falls_back_to_english() -> None:
    assert language.load_lexicon("xx") == language.load_lexicon("en")


def test_normalize() -> None:
    assert language.normalize("Don’t,") == "don't"
    assert language.normalize("...") == ""


def test_repetition_across_sentence_break_is_not_a_stumble() -> None:
    assert run("We start with heating. Heating is costly.").repetitions == []
