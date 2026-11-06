"""Step 5: pronunciation estimate.

For each word Whisper heard, we compare the phonemes a wav2vec2 phoneme model
recognizes in that stretch of audio against the phonemes espeak expects for
the word. A word is flagged only when the phonemes differ a lot, or when they
differ somewhat and Whisper was also unsure. Accents differ from espeak's
reference, so the UI presents this as an estimate, never as a hard score.
"""

from __future__ import annotations

import gc
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from app.pipeline import language as lang_mod
from app.schemas.metrics import PronunciationMetrics, UnclearWord
from app.schemas.transcript import Transcript, Word

log = logging.getLogger(__name__)

MODEL_NAME = "facebook/wav2vec2-lv-60-espeak-cv-ft"
SAMPLE_RATE = 16_000
FRAME_S = 0.02  # wav2vec2 outputs one frame per 20 ms
CHUNK_S = 20.0
PAD_S = 0.04  # widen each word's window a little; Whisper's edges are approximate
MIN_PHONES = 3  # shorter words are too short to judge
MISPRONOUNCED_BELOW = 0.45  # flagged on phonemes alone
UNCLEAR_BELOW = 0.65  # flagged when Whisper is also unsure
LOW_CONFIDENCE = 0.5
ESPEAK_VOICES = {"en": "en-us", "es": "es", "fr": "fr-fr", "de": "de", "it": "it", "pt": "pt"}

# Phones that sound alike or that espeak and the model spell differently.
_NORMALIZE = {
    "ɐ": "ə",
    "ᵻ": "ɪ",
    "ɚ": "ə ɹ",
    "ɝ": "ɜ ɹ",
    "ɾ": "t",
    "ʔ": "t",
    "ɫ": "l",
    "oʊ": "o",
    "əʊ": "o",
    "ɔː": "ɔ",
    "ɑː": "ɑ",
    "iː": "i",
    "uː": "u",
    "ɜː": "ɜ",
    "aɪə": "aɪ ə",
    "aʊə": "aʊ ə",
    "ɔːɹ": "ɔ ɹ",
    "ɑːɹ": "ɑ ɹ",
    "ɪɹ": "ɪ ɹ",
    "ɛɹ": "ɛ ɹ",
    "ʊɹ": "ʊ ɹ",
    "n̩": "n",
    "l̩": "l",
    "ɡ": "g",
}
_CLOSE = [
    {"ə", "ʌ", "ɪ"},
    {"i", "ɪ"},
    {"u", "ʊ"},
    {"ɛ", "æ", "e"},
    {"ɑ", "ɔ", "ɒ", "a"},
    {"t", "d"},
    {"θ", "ð"},
    {"s", "z"},
    {"o", "ɔ"},
]


def normalize_phones(phones: list[str]) -> list[str]:
    out: list[str] = []
    for p in phones:
        p = p.replace("ˈ", "").replace("ˌ", "")
        mapped = _NORMALIZE.get(p, p.replace("ː", ""))
        out.extend(x for x in mapped.split() if x)
    return out


