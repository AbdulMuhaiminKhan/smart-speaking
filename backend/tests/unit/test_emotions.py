import pytest

from app.pipeline import body
from app.pipeline import body_features as bf
from app.pipeline import voice_emotion as ve
from tests.helpers import transcript_from, words_from


@pytest.mark.parametrize(
    "shapes,expected",
    [
        ({}, "neutral"),
        (
            {
                "mouthSmileLeft": 0.7,
                "mouthSmileRight": 0.7,
                "cheekSquintLeft": 0.4,
                "cheekSquintRight": 0.4,
            },
            "happy",
        ),
        (
            {
                "browInnerUp": 0.7,
                "browOuterUpLeft": 0.6,
                "browOuterUpRight": 0.6,
                "eyeWideLeft": 0.6,
                "eyeWideRight": 0.6,
            },
            "surprised",
        ),
        (
            {
                "browDownLeft": 0.7,
                "browDownRight": 0.7,
                "mouthPressLeft": 0.4,
                "mouthPressRight": 0.4,
            },
            "angry",
        ),
        ({"mouthFrownLeft": 0.6, "mouthFrownRight": 0.6, "browInnerUp": 0.4}, "sad"),
        (
            {
                "noseSneerLeft": 0.6,
                "noseSneerRight": 0.6,
                "mouthUpperUpLeft": 0.5,
                "mouthUpperUpRight": 0.5,
            },
            "disgusted",
        ),
        (
            {
                "eyeWideLeft": 0.7,
                "eyeWideRight": 0.7,
                "mouthStretchLeft": 0.6,
                "mouthStretchRight": 0.6,
                "browInnerUp": 0.3,
            },
            "fearful",
        ),
        ({"jawOpen": 0.8}, "neutral"),  # talking alone is not surprise
        ({"mouthSmileLeft": 0.3, "mouthSmileRight": 0.3}, "neutral"),  # a hint of a smile
    ],
)
def test_face_emotion(shapes: dict[str, float], expected: str) -> None:
    emotion, scores = bf.face_emotion(shapes)
    assert emotion == expected
    assert set(scores) == set(bf.EMOTIONS) - {"neutral"}


def test_body_aggregates_emotions_and_negative_segments() -> None:
    happy = {
        "mouthSmileLeft": 0.8,
        "mouthSmileRight": 0.8,
        "cheekSquintLeft": 0.5,
        "cheekSquintRight": 0.5,
    }
    sad = {"mouthFrownLeft": 0.7, "mouthFrownRight": 0.7, "browInnerUp": 0.5}
    frames = []
    for i in range(100):  # 10 s: happy for 5 s, then sad for 5 s
        shapes = happy if i < 50 else sad
        frames.append(body.FrameObs(t=i / 10, brightness=120, face=bf.face(shapes, None)))
    m = body.aggregate(frames, 10, 10)
    assert m.emotions["happy"] == pytest.approx(0.5) and m.emotions["sad"] == pytest.approx(0.5)
    assert [p.emotion for p in m.emotion_timeline] == ["happy", "sad"]
    assert any(s.kind == "emotion_sad" for s in m.segments)


def test_voice_emotion_windows_skip_silence() -> None:
    words = words_from(" ".join(["word"] * 10))  # 0 to about 4 s of speech
    t = transcript_from(words, duration=12)
    windows = ve.speech_windows(t, 12)
    assert windows == [(0.0, 4.0)]


def test_voice_emotion_summary() -> None:
    m = ve.summarize(
        [(0, 4), (4, 8)],
        [
            {"neutral": 0.1, "happy": 0.8, "angry": 0.05, "sad": 0.05},
            {"neutral": 0.5, "happy": 0.4, "angry": 0.05, "sad": 0.05},
        ],
    )
    assert m.dominant == "happy"
    assert m.emotions["happy"] == 0.6
    assert [p.emotion for p in m.timeline] == ["happy", "neutral"]
    assert ve.summarize([], []).emotions == {}


def test_voice_emotion_near_tie_is_neutral() -> None:
    m = ve.summarize([(0, 4)], [{"neutral": 0.41, "happy": 0.1, "angry": 0.42, "sad": 0.07}])
    assert m.dominant == "neutral"
