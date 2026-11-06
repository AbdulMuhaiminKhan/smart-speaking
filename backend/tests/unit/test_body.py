import math

import pytest

from app.pipeline import body
from app.pipeline import body_features as bf
from app.pipeline.body_features import Pt

ASPECT = 1.0  # square image keeps the geometry easy to reason about


def pose(**overrides: Pt) -> list[Pt]:
    """Upright person facing the camera; shoulder width 0.3."""
    pts = [Pt(0.5, 0.5, 0.0)] * 33
    base = {
        bf.NOSE: Pt(0.5, 0.30),
        bf.L_EAR: Pt(0.56, 0.29),
        bf.R_EAR: Pt(0.44, 0.29),
        bf.L_SHOULDER: Pt(0.65, 0.48),
        bf.R_SHOULDER: Pt(0.35, 0.48),
        bf.L_WRIST: Pt(0.7, 0.8),
        bf.R_WRIST: Pt(0.3, 0.8),
    }
    base.update({getattr(bf, k): v for k, v in overrides.items()})
    for i, p in base.items():
        pts[i] = p
    return pts


def test_upright_posture() -> None:
    p = bf.posture(pose(), ASPECT)
    assert p is not None
    assert p.shoulder_width == pytest.approx(0.3)
    assert not (p.slouch or p.head_down or p.tilted or p.leaning or p.arms_crossed)
    assert p.neck_ratio == pytest.approx(0.19 / 0.3, abs=0.01)


def test_slouch_and_head_down() -> None:
    p = bf.posture(pose(NOSE=Pt(0.5, 0.45), L_EAR=Pt(0.56, 0.42), R_EAR=Pt(0.44, 0.42)), ASPECT)
    assert p is not None and p.slouch and p.head_down


def test_shoulder_tilt_and_lean() -> None:
    p = bf.posture(pose(L_SHOULDER=Pt(0.65, 0.53), NOSE=Pt(0.62, 0.30)), ASPECT)
    assert p is not None
    assert p.tilt_deg == pytest.approx(math.degrees(math.atan2(0.05, 0.3)), abs=0.1)
    assert p.tilted and p.leaning


def test_arms_crossed() -> None:
    p = bf.posture(pose(L_WRIST=Pt(0.4, 0.6), R_WRIST=Pt(0.6, 0.6)), ASPECT)
    assert p is not None and p.arms_crossed


def test_hidden_shoulders_give_none() -> None:
    assert bf.posture(pose(L_SHOULDER=Pt(0.65, 0.48, 0.1)), ASPECT) is None


def rot_y(deg: float) -> list[list[float]]:
    r = math.radians(deg)
    return [
        [math.cos(r), 0, math.sin(r), 0],
        [0, 1, 0, 0],
        [-math.sin(r), 0, math.cos(r), 0],
        [0, 0, 0, 1],
    ]


def rot_x(deg: float) -> list[list[float]]:
    r = math.radians(deg)
    return [
        [1, 0, 0, 0],
        [0, math.cos(r), -math.sin(r), 0],
        [0, math.sin(r), math.cos(r), 0],
        [0, 0, 0, 1],
    ]


def test_head_angles() -> None:
    yaw, pitch = bf.head_angles(rot_y(30))
    assert abs(yaw) == pytest.approx(30, abs=0.1) and abs(pitch) < 0.1
    yaw, pitch = bf.head_angles(rot_x(25))
    assert abs(pitch) == pytest.approx(25, abs=0.1) and abs(yaw) < 0.1


def test_eye_contact_rules() -> None:
    assert bf.face({}, rot_y(5)).eye_contact
    assert not bf.face({}, rot_y(30)).eye_contact
    assert not bf.face({"eyeLookOutLeft": 0.7, "eyeLookInRight": 0.7}, rot_y(0)).eye_contact
    # Looking slightly down at a screen under the webcam still counts.
    assert bf.face({"eyeLookDownLeft": 0.4, "eyeLookDownRight": 0.4}, rot_x(10)).eye_contact
    assert not bf.face({"eyeLookDownLeft": 0.8, "eyeLookDownRight": 0.8}, None).eye_contact


