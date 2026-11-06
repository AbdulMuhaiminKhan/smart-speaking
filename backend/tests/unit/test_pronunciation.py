import pytest

from app.pipeline import pronunciation as pr
from app.schemas.transcript import Segment, Transcript, Word


def test_normalize_phones_maps_spelling_variants() -> None:
    assert pr.normalize_phones(["ɐ", "ˈɑː", "ɚ", "aɪə"]) == ["ə", "ɑ", "ə", "ɹ", "aɪ", "ə"]


def test_phone_similarity() -> None:
    assert pr.phone_similarity(["k", "æ", "t"], ["k", "æ", "t"]) == 1.0
    assert pr.phone_similarity(["k", "æ", "t"], ["k", "ɛ", "t"]) == pytest.approx(
        1 - 0.4 / 3, abs=0.01
    )
    assert pr.phone_similarity(["k", "æ", "t"], ["d", "ɔ", "g"]) == 0.0
    assert pr.phone_similarity([], ["a"]) == 0.0


def test_ctc_collapse() -> None:
    assert pr.ctc_collapse(
        ["<pad>", "k", "k", "<pad>", "æ", "æ", "t", "<pad>", "t"], {"<pad>"}
    ) == ["k", "æ", "t", "t"]


def test_align_words_is_robust_to_extra_phones_at_edges() -> None:
    expected = [["h", "ɛ", "l", "oʊ"], ["w", "ɜː", "l", "d"]]
    heard = ["ə", "m", "h", "ɛ", "l", "o", "w", "ɜ", "l", "d", "s"]  # noise before and after
    out = pr.align_words(expected, heard)
    assert [s for s, _ in out] == [1.0, 1.0]
    assert out[0][1] == ["h", "ɛ", "l", "o"]


def test_align_words_flags_the_wrong_word() -> None:
    expected = [["h", "ɛ", "l", "oʊ"], ["w", "ɜː", "l", "d"]]
    heard = ["h", "ɛ", "l", "o", "v", "æ", "n"]
    good, bad = pr.align_words(expected, heard)
    assert good[0] == 1.0
    assert bad[0] < pr.MISPRONOUNCED_BELOW


@pytest.mark.parametrize(
    "sim,prob,expected",
    [(0.3, 0.99, "mispronounced"), (0.6, 0.3, "unclear"), (0.6, 0.9, None), (0.9, 0.1, None)],
)
def test_judge(sim: float, prob: float, expected: str | None) -> None:
    assert pr.judge(sim, prob) == expected


def w(text: str, start: float, prob: float = 0.95) -> Word:
    return Word(text=text, start=start, end=start + 0.4, probability=prob)


@pytest.mark.parametrize(
    "word,start,ok",
    [
        ("energy", False, True),
        ("the", False, False),
        ("LED", False, False),
        ("Khan", False, False),
        ("Today", True, True),
        ("42", False, False),
        ("um,", False, False),
    ],
)
def test_checkable(word: str, start: bool, ok: bool) -> None:
    from app.pipeline import language

    lex = language.load_lexicon("en")
    skip = (
        {" ".join(p) for p in lex.fillers_always} | set(lex.fillers_contextual) | set(lex.stopwords)
    )
    assert pr.checkable(w(word, 0), language.normalize(word), skip, start) is ok


def transcript(words: list[Word]) -> Transcript:
    return Transcript(
        language="en",
        duration_s=10,
        model="t",
        segments=[Segment(id=0, start=0, end=words[-1].end, text="", words=words)],
    )


def test_analyze_flags_mismatch_with_frames() -> None:
    words = [w("Today", 0.0), w("energy", 0.5), w("matters", 1.0)]
    expected = {
        "today": ["t", "ə", "d", "eɪ"],
        "energy": ["ɛ", "n", "ɚ", "dʒ", "i"],
        "matters": ["m", "æ", "ɾ", "ɚ", "z"],
    }
    # 20 ms frames: say "today", then garbage instead of "energy", then "matters"
    frames = (
        ["t"] * 5
        + ["ə"] * 5
        + ["d"] * 5
        + ["eɪ"] * 5
        + ["<pad>"] * 5
        + ["b"] * 5
        + ["ʊ"] * 5
        + ["k"] * 5
        + ["<pad>"] * 5
        + ["m"] * 5
        + ["æ"] * 5
        + ["t"] * 5
        + ["ə"] * 5
        + ["ɹ"] * 5
        + ["z"] * 5
    )
    m = pr.analyze(transcript(words), frames, expected, {"<pad>"})
    assert m.method == "phonemes" and m.words_checked == 3
    assert [u.word for u in m.unclear_words] == ["energy"]
    assert m.unclear_words[0].reason == "mispronounced"


def test_analyze_without_model_uses_whisper_confidence() -> None:
    words = [w("energy", 0.0, prob=0.2), w("matters", 0.5)]
    expected = {"energy": ["ɛ", "n", "ɚ", "dʒ", "i"], "matters": ["m", "æ", "ɾ", "ɚ", "z"]}
    m = pr.analyze(transcript(words), None, expected, set())
    assert m.method == "whisper_only"
    assert [u.word for u in m.unclear_words] == ["energy"]