def _sub_cost(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return 0.4 if any(a in g and b in g for g in _CLOSE) else 1.0


def phone_similarity(expected: list[str], heard: list[str]) -> float:
    """1 minus the weighted edit distance, divided by the longer sequence."""
    e, h = normalize_phones(expected), normalize_phones(heard)
    if not e and not h:
        return 1.0
    if not e or not h:
        return 0.0
    prev = [float(j) for j in range(len(h) + 1)]
    for i in range(1, len(e) + 1):
        cur = [float(i)] + [0.0] * len(h)
        for j in range(1, len(h) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + _sub_cost(e[i - 1], h[j - 1]))
        prev = cur
    return round(max(0.0, 1.0 - prev[-1] / max(len(e), len(h))), 3)


def align_words(expected: list[list[str]], heard: list[str]) -> list[tuple[float, list[str]]]:
    """Align the heard phones of a stretch of audio against the expected phones
    of the words in it, and return (similarity, heard phones) per word.

    Aligning a whole segment at once is robust to Whisper's word timestamps
    being slightly off. Heard phones before the first and after the last
    expected phone are free (the audio window is padded).
    """
    exp: list[tuple[int, str]] = [
        (wi, p) for wi, phones in enumerate(expected) for p in normalize_phones(phones)
    ]
    hrd = normalize_phones(heard)
    n, m = len(exp), len(hrd)
    # cost[i][j]: best cost aligning exp[:i] with hrd[:j]; leading heard phones are free.
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    move = [[0] * (m + 1) for _ in range(n + 1)]  # 1 diag, 2 up (deletion), 3 left (insertion)
    for i in range(1, n + 1):
        cost[i][0] = float(i)
        move[i][0] = 2
    for i in range(1, n + 1):
        ei = exp[i - 1][1]
        row, prow = cost[i], cost[i - 1]
        for j in range(1, m + 1):
            d = prow[j - 1] + _sub_cost(ei, hrd[j - 1])
            u = prow[j] + 1.0
            left = row[j - 1] + 1.0
            best, mv = d, 1
            if u < best:
                best, mv = u, 2
            if left < best:
                best, mv = left, 3
            row[j] = best
            move[i][j] = mv
    # Trailing heard phones are free: end anywhere on the last row.
    j = min(range(m + 1), key=lambda k: cost[n][k]) if n else 0
    per_cost = [0.0] * len(expected)
    per_heard: list[list[str]] = [[] for _ in expected]
    i = n
    while i > 0:
        mv = move[i][j] if j > 0 else 2
        wi = exp[i - 1][0]
        if mv == 1:
            per_cost[wi] += _sub_cost(exp[i - 1][1], hrd[j - 1])
            per_heard[wi].append(hrd[j - 1])
            i, j = i - 1, j - 1
        elif mv == 2:
            per_cost[wi] += 1.0
            i -= 1
        else:
            per_cost[wi] += 1.0  # extra phone inside this word
            per_heard[wi].append(hrd[j - 1])
            j -= 1
    out: list[tuple[float, list[str]]] = []
    for wi, phones in enumerate(expected):
        length = max(1, len(normalize_phones(phones)))
        out.append((round(max(0.0, 1.0 - per_cost[wi] / length), 3), per_heard[wi][::-1]))
    return out


def ctc_collapse(tokens: list[str], blank: set[str]) -> list[str]:
    out: list[str] = []
    last: str | None = None
    for t in tokens:
        if t != last and t not in blank:
            out.append(t)
        last = t
    return out


def judge(similarity: float, whisper_prob: float) -> str | None:
    if similarity < MISPRONOUNCED_BELOW:
        return "mispronounced"
    if similarity < UNCLEAR_BELOW and whisper_prob < LOW_CONFIDENCE:
        return "unclear"
    return None


def checkable(word: Word, norm: str, skip_words: set[str], sentence_start: bool = False) -> bool:
    """Words we can judge fairly. Skipped: fillers and short function words (often
    reduced in natural speech), numbers, acronyms, and capitalized words in mid
    sentence (names, which espeak often gets wrong)."""
    raw = word.text.strip(".,!?;:\"'()")
    if not norm or norm.isdigit() or norm in skip_words or len(norm) < 3:
        return False
    if raw.isupper() and len(raw) > 1:
        return False
    return not (raw[:1].isupper() and not sentence_start and norm != "i")


# ---- models (impure) --------------------------------------------------------


def _espeak_library() -> None:
    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return
    if sys.platform == "darwin":
        for p in ("/opt/homebrew/lib/libespeak-ng.dylib", "/usr/local/lib/libespeak-ng.dylib"):
            if Path(p).exists():
                os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = p
                return


def expected_phones(words: list[str], language: str) -> dict[str, list[str]]:
    from phonemizer.backend import EspeakBackend
    from phonemizer.separator import Separator

    _espeak_library()
    backend = EspeakBackend(ESPEAK_VOICES.get(language, "en-us"), with_stress=False)
    unique = sorted(set(words))
    out = backend.phonemize(
        unique, separator=Separator(phone=" ", word="", syllable=""), strip=True
    )
    return {w: p.split() for w, p in zip(unique, out, strict=True)}


@lru_cache(maxsize=1)
def load_model(models_dir: str) -> tuple[Any, Any, Any]:
    import importlib

    import torch

    tf: Any = importlib.import_module("transformers")  # untyped heavy import
    cache = str(Path(models_dir) / "hf")

    def load(local_only: bool) -> tuple[Any, Any, Any]:
        opts: dict[str, Any] = {"cache_dir": cache, "local_files_only": local_only}
        return (
            tf.Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME, **opts),
            tf.AutoTokenizer.from_pretrained(MODEL_NAME, **opts),
            tf.Wav2Vec2ForCTC.from_pretrained(MODEL_NAME, **opts),
        )

    try:
        fe, tok, model = load(True)  # cached copy, no network
    except Exception:
        fe, tok, model = load(False)  # first run: download once
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return fe, tok, model.eval().to(device)


def unload_model() -> None:
    load_model.cache_clear()
    gc.collect()


