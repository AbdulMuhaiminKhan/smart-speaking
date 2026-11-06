import numpy as np

from app.schemas.transcript import Word
from app.services.live import SAMPLE_RATE, LiveTranscriber


def tone(seconds: float, amp: float = 0.3) -> bytes:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (np.sin(2 * np.pi * 220 * t) * amp * 32767).astype(np.int16).tobytes()


def silence(seconds: float) -> bytes:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.int16).tobytes()


class FakeModel:
    """Pretends every second of sound contains two words; first word of each chunk is 'um,'."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, float]] = []

    def __call__(self, samples: np.ndarray, offset: float) -> list[Word]:
        self.calls.append((len(samples), offset))
        n = max(1, int(len(samples) / SAMPLE_RATE * 2))
        return [
            Word(
                text="um," if i == 0 else "word",
                start=offset + i * 0.5,
                end=offset + i * 0.5 + 0.4,
                probability=0.9,
            )
            for i in range(n)
        ]


def test_waits_for_enough_audio() -> None:
    live = LiveTranscriber(transcribe=FakeModel())
    live.feed(tone(1.0))
    assert not live.ready()
    assert not live.step()


def test_cuts_at_quiet_moment() -> None:
    model = FakeModel()
    live = LiveTranscriber(transcribe=model)
    live.feed(tone(3.0) + silence(0.4) + tone(0.3))
    assert live.ready()
    assert live.step()
    cut_samples, offset = model.calls[0]
    assert offset == 0.0
    assert 3.0 * SAMPLE_RATE < cut_samples < 3.4 * SAMPLE_RATE


def test_forces_cut_after_max_chunk() -> None:
    model = FakeModel()
    live = LiveTranscriber(transcribe=model)
    live.feed(tone(8.5))
    assert live.step()
    assert model.calls[0][0] == int(8.5 * SAMPLE_RATE)


def test_silence_skips_model() -> None:
    model = FakeModel()
    live = LiveTranscriber(transcribe=model)
    live.feed(silence(4))
    assert not live.step()
    assert model.calls == []


def test_stats_count_words_and_fillers_with_offsets() -> None:
    model = FakeModel()
    live = LiveTranscriber(transcribe=model)
    for _ in range(3):
        live.feed(tone(3.0) + silence(0.5))
        live.step()
    assert [c[1] for c in model.calls][0] == 0.0
    assert model.calls[1][1] > 3.0  # second chunk starts where the first ended
    s = live.stats()
    assert s.words > 0
    assert s.fillers == 3
    assert s.filler_counts == {"um": 3}
    assert s.wpm is not None and s.wpm > 0


def test_final_flushes_remaining_audio() -> None:
    model = FakeModel()
    live = LiveTranscriber(transcribe=model)
    live.feed(tone(1.0))
    assert live.step(final=True)
    assert live.stats().words >= 1


def test_websocket_streams_stats(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.api import live as live_api

    monkeypatch.setattr(live_api, "whisper_transcribe_fn", lambda *a: FakeModel())
    with client.websocket_connect("/api/live/ws") as ws:
        assert ws.receive_json()["type"] == "ready"
        audio = tone(3.0) + silence(0.5)
        for i in range(0, len(audio), 8000):
            ws.send_bytes(audio[i : i + 8000])
        ws.send_text("stop")
        messages = []
        while True:
            m = ws.receive_json()
            messages.append(m)
            if m["type"] == "done":
                break
    stats = [m for m in messages if m["type"] == "stats"]
    assert stats[-1]["words"] > 0
    assert stats[-1]["fillers"] >= 1
