"""Step 6: body language and eye contact from video frames with MediaPipe.

Frames are decoded with OpenCV at SAMPLE_FPS and run through the Pose, Face
and Hand landmarkers. `aggregate` (pure, unit tested) turns the per-frame
observations into the metrics the scorer uses.
"""

from __future__ import annotations

import logging
import math
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.pipeline import body_features as bf
from app.schemas.metrics import BodyMetrics, EmotionPoint, Segment, TimePoint

log = logging.getLogger(__name__)

SAMPLE_FPS = 10.0  # fidgeting and swaying are 1-4 Hz movements; 10 fps catches them
FACE_EVERY = 2  # run the face model on every 2nd sampled frame (5 fps)
MAX_WIDTH = 640
EYE_SERIES_WINDOW_S = 5.0
GESTURE_SPEED = 1.0  # hand speed in shoulder widths per second that counts as a gesture
FIDGET_SPEED = 0.3
HANDS_CLOSE = 0.6  # hands this close together (shoulder widths) and moving = fidgeting
SWAY_WINDOW_S = 2.0
SWAY_STD = 0.04  # sideways wobble, in shoulder widths, inside a 2 s window
SWAY_MIN_CROSSINGS = 2

MIN_SEGMENT_S = {
    "looking_away": 3.0,
    "head_down": 3.0,
    "slouch": 5.0,
    "arms_crossed": 3.0,
    "hands_hidden": 15.0,
    "tense": 5.0,
    "fidget": 2.0,
    "strong_emotion": 3.0,
}
NEGATIVE_EMOTIONS = {"sad", "angry", "fearful", "disgusted"}

MODEL_URLS = {
    "pose": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "face": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    "hand": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
}

ProgressFn = Callable[[float], None]


@dataclass
class HandObs:
    center: bf.Pt
    open: bool
    touching_face: bool


@dataclass
class FrameObs:
    t: float
    brightness: float
    face_checked: bool = True  # False on frames where the face model was skipped
    posture: bf.PostureFrame | None = None
    face: bf.FaceFrame | None = None
    hands: list[HandObs] = field(default_factory=list)


# ---- aggregation (pure) -----------------------------------------------------


def runs(
    times: list[float], flags: list[bool], min_s: float, gap_s: float
) -> list[tuple[float, float]]:
    """Merge consecutive True frames into (start, end) runs lasting at least min_s."""
    out: list[tuple[float, float]] = []
    start: float | None = None
    last = 0.0
    for t, f in zip(times, flags, strict=True):
        if f:
            if start is None:
                start = t
            last = t
        elif start is not None and t - last > gap_s:
            if last + gap_s - start >= min_s:
                out.append((round(start, 2), round(last + gap_s, 2)))
            start = None
    if start is not None and last + gap_s - start >= min_s:
        out.append((round(start, 2), round(last + gap_s, 2)))
    return out


def _ratio(values: list[bool]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def _sway_windows(frames: list[FrameObs]) -> list[tuple[float, float]]:
    pts = [(f.t, f.posture.shoulder_mid.x / f.posture.shoulder_width) for f in frames if f.posture]
    if len(pts) < 10:
        return []
    out: list[tuple[float, float]] = []
    t0 = pts[0][0]
    end = pts[-1][0]
    while t0 + SWAY_WINDOW_S <= end:
        xs = [x for t, x in pts if t0 <= t < t0 + SWAY_WINDOW_S]
        if len(xs) >= 6:
            mean = sum(xs) / len(xs)
            std = math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))
            crossings = sum((a >= mean) != (b >= mean) for a, b in zip(xs, xs[1:], strict=False))
            if std > SWAY_STD and crossings >= SWAY_MIN_CROSSINGS:
                out.append((round(t0, 2), round(t0 + SWAY_WINDOW_S, 2)))
        t0 += SWAY_WINDOW_S
    return out


