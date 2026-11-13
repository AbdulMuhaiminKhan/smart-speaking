"""German and Urdu support in the language step, Whisper prompts and coaching."""

import pytest

from app.pipeline import language, report_llm, transcribe
from tests.helpers import transcript_from, words_from


def run(text: str, lang: str) -> language.LanguageMetrics:
    return language.run(transcript_from(words_from(text)), speaking_time_s=60, language=lang)


def test_german_fillers_and_hedges() -> None:
    m = run(
        "Ähm, also ich habe halt, sag ich mal, viel geübt. Also, das ist "
        "sozusagen mein Plan. Ich glaube, vielleicht klappt es.",
        "de",
    )
    assert m.filler_counts == {"ähm": 1, "halt": 1, "sag ich mal": 1, "also": 1, "sozusagen": 1}
    assert m.hedge_counts == {"ich glaube": 1, "vielleicht": 1}


def test_german_also_is_only_a_filler_at_sentence_start_with_comma() -> None:
    assert run("Wir gehen also nach Hause.", "de").fillers == []


def test_urdu_fillers_hedges_and_sentence_end() -> None:
    m = run("اُم، میں آج بات کروں گا۔ اچھا، یعنی یہ اہم ہے۔ شاید آپ کو پسند آئے؟", "ur")
    assert m.filler_counts == {"ام": 1, "اچھا": 1, "یعنی": 1}
    assert m.hedge_counts == {"شاید": 1}
    assert m.sentence_count == 3


def test_urdu_normalize_drops_diacritics_and_unifies_letters() -> None:
    assert language.normalize("اُم،") == "ام"
    assert language.normalize("كيا") == "کیا"  # Arabic kaf and yeh become Urdu letters


def test_lexicons_keep_yes_and_no_as_words() -> None:
    assert {"yes", "no"} <= language.load_lexicon("en").stopwords


@pytest.mark.parametrize("lang,word", [("en", "um"), ("de", "ähm"), ("ur", "یعنی")])
def test_whisper_prompt_per_language(lang: str, word: str) -> None:
    assert word in transcribe.filler_prompt(lang).lower()


def test_coaching_prompt_asks_for_the_reader_language() -> None:
    assert report_llm.system_prompt("en") == report_llm.SYSTEM_PROMPT
    assert "German" in report_llm.system_prompt("de")
    assert "Urdu script" in report_llm.system_prompt("ur")