def frame_tokens(audio: npt.NDArray[np.float32], models_dir: Path) -> list[str]:
    """Greedy phoneme token per 20 ms frame for the whole recording."""
    import torch

    fe, tok, model = load_model(str(models_dir))
    device = next(model.parameters()).device
    tokens: list[str] = []
    step = int(CHUNK_S * SAMPLE_RATE)
    for start in range(0, len(audio), step):
        chunk = audio[start : start + step]
        if len(chunk) < SAMPLE_RATE * 0.1:
            break
        values = fe(chunk, sampling_rate=SAMPLE_RATE, return_tensors="pt").input_values.to(device)
        with torch.inference_mode():
            ids = model(values).logits[0].argmax(-1).tolist()
        tokens.extend(tok.convert_ids_to_tokens(ids))
        expected_frames = round(len(chunk) / SAMPLE_RATE / FRAME_S)
        # Keep frame count aligned with time even if the model rounds differently.
        if len(ids) < expected_frames:
            tokens.extend([tok.pad_token] * (expected_frames - len(ids)))
        elif len(ids) > expected_frames:
            del tokens[len(tokens) - (len(ids) - expected_frames) :]
    return tokens


def analyze(
    transcript: Transcript,
    frames: list[str] | None,
    expected: dict[str, list[str]],
    blank: set[str],
    language: str = "en",
) -> PronunciationMetrics:
    """Pure comparison step. frames=None means the phoneme model was not available."""
    lex = lang_mod.load_lexicon(language)
    skip = (
        {" ".join(p) for p in lex.fillers_always} | set(lex.fillers_contextual) | set(lex.stopwords)
    )
    words = transcript.words
    low_conf = sum(w.probability < LOW_CONFIDENCE for w in words)
    flagged: list[UnclearWord] = []
    sims: list[float] = []
    checked = 0
    for seg in transcript.segments:
        seg_words = [w for w in seg.words if lang_mod.normalize(w.text)]
        if not seg_words:
            continue
        norms = [lang_mod.normalize(w.text) for w in seg_words]
        exp_phones = [expected.get(nm, []) for nm in norms]
        if frames is not None:
            a = max(0, int((seg_words[0].start - 0.3) / FRAME_S))
            b = min(len(frames), int((seg_words[-1].end + 0.3) / FRAME_S) + 1)
            aligned = align_words(exp_phones, ctc_collapse(frames[a:b], blank))
        for k, (w, norm) in enumerate(zip(seg_words, norms, strict=True)):
            exp = exp_phones[k]
            prev = seg_words[k - 1].text if k else ""
            starts = k == 0 or prev.rstrip("\"')").endswith((".", "?", "!"))
            if not checkable(w, norm, skip, starts) or len(exp) < MIN_PHONES:
                continue
            checked += 1
            clean = w.text.strip(".,!?;:\"'")
            if frames is None:
                if w.probability < 0.3:
                    flagged.append(
                        UnclearWord(
                            word=clean,
                            start=w.start,
                            end=w.end,
                            expected=" ".join(exp),
                            heard="",
                            similarity=0.0,
                            whisper_probability=w.probability,
                            reason="unclear",
                        )
                    )
                continue
            sim, heard = aligned[k]
            sims.append(sim)
            reason = judge(sim, w.probability)
            if reason == "mispronounced" or reason == "unclear":
                flagged.append(
                    UnclearWord(
                        word=clean,
                        start=w.start,
                        end=w.end,
                        expected=" ".join(exp),
                        heard=" ".join(heard),
                        similarity=sim,
                        whisper_probability=round(w.probability, 3),
                        reason=reason,
                    )
                )
    n_words = max(1, len(words))
    return PronunciationMetrics(
        method="phonemes" if frames is not None else "whisper_only",
        words_checked=checked,
        mean_similarity=round(sum(sims) / len(sims), 3) if sims else None,
        low_confidence_ratio=round(low_conf / n_words, 3),
        unclear_per_100_words=round(len(flagged) / n_words * 100, 2),
        unclear_words=flagged,
    )


def run(
    audio_path: Path, transcript: Transcript, models_dir: Path, language: str = "en"
) -> PronunciationMetrics:
    from app.pipeline.transcribe import load_wav

    words = [lang_mod.normalize(w.text) for w in transcript.words]
    expected = expected_phones([w for w in words if w], language)
    try:
        frames = frame_tokens(load_wav(audio_path), models_dir)
        _, tok, _ = load_model(str(models_dir))
        blank = {tok.pad_token, "<s>", "</s>", "<unk>", "|"}
    except Exception:
        log.exception("phoneme model unavailable; falling back to Whisper confidence only")
        frames, blank = None, set()
    finally:
        unload_model()  # 1.2 GB; free it before the body step
    return analyze(transcript, frames, expected, blank, language)
