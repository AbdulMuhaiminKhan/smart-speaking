// Live body-language checks. Mirrors backend/app/pipeline/body_features.py so
// the live hints agree with the final report. Thresholds: docs/scoring.md.

export interface P {
  x: number
  y: number
  visibility?: number
}

export const POSE = { NOSE: 0, L_EAR: 7, R_EAR: 8, L_SHOULDER: 11, R_SHOULDER: 12, L_WRIST: 15, R_WRIST: 16, L_HIP: 23, R_HIP: 24 }

export const RULES = {
  VISIBLE: 0.5,
  EYE_YAW_MAX_DEG: 15,
  EYE_PITCH_MAX_DEG: 20,
  GAZE_SIDE_MAX: 0.45,
  GAZE_UP_MAX: 0.45,
  GAZE_DOWN_MAX: 0.55,
  SLOUCH_NECK_RATIO: 0.35,
  HEAD_DOWN_RATIO: 0.25,
  TILT_DEG: 8,
  LEAN_RATIO: 0.3,
  SMILE_MIN: 0.35,
}

const vis = (p: P | undefined) => !!p && (p.visibility ?? 1) >= RULES.VISIBLE

export interface PostureCheck {
  ok: boolean
  slouch: boolean
  headDown: boolean
  tilted: boolean
  leaning: boolean
  label: string
}

export function checkPosture(pose: P[], aspect: number): PostureCheck | null {
  const ls = pose[POSE.L_SHOULDER]
  const rs = pose[POSE.R_SHOULDER]
  if (!vis(ls) || !vis(rs)) return null
  const sx = (p: P) => p.x * aspect
  const width = Math.hypot(sx(ls) - sx(rs), ls.y - rs.y)
  if (width < 1e-3) return null
  const midX = (sx(ls) + sx(rs)) / 2
  const midY = (ls.y + rs.y) / 2
  let tilt = Math.abs((Math.atan2(ls.y - rs.y, sx(ls) - sx(rs)) * 180) / Math.PI)
  tilt = Math.min(tilt, 180 - tilt)
  const ears = [pose[POSE.L_EAR], pose[POSE.R_EAR]].filter(vis)
  const neck = ears.length ? (midY - ears.reduce((a, e) => a + e.y, 0) / ears.length) / width : null
  const nose = pose[POSE.NOSE]
  const head = vis(nose) ? (midY - nose.y) / width : null
  const lean = vis(nose) ? (sx(nose) - midX) / width : null

  const slouch = neck !== null && neck < RULES.SLOUCH_NECK_RATIO
  const headDown = head !== null && head < RULES.HEAD_DOWN_RATIO
  const tilted = tilt > RULES.TILT_DEG
  const leaning = lean !== null && Math.abs(lean) > RULES.LEAN_RATIO
  const label = headDown ? 'Head down' : slouch ? 'Slouching' : tilted ? 'Shoulders tilted' : leaning ? 'Leaning' : 'Posture OK'
  return { ok: !(slouch || headDown || tilted || leaning), slouch, headDown, tilted, leaning, label }
}

export interface Baseline {
  yaw: number
  pitch: number
  down: number
}

export const EMOTIONS = ['neutral', 'happy', 'surprised', 'sad', 'angry', 'fearful', 'disgusted'] as const
export type Emotion = (typeof EMOTIONS)[number]