def test_expressions() -> None:
    assert bf.face({"mouthSmileLeft": 0.6, "mouthSmileRight": 0.5}, None).expression == "smiling"
    assert bf.face({"browDownLeft": 0.6, "browDownRight": 0.5}, None).expression == "tense"
    assert bf.face({}, None).expression == "neutral"


def hand(open_: bool, cx: float = 0.5, cy: float = 0.7) -> list[Pt]:
    pts = [Pt(cx, cy + 0.05)] * 21  # wrist below centre
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        pts[pip] = Pt(cx, cy)
        pts[tip] = Pt(cx, cy - 0.04) if open_ else Pt(cx, cy + 0.03)
    pts[0] = Pt(cx, cy + 0.05)
    return pts


def test_open_hand() -> None:
    assert bf.hand_is_open(hand(True))
    assert not bf.hand_is_open(hand(False))


def frame(
    t: float,
    *,
    eye: bool = True,
    slouch: bool = False,
    hands: list[body.HandObs] | None = None,
    x: float = 0.5,
) -> body.FrameObs:
    nose_y = 0.45 if slouch else 0.30
    ear_y = 0.42 if slouch else 0.29
    p = bf.posture(
        pose(
            NOSE=Pt(x, nose_y),
            L_SHOULDER=Pt(x + 0.15, 0.48),
            R_SHOULDER=Pt(x - 0.15, 0.48),
            L_EAR=Pt(x + 0.06, ear_y),
            R_EAR=Pt(x - 0.06, ear_y),
        ),
        ASPECT,
    )
    f = bf.face({}, rot_y(0 if eye else 40))
    return body.FrameObs(t=t, brightness=120, posture=p, face=f, hands=hands or [])


def test_aggregate_eye_contact_and_segments() -> None:
    frames = [frame(i / 10, eye=not (50 <= i < 100)) for i in range(200)]  # away from 5 s to 10 s
    m = body.aggregate(frames, 10, 20)
    assert m.eye_contact_ratio == pytest.approx(0.75, abs=0.01)
    away = [s for s in m.segments if s.kind == "looking_away"]
    assert len(away) == 1 and away[0].start == pytest.approx(5, abs=0.2)
    assert m.eye_contact_series[1].value == 0.0
    assert m.face_detected_ratio == 1.0 or m.face_detected_ratio >= 0.99


def test_aggregate_slouch_and_hidden_hands() -> None:
    frames = [frame(i / 10, slouch=i >= 100) for i in range(200)]
    m = body.aggregate(frames, 10, 20)
    assert m.slouch_ratio == pytest.approx(0.5)
    kinds = {s.kind for s in m.segments}
    assert {"slouch", "hands_hidden"} <= kinds
    assert m.hands_visible_ratio == 0.0


def test_aggregate_gestures() -> None:
    frames = []
    for i in range(100):  # 10 s, the hand jumps every second
        cx = 0.3 if (i // 10) % 2 == 0 else 0.7
        frames.append(frame(i / 10, hands=[body.HandObs(Pt(cx, 0.7), True, False)]))
    m = body.aggregate(frames, 10, 10)
    assert m.gestures_per_min == pytest.approx(54, abs=6)
    assert m.open_gesture_ratio == 1.0


def test_aggregate_sway() -> None:
    frames = [frame(i / 10, x=0.5 + 0.03 * math.sin(i / 10 * 2 * math.pi)) for i in range(100)]
    assert (body.aggregate(frames, 10, 10).sway_ratio or 0) > 0.5
    still = [frame(i / 10) for i in range(100)]
    assert body.aggregate(still, 10, 10).sway_ratio == 0


def test_aggregate_empty() -> None:
    m = body.aggregate([], 10, 5)
    assert m.frames_analyzed == 0 and m.eye_contact_ratio is None


def test_runs() -> None:
    t = [i / 10 for i in range(50)]
    flags = [10 <= i < 40 for i in range(50)]
    assert body.runs(t, flags, 2.0, 0.15) == [(1.0, 4.05)]
    assert body.runs(t, flags, 5.0, 0.15) == []
