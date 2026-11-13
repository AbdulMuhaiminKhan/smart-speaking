"""Step 4: filler words, hedges, repetition, vocabulary, sentences and script match.

Word lists live in lexicons/<lang>.yaml (en, de, ur) so other languages can be
added without code changes. Sentence clarity feedback comes from the LLM.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.schemas.metrics import LanguageMetrics, Occurrence, ScriptComparison
from app.schemas.transcript import Transcript, Word

LEXICON_DIR = Path(__file__).parent / "lexicons"
MATTR_WINDOW = 50
LONG_SENTENCE_WORDS = 30
OVERUSE_MIN_COUNT = 4
OVERUSE_MIN_SHARE = 0.02
SCRIPT_GAP_MIN_WORDS = 3

SUPPORTED_LANGUAGES = ("en", "de", "ur")

_PUNCT = re.compile(r"[^\w']+", re.UNICODE)
# Latin plus the Urdu full stop (U+06D4) and question mark (U+061F).
_SENTENCE_END = (".", "?", "!", "\u06d4", "\u061f")
_COMMAS = (",", "\u060c", "\u2026", "...")  # includes the Arabic-script comma
# Arabic code points Whisper sometimes writes in place of the Urdu letters.
_URDU_LETTERS = str.maketrans({"\u064a": "\u06cc", "\u0649": "\u06cc", "\u0643": "\u06a9"})


@dataclass(frozen=True)
class Lexicon:
    fillers_always: tuple[tuple[str, ...], ...]
    fillers_contextual: frozenset[str]
    like_not_after: frozenset[str]
    like_quotative_after: frozenset[str]
    hedges: tuple[tuple[str, ...], ...]
    stopwords: frozenset[str]
    whisper_prompt: str = ""
    # Words like English "like" with their own rules (see is_contextual_filler).
    like_words: frozenset[str] = frozenset()


def _phrases(items: list[str]) -> tuple[tuple[str, ...], ...]:
    # Longest phrases first so "i think maybe" wins over "i think".
    tokens = (tuple(t for t in (normalize(x) for x in p.split()) if t) for p in items)
    return tuple(sorted((t for t in tokens if t), key=len, reverse=True))


def _words(items: list[str] | None) -> frozenset[str]:
    return frozenset(n for n in (normalize(x) for x in items or []) if n)


@lru_cache
def load_lexicon(language: str = "en") -> Lexicon:
    path = LEXICON_DIR / f"{language}.yaml"
    if not path.exists():
        path = LEXICON_DIR / "en.yaml"
    # BaseLoader keeps every value a string ("no" and "yes" are words, not booleans).
    data: dict[str, Any] = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return Lexicon(
        fillers_always=_phrases(data["fillers"]["always"]),
        fillers_contextual=_words(data["fillers"].get("contextual")),
        like_not_after=_words(data.get("like_not_filler_after")),
        like_quotative_after=_words(data.get("like_quotative_after")),
        hedges=_phrases(data["hedges"]),
        stopwords=_words(data["stopwords"]),
        whisper_prompt=str(data.get("whisper_prompt", "")).strip(),
        like_words=_words(data.get("like_words")),
    )


def normalize(text: str) -> str:
    """Lowercase, drop punctuation and Arabic-script diacritics, unify Urdu letters."""
    return _PUNCT.sub("", text.lower().replace("\u2019", "'").translate(_URDU_LETTERS))


def _has_comma(raw: str) -> bool:
    return raw.rstrip().endswith(_COMMAS)


def _sentence_start(words: list[Word], i: int) -> bool:
    return i == 0 or words[i - 1].text.rstrip("\"')").endswith(_SENTENCE_END)


def _match_phrases(
    norm: list[str], phrases: tuple[tuple[str, ...], ...], taken: set[int]
) -> list[tuple[int, int]]:
    """Return (start, length) for each non-overlapping phrase match."""
    hits: list[tuple[int, int]] = []
    i = 0
    while i < len(norm):
        for phrase in phrases:
            n = len(phrase)
            if tuple(norm[i : i + n]) == phrase and not any(j in taken for j in range(i, i + n)):
                hits.append((i, n))
                taken.update(range(i, i + n))
                i += n - 1
                break
        i += 1
    return hits


def _occ(words: list[Word], start: int, length: int, norm: list[str]) -> Occurrence:
    return Occurrence(
        phrase=" ".join(norm[start : start + length]),
        start=words[start].start,
        end=words[start + length - 1].end,
        word_index=start,
    )


def is_contextual_filler(words: list[Word], norm: list[str], i: int, lex: Lexicon) -> bool:
    w = norm[i]
    prev = norm[i - 1] if i > 0 else ""
    prev_comma = i > 0 and _has_comma(words[i - 1].text)
    own_comma = _has_comma(words[i].text)
    if w in lex.like_words:
        if prev in lex.like_quotative_after:
            return True
        if prev in lex.like_not_after:
            return False
        return prev_comma or own_comma
    # Other contextual words ("So, ...", "Also, ...", "اچھا، ...") count only at the
    # start of a sentence and followed by a comma.
    return _sentence_start(words, i) and own_comma


def find_fillers(words: list[Word], norm: list[str], lex: Lexicon) -> list[Occurrence]:
    taken: set[int] = set()
    hits = _match_phrases(norm, lex.fillers_always, taken)
    for i, w in enumerate(norm):
        if (
            i not in taken
            and w in lex.fillers_contextual
            and is_contextual_filler(words, norm, i, lex)
        ):
            hits.append((i, 1))
            taken.add(i)
    return sorted((_occ(words, s, n, norm) for s, n in hits), key=lambda o: o.start)


def _ends_phrase(raw: str) -> bool:
    # "Heating. Heating is..." repeats on purpose across a break; not a stumble.
    return raw.rstrip("\"')").endswith((*_SENTENCE_END, ",", ";", ":", "\u060c", "\u061b"))


def find_repetitions(words: list[Word], norm: list[str], skip: set[int]) -> list[Occurrence]:
    """Immediate repeats such as "the the" or "I was, I was"."""
    out: list[Occurrence] = []
    i = 0
    while i < len(norm) - 1:
        if i in skip or not norm[i]:
            i += 1
            continue
        for n in (2, 1):  # bigrams first
            a, b = norm[i : i + n], norm[i + n : i + 2 * n]
            crosses_break = _ends_phrase(words[i + n - 1].text)
            if (
                len(b) == n
                and a == b
                and not crosses_break
                and not any(j in skip for j in range(i, i + 2 * n))
            ):
                out.append(
                    Occurrence(
                        phrase=" ".join(a + b),
                        start=words[i].start,
                        end=words[i + 2 * n - 1].end,
                        word_index=i,
                    )
                )
                i += 2 * n - 1
                break
        i += 1
    return out


def mattr(tokens: list[str], window: int = MATTR_WINDOW) -> float:
    """Moving-average type-token ratio: vocabulary variety that does not drop with length."""
    if not tokens:
        return 0.0
    if len(tokens) <= window:
        return len(set(tokens)) / len(tokens)
    counts = Counter(tokens[:window])
    total = len(counts) / window
    for i in range(window, len(tokens)):
        out_tok, in_tok = tokens[i - window], tokens[i]
        counts[out_tok] -= 1
        if counts[out_tok] == 0:
            del counts[out_tok]
        counts[in_tok] += 1
        total += len(counts) / window
    return total / (len(tokens) - window + 1)


def split_sentences(words: list[Word]) -> list[tuple[int, int]]:
    """(start index, word count) per sentence, split on . ? ! in Whisper's punctuation."""
    out: list[tuple[int, int]] = []
    start = 0
    for i, w in enumerate(words):
        if w.text.rstrip("\"')").endswith(_SENTENCE_END):
            out.append((start, i - start + 1))
            start = i + 1
    if start < len(words):
        out.append((start, len(words) - start))
    return out