/** Mirrors face_emotion() in backend/app/pipeline/body_features.py. */
export function faceEmotion(shapes: Record<string, number>): { emotion: Emotion; scores: Record<string, number> } {
  const b = (...names: string[]) => names.reduce((a, n) => a + (shapes[n] ?? 0), 0) / names.length
  const browUp = (b('browInnerUp') + b('browOuterUpLeft', 'browOuterUpRight')) / 2
  const smile = b('mouthSmileLeft', 'mouthSmileRight')
  const raw: Record<string, number> = {
    happy: 0.7 * smile + 0.3 * b('cheekSquintLeft', 'cheekSquintRight'),
    surprised: 0.5 * browUp + 0.4 * b('eyeWideLeft', 'eyeWideRight') + 0.1 * b('jawOpen'),
    sad: 0.6 * b('mouthFrownLeft', 'mouthFrownRight') + 0.4 * b('browInnerUp') - 0.3 * smile,
    angry: 0.6 * b('browDownLeft', 'browDownRight') + 0.2 * b('eyeSquintLeft', 'eyeSquintRight') + 0.2 * b('mouthPressLeft', 'mouthPressRight'),
    fearful: 0.4 * b('eyeWideLeft', 'eyeWideRight') + 0.3 * b('browInnerUp') + 0.3 * b('mouthStretchLeft', 'mouthStretchRight'),
    disgusted: 0.6 * b('noseSneerLeft', 'noseSneerRight') + 0.4 * b('mouthUpperUpLeft', 'mouthUpperUpRight'),
  }
  const scores = Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, Math.max(0, Math.min(1, v))]))
  const best = Object.keys(scores).reduce((a, k) => (scores[k] > scores[a] ? k : a), 'happy')
  const threshold = best === 'happy' ? 0.35 : 0.25
  return { emotion: (scores[best] >= threshold ? best : 'neutral') as Emotion, scores }
}

export interface FaceCheck {
  eyeContact: boolean
  smiling: boolean
  emotion: Emotion
  yaw: number
  pitch: number
  down: number
  label: string
}

/** Head angles from MediaPipe's facial transformation matrix (column-major 4x4). */
export function headAngles(m: number[]): { yaw: number; pitch: number } {
  // Third column of the rotation part = the face's forward axis.
  const fx = m[8]
  const fy = m[9]
  const fz = m[10]
  const yaw = (Math.atan2(fx, fz) * 180) / Math.PI
  const pitch = (Math.atan2(-fy, Math.hypot(fx, fz)) * 180) / Math.PI
  return { yaw, pitch }
}

export function checkFace(shapes: Record<string, number>, matrix: number[] | null, baseline: Baseline | null): FaceCheck {
  const b = (k: string) => shapes[k] ?? 0
  const { yaw, pitch } = matrix ? headAngles(matrix) : { yaw: 0, pitch: 0 }
  const side = Math.max((b('eyeLookOutLeft') + b('eyeLookInRight')) / 2, (b('eyeLookInLeft') + b('eyeLookOutRight')) / 2)
  const up = (b('eyeLookUpLeft') + b('eyeLookUpRight')) / 2
  const down = (b('eyeLookDownLeft') + b('eyeLookDownRight')) / 2
  // Live mode subtracts the calibration pose (where the camera is for this person).
  const y = yaw - (baseline?.yaw ?? 0)
  const p = pitch - (baseline?.pitch ?? 0)
  const d = Math.max(0, down - (baseline?.down ?? 0))
  const eyeContact =
    Math.abs(y) <= RULES.EYE_YAW_MAX_DEG &&
    Math.abs(p) <= RULES.EYE_PITCH_MAX_DEG &&
    side < RULES.GAZE_SIDE_MAX &&
    up < RULES.GAZE_UP_MAX &&
    d < RULES.GAZE_DOWN_MAX
  const smiling = (b('mouthSmileLeft') + b('mouthSmileRight')) / 2 >= RULES.SMILE_MIN
  const { emotion } = faceEmotion(shapes)
  return { eyeContact, smiling, emotion, yaw, pitch, down, label: eyeContact ? 'Eye contact' : 'Looking away' }
}

/** Bounding box of landmarks. Face and hand landmarks carry no visibility, so pass useVisibility=false. */
export function bbox(points: P[], pad = 0.02, useVisibility = true): { x: number; y: number; w: number; h: number } | null {
  const pts = useVisibility ? points.filter((p) => (p.visibility ?? 1) >= RULES.VISIBLE) : points
  if (!pts.length) return null
  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const x0 = Math.max(0, Math.min(...xs) - pad)
  const y0 = Math.max(0, Math.min(...ys) - pad)
  const x1 = Math.min(1, Math.max(...xs) + pad)
  const y1 = Math.min(1, Math.max(...ys) + pad)
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }
}
