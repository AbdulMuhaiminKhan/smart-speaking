"""Step 2: speech to text with faster-whisper, keeping word timestamps and fillers.

Whisper tends to "clean up" speech and drop filler words. Two things push it
to keep them: an initial prompt written in a disfluent style, and turning off
conditioning on previous text (which also reduces repetition loops).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from app.pipeline.errors import NoSpeechError
from app.schemas.transcript import Segment, Transcript, Word

FILLER_PROMPT = (
    "Umm, so, uh, I was like, you know, thinking about it. Hmm, basically, "
    "I mean, it's, uh, sort of... actually, okay, um, let me start."
)

ProgressFn = Callable[[float], None]


class _WordLike(Protocol):
    word: str
    start: float
    end: float
    probability: float


class _SegmentLike(Protocol):
    id: int
    start: float
    end: float
    text: str
    words: list[_WordLike] | None
    avg_logprob: float
    no_speech_prob: float


def detect_device(preference: str = "auto") -> tuple[str, str]:
    """Return (device, compute_type). GPU is used only if CUDA is really available."""
    if preference == "cpu":
        return "cpu", "int8"
    try:
        import ctranslate2

        has_cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:  # pragma: no cover - depends on the machine
        has_cuda = False
    if has_cuda and preference in {"auto", "cuda"}:
        return "cuda", "float16"
    return "cpu", "int8"


@lru_cache(maxsize=2)
def load_model(size: str, models_dir: str, device_pref: str = "auto") -> Any:
    from faster_whisper import WhisperModel

    device, compute_type = detect_device(device_pref)
    kwargs = {
        "device": device,
        "compute_type": compute_type,
        "download_root": str(Path(models_dir) / "whisper"),
    }
    try:
        # Use the cached copy without contacting Hugging Face; download only once.
        return WhisperModel(size, local_files_only=True, **kwargs)
    except Exception:
        return WhisperModel(size, **kwargs)


def load_wav(path: Path) -> Any:
    """Read the 16 kHz mono WAV from preprocess as float32 in [-1, 1].

    Passing samples (not a path) keeps faster-whisper from decoding with PyAV,
    since ffmpeg already did that work in step 1.
    """
    import wave

    import numpy as np

    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError("expected 16-bit mono WAV")
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def clean_word(text: str) -> str:
    return text.strip()


def build_transcript(
    segments: Iterable[_SegmentLike],
    *,
    language: str,
    language_probability: float | None,
    duration_s: float,
    model: str,
    on_progress: ProgressFn | None = None,
) -> Transcript:
    """Convert faster-whisper output into our Transcript. Pure apart from progress calls."""
    out: list[Segment] = []
    for seg in segments:
        words = [
            Word(
                text=clean_word(w.word),
                start=round(float(w.start), 3),
                end=round(float(w.end), 3),
                probability=min(1.0, max(0.0, float(w.probability))),
            )
            for w in (seg.words or [])
            if clean_word(w.word)
        ]
        out.append(
            Segment(
                id=len(out),
                start=round(float(seg.start), 3),
                end=round(float(seg.end), 3),
                text=seg.text.strip(),
                words=words,
                avg_logprob=float(seg.avg_logprob),
                no_speech_prob=float(seg.no_speech_prob),
            )
        )
        if on_progress and duration_s > 0:
            on_progress(min(1.0, float(seg.end) / duration_s))

    transcript = Transcript(
        language=language,
        language_probability=language_probability,
        duration_s=duration_s,
        model=model,
        segments=out,
    )
    if not transcript.words:
        raise NoSpeechError()
    return transcript


def run(
    audio_path: Path,
    *,
    model_size: str,
    models_dir: Path,
    language: str | None = "en",
    device_pref: str = "auto",
    on_progress: ProgressFn | None = None,
) -> Transcript:
    model = load_model(model_size, str(models_dir), device_pref)
    segments, info = model.transcribe(
        load_wav(audio_path),
        language=language,
        word_timestamps=True,
        initial_prompt=FILLER_PROMPT,
        condition_on_previous_text=False,
        vad_filter=False,  # keep silences and fillers; pauses are measured later
        beam_size=5,
    )
    return build_transcript(
        segments,
        language=info.language,
        language_probability=getattr(info, "language_probability", None),
        duration_s=float(info.duration),
        model=model_size,
        on_progress=on_progress,
    )
