from pathlib import Path

import pytest

from app.pipeline import preprocess
from app.pipeline.errors import NoAudioError, TooLongError, TooShortError, UnsupportedFormatError
from tests.conftest import make_test_video, requires_ffmpeg


def probe_json(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "62.5"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1280,
                "height": 720,
                "avg_frame_rate": "30000/1001",
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    data.update(overrides)
    return data


def test_parse_probe_reads_streams() -> None:
    info = preprocess.parse_probe(probe_json())
    assert info.duration_s == 62.5
    assert info.has_video and info.has_audio
    assert info.width == 1280 and info.height == 720
    assert info.fps == pytest.approx(29.97, abs=0.01)


def test_parse_probe_ignores_cover_art() -> None:
    info = preprocess.parse_probe(
        probe_json(
            streams=[
                {"codec_type": "video", "disposition": {"attached_pic": 1}},
                {"codec_type": "audio", "codec_name": "aac"},
            ]
        )
    )
    assert not info.has_video


def test_parse_probe_falls_back_to_stream_duration() -> None:
    info = preprocess.parse_probe(
        probe_json(
            format={"format_name": "matroska,webm"},
            streams=[{"codec_type": "audio", "duration": "12.0"}],
        )
    )
    assert info.duration_s == 12.0


def test_parse_probe_without_duration_is_unsupported() -> None:
    with pytest.raises(UnsupportedFormatError):
        preprocess.parse_probe({"format": {"format_name": "webm"}, "streams": []})


@pytest.mark.parametrize(
    "rate,expected", [("30/1", 30.0), ("0/0", None), ("25", 25.0), (None, None)]
)
def test_parse_rate(rate: str | None, expected: float | None) -> None:
    assert preprocess._parse_rate(rate) == expected


def test_validate_accepts_good_input() -> None:
    assert preprocess.validate_media(preprocess.parse_probe(probe_json()), 5, 930) == []


def test_validate_rejects_unknown_container() -> None:
    info = preprocess.parse_probe(probe_json(format={"format_name": "avi", "duration": "60"}))
    with pytest.raises(UnsupportedFormatError):
        preprocess.validate_media(info, 5, 930)


def test_validate_rejects_missing_audio() -> None:
    info = preprocess.parse_probe(probe_json(streams=[{"codec_type": "video"}]))
    with pytest.raises(NoAudioError):
        preprocess.validate_media(info, 5, 930)


def test_validate_rejects_short_and_long() -> None:
    short = preprocess.parse_probe(probe_json(format={"format_name": "webm", "duration": "2"}))
    long = preprocess.parse_probe(probe_json(format={"format_name": "webm", "duration": "1200"}))
    with pytest.raises(TooShortError):
        preprocess.validate_media(short, 5, 930)
    with pytest.raises(TooLongError):
        preprocess.validate_media(long, 5, 930)


def test_validate_warns_for_audio_only_and_low_quality() -> None:
    audio_only = preprocess.parse_probe(probe_json(streams=[{"codec_type": "audio"}]))
    assert any(w.startswith("no_video") for w in preprocess.validate_media(audio_only, 5, 930))
    tiny = preprocess.parse_probe(
        probe_json(
            streams=[
                {"codec_type": "video", "height": 144, "avg_frame_rate": "5/1"},
                {"codec_type": "audio"},
            ]
        )
    )
    codes = {w.split(":")[0] for w in preprocess.validate_media(tiny, 5, 930)}
    assert codes == {"low_resolution", "low_fps"}


@requires_ffmpeg
def test_run_extracts_16k_mono_wav(tmp_path: Path) -> None:
    import wave

    clip = make_test_video(tmp_path / "clip.mp4", seconds=6)
    info, audio, warnings = preprocess.run(clip, tmp_path / "work", 5, 930)
    assert info.has_video and info.has_audio
    assert warnings == []
    with wave.open(str(audio)) as wav:
        assert wav.getframerate() == 16_000
        assert wav.getnchannels() == 1
        assert wav.getnframes() / 16_000 == pytest.approx(6.0, abs=0.2)


@requires_ffmpeg
def test_run_rejects_garbage_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video at all")
    with pytest.raises(UnsupportedFormatError):
        preprocess.run(bad, tmp_path / "work", 5, 930)


@requires_ffmpeg
def test_run_rejects_video_without_audio(tmp_path: Path) -> None:
    clip = make_test_video(tmp_path / "silent.mp4", seconds=6, audio=False)
    with pytest.raises(NoAudioError):
        preprocess.run(clip, tmp_path / "work", 5, 930)