def _merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1] + 0.01:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def aggregate(frames: list[FrameObs], sample_fps: float, duration_s: float) -> BodyMetrics:
    n = len(frames)
    dt = 1.0 / sample_fps
    times = [f.t for f in frames]
    face_frames = [f for f in frames if f.face]
    pose_frames = [f for f in frames if f.posture]

    # Eye contact over time (5 s buckets).
    series: list[TimePoint] = []
    k = 0.0
    while k < duration_s:
        bucket = [
            f.face.eye_contact for f in face_frames if f.face and k <= f.t < k + EYE_SERIES_WINDOW_S
        ]
        series.append(TimePoint(t=round(k + EYE_SERIES_WINDOW_S / 2, 2), value=_ratio(bucket)))
        k += EYE_SERIES_WINDOW_S

    # Hands: speed of the nearest hand between sampled frames.
    gesture_events = 0
    fidget_flags: list[bool] = []
    hand_visible_flags: list[bool] = []
    open_flags: list[bool] = []
    touch_flags: list[bool] = []
    prev: FrameObs | None = None
    in_gesture = False
    for f in frames:
        visible = bool(f.hands)
        if f.posture is not None:
            hand_visible_flags.append(visible)
        touch_flags.append(any(h.touching_face for h in f.hands))
        if not visible:
            prev, in_gesture = f, False
            fidget_flags.append(False)
            continue
        open_flags.extend(h.open for h in f.hands)
        width = f.posture.shoulder_width if f.posture else None
        speed = 0.0
        if prev is not None and prev.hands and width:
            step = max(f.t - prev.t, dt)
            speed = max(
                min(bf._dist(h.center, p.center) for p in prev.hands) / width / step
                for h in f.hands
            )
        if speed >= GESTURE_SPEED and not in_gesture:
            gesture_events += 1
        in_gesture = speed >= GESTURE_SPEED
        close = (
            len(f.hands) == 2
            and width is not None
            and bf._dist(f.hands[0].center, f.hands[1].center) / width < HANDS_CLOSE
        )
        fidget_flags.append((close and speed >= FIDGET_SPEED) or touch_flags[-1])
        prev = f

    face_touch_events = runs(times, touch_flags, 0.5, dt * 1.5)
    minutes = max(duration_s / 60.0, 1e-6)
    sway = _merge(_sway_windows(frames))
    sway_ratio = (
        round(sum(e - s for s, e in sway) / (times[-1] - times[0]), 3)
        if len(pose_frames) >= 10 and times[-1] > times[0]
        else None
    )

    segs: list[Segment] = []

    def add(kind: str, flags: list[bool], ts: list[float]) -> None:
        for s, e in runs(ts, flags, MIN_SEGMENT_S[kind], dt * FACE_EVERY * 1.5):
            segs.append(Segment(kind=kind, start=s, end=e))

    ft = [f.t for f in face_frames]
    add("looking_away", [not f.face.eye_contact for f in face_frames if f.face], ft)
    add("tense", [f.face.expression == "tense" for f in face_frames if f.face], ft)
    for emo in sorted(NEGATIVE_EMOTIONS):
        for s, e in runs(
            ft,
            [bool(f.face and f.face.emotion == emo) for f in face_frames],
            MIN_SEGMENT_S["strong_emotion"],
            dt * FACE_EVERY * 1.5,
        ):
            segs.append(Segment(kind=f"emotion_{emo}", start=s, end=e))
    pt = [f.t for f in pose_frames]
    add("head_down", [f.posture.head_down for f in pose_frames if f.posture], pt)
    add("slouch", [f.posture.slouch for f in pose_frames if f.posture], pt)
    add("arms_crossed", [f.posture.arms_crossed for f in pose_frames if f.posture], pt)
    add("hands_hidden", [not f.hands for f in pose_frames], pt)
    add("fidget", fidget_flags, times)
    segs += [Segment(kind="face_touch", start=s, end=e) for s, e in face_touch_events]
    segs += [Segment(kind="sway", start=s, end=e) for s, e in sway]
    segs.sort(key=lambda s: (s.start, s.kind))

    postures = [f.posture for f in pose_frames if f.posture]
    faces = [f.face for f in face_frames if f.face]

    emotions = (
        {emo: round(sum(f.emotion == emo for f in faces) / len(faces), 3) for emo in bf.EMOTIONS}
        if faces
        else {}
    )
    emotion_timeline = []
    k = 0.0
    while k < duration_s:
        window = [
            f.face.emotion for f in face_frames if f.face and k <= f.t < k + EYE_SERIES_WINDOW_S
        ]
        if window:
            top = max(set(window), key=window.count)
            emotion_timeline.append(
                EmotionPoint(
                    t=round(k + EYE_SERIES_WINDOW_S / 2, 2),
                    emotion=top,
                    share=round(window.count(top) / len(window), 3),
                )
            )
        k += EYE_SERIES_WINDOW_S
    tilts = sorted(p.tilt_deg for p in postures)
    hands_ratio = _ratio(hand_visible_flags)
    return BodyMetrics(
        sample_fps=sample_fps,
        frames_analyzed=n,
        face_detected_ratio=(
            round(len(face_frames) / max(1, sum(f.face_checked for f in frames)), 3)
        ),
        pose_detected_ratio=round(len(pose_frames) / n, 3) if n else 0.0,
        too_dark_ratio=round(sum(f.brightness < bf.DARK_BRIGHTNESS for f in frames) / n, 3)
        if n
        else 0.0,
        eye_contact_ratio=_ratio([f.eye_contact for f in faces]),
        eye_contact_series=series,
        slouch_ratio=_ratio([p.slouch for p in postures]),
        head_down_ratio=_ratio([p.head_down for p in postures]),
        shoulder_tilt_deg=round(tilts[len(tilts) // 2], 2) if tilts else None,
        tilt_ratio=_ratio([p.tilted for p in postures]),
        lean_ratio=_ratio([p.leaning for p in postures]),
        hands_visible_ratio=hands_ratio,
        gestures_per_min=round(gesture_events / minutes, 2) if postures else None,
        open_gesture_ratio=_ratio(open_flags),
        arms_crossed_ratio=_ratio([p.arms_crossed for p in postures]),
        face_touch_count=len(face_touch_events),
        fidget_ratio=_ratio([x for x, f in zip(fidget_flags, frames, strict=True) if f.hands]),
        sway_ratio=sway_ratio,
        smile_ratio=_ratio([f.expression == "smiling" for f in faces]),
        tense_ratio=_ratio([f.expression == "tense" for f in faces]),
        neutral_ratio=_ratio([f.expression == "neutral" for f in faces]),
        emotions=emotions,
        emotion_timeline=emotion_timeline,
        segments=segs,
    )


# ---- MediaPipe (impure) -----------------------------------------------------


def ensure_models(models_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    folder = models_dir / "mediapipe"
    folder.mkdir(parents=True, exist_ok=True)
    for name, url in MODEL_URLS.items():
        path = folder / url.rsplit("/", 1)[-1]
        if not path.exists():
            log.info("downloading %s model", name)
            tmp = path.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)  # noqa: S310 - fixed https URLs
            tmp.rename(path)
        out[name] = path
    return out


def _landmarkers(models: dict[str, Path]) -> tuple[Any, Any, Any]:
    from mediapipe.tasks.python import BaseOptions, vision

    mode = vision.RunningMode.VIDEO
    pose = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models["pose"])),
            running_mode=mode,
            num_poses=1,
        )
    )
    face = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models["face"])),
            running_mode=mode,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
    )
    hand = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models["hand"])),
            running_mode=mode,
            num_hands=2,
        )
    )
    return pose, face, hand


