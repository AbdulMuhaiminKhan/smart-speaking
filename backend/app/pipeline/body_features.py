"""Per-frame body-language features from MediaPipe landmarks. Pure functions.

Coordinates are MediaPipe's normalized image coordinates (x right, y down,
0..1). Distances are divided by shoulder width so they do not depend on how
far the speaker sits from the camera. Thresholds are documented in
docs/scoring.md and mirrored in frontend/src/live/bodyRules.ts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# MediaPipe Pose landmark indexes
NOSE, L_EAR, R_EAR = 0, 7, 8
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24

# Thresholds
VISIBLE = 0.5  # pose landmark visibility needed to trust it
EYE_YAW_MAX_DEG = 15.0
EYE_PITCH_MAX_DEG = 20.0  # webcams sit above the screen, so allow looking a bit down
GAZE_SIDE_MAX = 0.45  # eye-look-in/out blendshape score that counts as looking sideways
GAZE_UP_MAX = 0.45
GAZE_DOWN_MAX = 0.55  # a little looser: the screen usually sits just below the camera
SLOUCH_NECK_RATIO = 0.35  # ear-to-shoulder height / shoulder width below this = slouched
HEAD_DOWN_RATIO = 0.25  # nose-to-shoulder height / shoulder width below this = head down
TILT_DEG = 8.0
LEAN_RATIO = 0.3  # head offset from shoulder centre / shoulder width
SMILE_MIN = 0.35
TENSE_MIN = 0.4
FACE_TOUCH_RATIO = 0.6  # hand within this many shoulder widths of the nose
DARK_BRIGHTNESS = 50  # mean pixel value (0..255) below this is too dark


@dataclass(frozen=True)
class Pt:
    x: float
    y: float
    visibility: float = 1.0


def _visible(*pts: Pt) -> bool:
    return all(p.visibility >= VISIBLE for p in pts)


def _mid(a: Pt, b: Pt) -> Pt:
    return Pt((a.x + b.x) / 2, (a.y + b.y) / 2, min(a.visibility, b.visibility))


def _dist(a: Pt, b: Pt) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


@dataclass(frozen=True)
class PostureFrame:
    shoulder_width: float
    shoulder_mid: Pt
    tilt_deg: float
    neck_ratio: float | None
    head_ratio: float | None
    lean: float | None
    slouch: bool
    head_down: bool
    tilted: bool
    leaning: bool
    arms_crossed: bool
    wrists: tuple[Pt | None, Pt | None]


def posture(pose: Sequence[Pt], aspect: float = 16 / 9) -> PostureFrame | None:
    """Posture features, or None when the shoulders are not visible.

    aspect = width / height of the image, so x and y distances are comparable.
    """
    ls, rs = pose[L_SHOULDER], pose[R_SHOULDER]
    if not _visible(ls, rs):
        return None

    def sc(p: Pt) -> Pt:  # scale x so both axes share units
        return Pt(p.x * aspect, p.y, p.visibility)

    ls_s, rs_s = sc(ls), sc(rs)
    width = _dist(ls_s, rs_s)
    if width < 1e-3:
        return None
    mid = _mid(ls_s, rs_s)
    tilt = abs(math.degrees(math.atan2(ls_s.y - rs_s.y, ls_s.x - rs_s.x)))
    tilt = min(tilt, 180 - tilt)

    ears = [sc(pose[i]) for i in (L_EAR, R_EAR) if pose[i].visibility >= VISIBLE]
    neck = (mid.y - sum(e.y for e in ears) / len(ears)) / width if ears else None
    nose = sc(pose[NOSE])
    head = (mid.y - nose.y) / width if nose.visibility >= VISIBLE else None
    lean = (nose.x - mid.x) / width if nose.visibility >= VISIBLE else None

    lw, rw = pose[L_WRIST], pose[R_WRIST]
    lw_v = sc(lw) if lw.visibility >= VISIBLE else None
    rw_v = sc(rw) if rw.visibility >= VISIBLE else None
    # Arms crossed: each wrist is past the body's centre line, at chest height.
    crossed = False
    if lw_v and rw_v:
        left_side = 1 if ls_s.x > rs_s.x else -1  # image may be mirrored
        crossed = (
            (lw_v.x - mid.x) * left_side < 0
            and (rw_v.x - mid.x) * left_side > 0
            and abs(lw_v.y - mid.y) < width
            and abs(rw_v.y - mid.y) < width
        )

    return PostureFrame(
        shoulder_width=width,
        shoulder_mid=mid,
        tilt_deg=tilt,
        neck_ratio=neck,
        head_ratio=head,
        lean=lean,
        slouch=neck is not None and neck < SLOUCH_NECK_RATIO,
        head_down=head is not None and head < HEAD_DOWN_RATIO,
        tilted=tilt > TILT_DEG,
        leaning=lean is not None and abs(lean) > LEAN_RATIO,
        arms_crossed=crossed,
        wrists=(lw_v, rw_v),
    )


def head_angles(matrix: Sequence[Sequence[float]]) -> tuple[float, float]:
    """(yaw, pitch) in degrees from MediaPipe's 4x4 facial transformation matrix.

    The face's forward axis is the third column of the rotation part; 0, 0
    means facing the camera. Only magnitudes are used downstream.
    """
    fx, fy, fz = matrix[0][2], matrix[1][2], matrix[2][2]
    yaw = math.degrees(math.atan2(fx, fz))
    pitch = math.degrees(math.atan2(-fy, math.hypot(fx, fz)))
    return yaw, pitch


@dataclass(frozen=True)
class FaceFrame:
    yaw: float
    pitch: float
    gaze_away: float  # strongest eye-look blendshape, 0..1
    eye_contact: bool
    smile: float
    tense: float
    expression: str  # smiling | tense | neutral
    emotion: str = "neutral"  # see EMOTIONS
    emotion_scores: dict[str, float] | None = None


def face(blendshapes: Mapping[str, float], matrix: Sequence[Sequence[float]] | None) -> FaceFrame:
    yaw, pitch = head_angles(matrix) if matrix is not None else (0.0, 0.0)

    def b(name: str) -> float:
        return float(blendshapes.get(name, 0.0))

    # Eyes turned sideways: one eye looks "in" while the other looks "out".
    horizontal = max(
        (b("eyeLookOutLeft") + b("eyeLookInRight")) / 2,
        (b("eyeLookInLeft") + b("eyeLookOutRight")) / 2,
    )
    up = (b("eyeLookUpLeft") + b("eyeLookUpRight")) / 2
    down = (b("eyeLookDownLeft") + b("eyeLookDownRight")) / 2
    gaze = max(horizontal, up, down)
    eyes_on_camera = horizontal < GAZE_SIDE_MAX and up < GAZE_UP_MAX and down < GAZE_DOWN_MAX
    eye_contact = abs(yaw) <= EYE_YAW_MAX_DEG and abs(pitch) <= EYE_PITCH_MAX_DEG and eyes_on_camera

    smile = (b("mouthSmileLeft") + b("mouthSmileRight")) / 2
    tense = max(
        (b("browDownLeft") + b("browDownRight")) / 2,
        (b("mouthPressLeft") + b("mouthPressRight")) / 2,
    )
    expression = "smiling" if smile >= SMILE_MIN else "tense" if tense >= TENSE_MIN else "neutral"
    emotion, scores = face_emotion(blendshapes)
    return FaceFrame(yaw, pitch, gaze, eye_contact, smile, tense, expression, emotion, scores)


EMOTIONS = ("neutral", "happy", "surprised", "sad", "angry", "fearful", "disgusted")
EMOTION_MIN = 0.25  # below this, the face counts as neutral
HAPPY_MIN = 0.35


def face_emotion(blendshapes: Mapping[str, float]) -> tuple[str, dict[str, float]]:
    """Basic facial emotion from MediaPipe blendshapes (FACS-style action units).

    A transparent heuristic, not a trained emotion model. Jaw opening is
    weighted low because it moves constantly while talking.
    """

    def b(*names: str) -> float:
        return sum(float(blendshapes.get(n, 0.0)) for n in names) / len(names)

    brow_up = (b("browInnerUp") + b("browOuterUpLeft", "browOuterUpRight")) / 2
    scores = {
        "happy": 0.7 * b("mouthSmileLeft", "mouthSmileRight")
        + 0.3 * b("cheekSquintLeft", "cheekSquintRight"),
        "surprised": 0.5 * brow_up + 0.4 * b("eyeWideLeft", "eyeWideRight") + 0.1 * b("jawOpen"),
        "sad": 0.6 * b("mouthFrownLeft", "mouthFrownRight")
        + 0.4 * b("browInnerUp")
        - 0.3 * b("mouthSmileLeft", "mouthSmileRight"),
        "angry": 0.6 * b("browDownLeft", "browDownRight")
        + 0.2 * b("eyeSquintLeft", "eyeSquintRight")
        + 0.2 * b("mouthPressLeft", "mouthPressRight"),
        "fearful": 0.4 * b("eyeWideLeft", "eyeWideRight")
        + 0.3 * b("browInnerUp")
        + 0.3 * b("mouthStretchLeft", "mouthStretchRight"),
        "disgusted": 0.6 * b("noseSneerLeft", "noseSneerRight")
        + 0.4 * b("mouthUpperUpLeft", "mouthUpperUpRight"),
    }
    scores = {k: round(max(0.0, min(1.0, v)), 3) for k, v in scores.items()}
    best = max(scores, key=lambda k: scores[k])
    threshold = HAPPY_MIN if best == "happy" else EMOTION_MIN
    return (best if scores[best] >= threshold else "neutral"), scores


def hand_is_open(hand: Sequence[Pt]) -> bool:
    """Open hand: at least three fingertips farther from the wrist than their middle joints."""
    wrist = hand[0]
    tips, pips = (8, 12, 16, 20), (6, 10, 14, 18)
    extended = sum(
        _dist(hand[t], wrist) > _dist(hand[p], wrist) * 1.1 for t, p in zip(tips, pips, strict=True)
    )
    return extended >= 3


def hand_center(hand: Sequence[Pt], aspect: float = 16 / 9) -> Pt:
    xs = [p.x * aspect for p in hand]
    ys = [p.y for p in hand]
    return Pt(sum(xs) / len(xs), sum(ys) / len(ys))


def touching_face(
    hand: Sequence[Pt], nose: Pt, shoulder_width: float, aspect: float = 16 / 9
) -> bool:
    c = hand_center(hand, aspect)
    n = Pt(nose.x * aspect, nose.y)
    return _dist(c, n) < FACE_TOUCH_RATIO * shoulder_width
