"""Emotion in the voice with a small speech emotion model (estimate).

superb/wav2vec2-base-superb-er was trained on acted English speech (IEMOCAP)
with four classes: neutral, happy, angry and sad. It listens to 4 second
windows that contain speech. Like every emotion model, it reads acted emotion
better than everyday speech, so the app shows it as an estimate.
"""

from __future__ import annotations

import gc
import importlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from app.schemas.metrics import EmotionPoint, VoiceEmotionMetrics
from app.schemas.transcript import Transcript

MODEL_NAME = "superb/wav2vec2-base-superb-er"
SAMPLE_RATE = 16_000
WINDOW_S = 4.0
MIN_SPEECH_SHARE = 0.4  # skip windows that are mostly silence
LABELS = {"neu": "neutral", "hap": "happy", "ang": "angry", "sad": "sad"}
DOMINANT_MIN = 0.4
DOMINANT_MARGIN = 0.1


def speech_windows(transcript: Transcript, duration_s: float) -> list[tuple[float, float]]:
    """Windows of WINDOW_S seconds where words cover enough of the time."""
    spans = [(w.start, w.end) for w in transcript.words]
    out: list[tuple[float, float]] = []
    t = 0.0
    while t < duration_s:
        end = min(duration_s, t + WINDOW_S)
        covered = sum(max(0.0, min(e, end) - max(s, t)) for s, e in spans)
        if end - t >= 1.5 and covered / (end - t) >= MIN_SPEECH_SHARE:
            out.append((t, end))
        t += WINDOW_S
    return out


def summarize(
    windows: list[tuple[float, float]], probs: list[dict[str, float]]
) -> VoiceEmotionMetrics:
    """Pure aggregation, unit tested."""
    names = list(LABELS.values())
    if not probs:
        return VoiceEmotionMetrics(model=MODEL_NAME, emotions={}, dominant="neutral", timeline=[])
    avg = {n: round(float(np.mean([p.get(n, 0.0) for p in probs])), 3) for n in names}
    timeline = []
    for (s, e), p in zip(windows, probs, strict=True):
        top = max(p, key=lambda k: p[k])
        timeline.append(EmotionPoint(t=round((s + e) / 2, 2), emotion=top, share=round(p[top], 3)))
    # Call a non-neutral emotion dominant only when it clearly beats neutral;
    # a near tie is reported as neutral rather than as, say, "angry".
    top = max((k for k in avg if k != "neutral"), key=lambda k: avg[k])
    dominant = (
        top
        if avg[top] >= DOMINANT_MIN and avg[top] - avg["neutral"] >= DOMINANT_MARGIN
        else "neutral"
    )
    return VoiceEmotionMetrics(model=MODEL_NAME, emotions=avg, dominant=dominant, timeline=timeline)


@lru_cache(maxsize=1)
def load_model(models_dir: str) -> tuple[Any, Any]:
    tf: Any = importlib.import_module("transformers")
    opts: dict[str, Any] = {"cache_dir": str(Path(models_dir) / "hf")}
    try:
        fe = tf.AutoFeatureExtractor.from_pretrained(MODEL_NAME, local_files_only=True, **opts)
        model = tf.AutoModelForAudioClassification.from_pretrained(
            MODEL_NAME, local_files_only=True, **opts
        )
    except Exception:
        fe = tf.AutoFeatureExtractor.from_pretrained(MODEL_NAME, **opts)
        model = tf.AutoModelForAudioClassification.from_pretrained(MODEL_NAME, **opts)
    return fe, model.eval()


def classify(
    audio: npt.NDArray[np.float32], windows: list[tuple[float, float]], models_dir: Path
) -> list[dict[str, float]]:
    import torch

    fe, model = load_model(str(models_dir))
    id2label = model.config.id2label
    out = []
    for s, e in windows:
        chunk = audio[int(s * SAMPLE_RATE) : int(e * SAMPLE_RATE)]
        inputs = fe(chunk, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.inference_mode():
            p = model(**inputs).logits.softmax(-1)[0].tolist()
        out.append({LABELS.get(id2label[i], id2label[i]): round(v, 4) for i, v in enumerate(p)})
    return out


def run(audio_path: Path, transcript: Transcript, models_dir: Path) -> VoiceEmotionMetrics:
    from app.pipeline.transcribe import load_wav

    windows = speech_windows(transcript, transcript.duration_s)
    try:
        probs = classify(load_wav(audio_path), windows, models_dir) if windows else []
    finally:
        load_model.cache_clear()
        gc.collect()
    return summarize(windows, probs)