def observe(
    video_path: Path, models_dir: Path, on_progress: ProgressFn | None = None
) -> tuple[list[FrameObs], float]:
    """Decode frames and run the landmarkers. Returns (observations, video duration)."""
    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [], 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if not 1 <= fps <= 240:
        fps = 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, round(fps / SAMPLE_FPS))
    pose_lm, face_lm, hand_lm = _landmarkers(ensure_models(models_dir))

    frames: list[FrameObs] = []
    index = 0
    sampled = 0
    try:
        while True:
            if not cap.grab():
                break
            if index % step:
                index += 1
                continue
            ok, bgr = cap.retrieve()
            if not ok:
                break
            t = index / fps
            h, w = bgr.shape[:2]
            if w > MAX_WIDTH:
                bgr = cv2.resize(bgr, (MAX_WIDTH, round(h * MAX_WIDTH / w)))
                h, w = bgr.shape[:2]
            aspect = w / h
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts = int(t * 1000)
            obs = FrameObs(
                t=round(t, 3),
                brightness=float(gray.mean()),
                face_checked=sampled % FACE_EVERY == 0,
            )

            pose_res = pose_lm.detect_for_video(image, ts)
            nose: bf.Pt | None = None
            if pose_res.pose_landmarks:
                pts = [bf.Pt(p.x, p.y, p.visibility or 0.0) for p in pose_res.pose_landmarks[0]]
                obs.posture = bf.posture(pts, aspect)
                nose = pts[bf.NOSE]

            if sampled % FACE_EVERY == 0:
                face_res = face_lm.detect_for_video(image, ts)
                if face_res.face_landmarks:
                    shapes = {c.category_name: c.score for c in face_res.face_blendshapes[0]}
                    matrix = (
                        face_res.facial_transformation_matrixes[0].tolist()
                        if face_res.facial_transformation_matrixes
                        else None
                    )
                    obs.face = bf.face(shapes, matrix)

            hand_res = hand_lm.detect_for_video(image, ts)
            for lms in hand_res.hand_landmarks or []:
                hand = [bf.Pt(p.x, p.y) for p in lms]
                touching = bool(
                    nose
                    and obs.posture
                    and bf.touching_face(hand, nose, obs.posture.shoulder_width, aspect)
                )
                obs.hands.append(
                    HandObs(bf.hand_center(hand, aspect), bf.hand_is_open(hand), touching)
                )

            frames.append(obs)
            sampled += 1
            index += 1
            if on_progress and total:
                on_progress(min(1.0, index / total))
    finally:
        cap.release()
        pose_lm.close()
        face_lm.close()
        hand_lm.close()
    duration = total / fps if total else (frames[-1].t if frames else 0.0)
    return frames, duration


def run(
    video_path: Path, models_dir: Path, duration_s: float, on_progress: ProgressFn | None = None
) -> BodyMetrics:
    frames, _ = observe(video_path, models_dir, on_progress)
    return aggregate(frames, SAMPLE_FPS, duration_s)