def compare_script(script: str, spoken: list[str]) -> ScriptComparison:
    expected = [t for t in (normalize(x) for x in script.split()) if t]
    if not expected:
        return ScriptComparison(coverage=0.0, extra_ratio=0.0, skipped=[], added=[])
    matcher = difflib.SequenceMatcher(None, expected, spoken, autojunk=False)
    matched = sum(b.size for b in matcher.get_matching_blocks())
    skipped: list[str] = []
    added: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"delete", "replace"} and i2 - i1 >= SCRIPT_GAP_MIN_WORDS:
            skipped.append(" ".join(expected[i1:i2][:15]))
        if tag in {"insert", "replace"} and j2 - j1 >= SCRIPT_GAP_MIN_WORDS:
            added.append(" ".join(spoken[j1:j2][:15]))
    return ScriptComparison(
        coverage=round(matched / len(expected), 3),
        extra_ratio=round(1 - matched / len(spoken), 3) if spoken else 0.0,
        skipped=skipped,
        added=added,
    )


def run(
    transcript: Transcript,
    *,
    speaking_time_s: float,
    language: str = "en",
    script_text: str | None = None,
) -> LanguageMetrics:
    lex = load_lexicon(language)
    words = sorted(transcript.words, key=lambda w: w.start)
    norm = [normalize(w.text) for w in words]

    fillers = find_fillers(words, norm, lex)
    filler_idx = {o.word_index + k for o in fillers for k in range(len(o.phrase.split()))}

    hedges = [_occ(words, s, n, norm) for s, n in _match_phrases(norm, lex.hedges, set(filler_idx))]
    repetitions = find_repetitions(words, norm, filler_idx)

    content = [t for i, t in enumerate(norm) if t and i not in filler_idx]
    counts = Counter(t for t in content if t not in lex.stopwords and len(t) > 2)
    threshold = max(OVERUSE_MIN_COUNT, OVERUSE_MIN_SHARE * len(content))
    overused = {w: c for w, c in counts.most_common(10) if c >= threshold}

    sentences = split_sentences(words)
    lengths = [n for _, n in sentences]
    long_sentences = [
        Occurrence(
            phrase=" ".join(w.text for w in words[s : s + 8]) + " …",
            start=words[s].start,
            end=words[s + n - 1].end,
            word_index=s,
        )
        for s, n in sentences
        if n > LONG_SENTENCE_WORDS
    ]

    minutes = max(speaking_time_s / 60, 1e-6)
    return LanguageMetrics(
        word_count=len(words),
        fillers=fillers,
        filler_counts=dict(Counter(o.phrase for o in fillers).most_common()),
        fillers_per_min=round(len(fillers) / minutes, 2),
        hedges=hedges,
        hedge_counts=dict(Counter(o.phrase for o in hedges).most_common()),
        repetitions=repetitions,
        overused_words=overused,
        vocabulary_mattr=round(mattr(content), 3),
        unique_words=len(set(content)),
        sentence_count=len(sentences),
        avg_sentence_words=round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        long_sentences=long_sentences,
        script=compare_script(script_text, content) if script_text else None,
    )
