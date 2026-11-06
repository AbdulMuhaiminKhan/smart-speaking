"""Live mode: rolling transcription of a microphone stream for live WPM and fillers.

The browser sends 16 kHz mono int16 PCM. We cut the stream at quiet moments
(so words are not split), transcribe each chunk with Whisper tiny, and keep a
running word list. Nothing is stored; the full recording is analyzed after
the session through the normal upload path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from app.pipeline import language
from app.schemas.transcript import Word

SAMPLE_RATE = 16_000
MIN_CHUNK_S = 3.0  # wait for at least this much new audio
MAX_CHUNK_S = 8.0  # cut here even without a quiet moment
SPLIT_SEARCH_S = 1.5  # look for a quiet point in the last part of the chunk
FRAME_S = 0.1
SILENCE_RMS = 0.01  # quieter frames (float scale) count as silence
RECENT_WINDOW_S = 30.0

# (samples float32, offset seconds) -> words with absolute times
TranscribeFn = Callable[[npt.NDArray[np.float32], float], list[Word]]


@dataclass
class LiveStats:
    elapsed_s: float
    words: int
    wpm: float | None  # since the first word
    wpm_recent: float | None  # last 30 seconds
    fillers: int
    filler_counts: dict[str, int]
    last_text: str
    speaking: bool

    def as_dict(self) -> dict[str, object]:
        return {"type": "stats", **self.__dict__}


@dataclass
class LiveTranscriber:
    transcribe: TranscribeFn
    language: str = "en"
    _pending: npt.NDArray[np.float32] = field(default_factory=lambda: np.zeros(0, np.float32))
    _committed_s: float = 0.0  # stream time where _pending starts
    _received_s: float = 0.0
    _words: list[Word] = field(default_factory=list)
    _last_text: str = ""

    def feed(self, pcm16: bytes) -> None:
        samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        self._pending = np.concatenate([self._pending, samples])
        self._received_s += len(samples) / SAMPLE_RATE

    def _split_point(self) -> int | None:
        n = len(self._pending)
        if n < MIN_CHUNK_S * SAMPLE_RATE:
            return None
        frame = int(FRAME_S * SAMPLE_RATE)
        search_from = max(0, n - int(SPLIT_SEARCH_S * SAMPLE_RATE))
        # Latest quiet frame inside the search window.
        for start in range(n - frame, search_from - 1, -frame):
            chunk = self._pending[start : start + frame]
            if float(np.sqrt(np.mean(chunk**2))) < SILENCE_RMS:
                return start + frame // 2
        if n >= MAX_CHUNK_S * SAMPLE_RATE:
            return n
        return None

    def ready(self) -> bool:
        return self._split_point() is not None

    def step(self, final: bool = False) -> bool:
        """Transcribe one chunk if there is one. Returns True if words were added."""
        cut = len(self._pending) if final and len(self._pending) else self._split_point()
        if cut is None:
            return False
        chunk, self._pending = self._pending[:cut], self._pending[cut:]
        offset = self._committed_s
        self._committed_s += cut / SAMPLE_RATE
        if float(np.sqrt(np.mean(chunk**2))) < SILENCE_RMS:
            return False  # all silence, skip the model call
        words = self.transcribe(chunk, offset)
        if words:
            self._words.extend(words)
            self._last_text = " ".join(w.text for w in words)
        return bool(words)

    def stats(self) -> LiveStats:
        words = self._words
        now = self._received_s
        wpm: float | None = None
        recent: float | None = None
        if words:
            spoken = max(now - words[0].start, 1.0)
            wpm = round(len(words) / spoken * 60, 0) if spoken >= 5 else None
            window = min(RECENT_WINDOW_S, spoken)
            n_recent = sum(1 for w in words if w.end >= now - window)
            recent = round(n_recent / window * 60, 0) if window >= 5 else None

        lex = language.load_lexicon(self.language)
        norm = [language.normalize(w.text) for w in words]
        fillers = language.find_fillers(words, norm, lex)
        counts: dict[str, int] = {}
        for f in fillers:
            counts[f.phrase] = counts.get(f.phrase, 0) + 1

        tail = self._pending[-int(SAMPLE_RATE * 0.5) :]
        speaking = bool(len(tail)) and float(np.sqrt(np.mean(tail**2))) >= SILENCE_RMS
        return LiveStats(
            elapsed_s=round(now, 1),
            words=len(words),
            wpm=wpm,
            wpm_recent=recent,
            fillers=len(fillers),
            filler_counts=counts,
            last_text=self._last_text,
            speaking=speaking,
        )


def whisper_transcribe_fn(model_size: str, models_dir: str, lang: str = "en") -> TranscribeFn:
    from app.pipeline import transcribe as tr

    model = tr.load_model(model_size, models_dir, "auto")

    def run(samples: npt.NDArray[np.float32], offset: float) -> list[Word]:
        segments, _ = model.transcribe(
            samples,
            language=lang,
            word_timestamps=True,
            initial_prompt=tr.FILLER_PROMPT,
            condition_on_previous_text=False,
            vad_filter=False,
            beam_size=1,
        )
        out: list[Word] = []
        for seg in segments:
            for w in seg.words or []:
                text = w.word.strip()
                if text:
                    out.append(
                        Word(
                            text=text,
                            start=round(offset + float(w.start), 3),
                            end=round(offset + float(w.end), 3),
                            probability=min(1.0, max(0.0, float(w.probability))),
                        )
                    )
        return out

    return run
