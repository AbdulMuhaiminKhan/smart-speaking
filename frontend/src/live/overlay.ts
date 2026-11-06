// Draws boxes, skeleton lines and labels over the (mirrored) camera preview.
import { FaceLandmarker, HandLandmarker, PoseLandmarker } from '@mediapipe/tasks-vision'
import { bbox, checkFace, checkPosture, POSE, type Baseline, type FaceCheck, type P, type PostureCheck } from './bodyRules'
import type { TrackResult } from './tracker'

export const EMOTION_LABELS: Record<string, string> = {
  neutral: 'Neutral',
  happy: 'Happy',
  surprised: 'Surprised',
  sad: 'Sad',
  angry: 'Angry',
  fearful: 'Worried',
  disgusted: 'Displeased',
}

export interface FrameChecks {
  face: FaceCheck | null
  posture: PostureCheck | null
  handsVisible: number
}

const GOOD = '#10b981'
const WARN = '#f59e0b'
const BAD = '#ef4444'
const INFO = '#60a5fa'

function mirror(p: P): P {
  return { ...p, x: 1 - p.x }
}

function drawBox(ctx: CanvasRenderingContext2D, box: { x: number; y: number; w: number; h: number }, color: string, label: string) {
  const { width: W, height: H } = ctx.canvas
  const x = box.x * W
  const y = box.y * H
  const w = box.w * W
  const h = box.h * H
  ctx.strokeStyle = color
  ctx.lineWidth = Math.max(2, W / 400)
  ctx.strokeRect(x, y, w, h)
  // Corner accents, like detection demos.
  const c = Math.min(w, h) * 0.18
  ctx.lineWidth *= 2
  for (const [cx, cy, dx, dy] of [
    [x, y, 1, 1],
    [x + w, y, -1, 1],
    [x, y + h, 1, -1],
    [x + w, y + h, -1, -1],
  ]) {
    ctx.beginPath()
    ctx.moveTo(cx + dx * c, cy)
    ctx.lineTo(cx, cy)
    ctx.lineTo(cx, cy + dy * c)
    ctx.stroke()
  }
  const font = Math.max(14, W / 45)
  ctx.font = `600 ${font}px Inter, system-ui, sans-serif`
  const tw = ctx.measureText(label).width + font
  const ly = y - font * 1.6 < 0 ? y + h : y - font * 1.6
  ctx.fillStyle = color
  ctx.fillRect(x - ctx.lineWidth / 4, ly, tw, font * 1.6)
  ctx.fillStyle = '#0b1220'
  ctx.fillText(label, x + font / 2, ly + font * 1.15)
}

function drawLines(
  ctx: CanvasRenderingContext2D,
  pts: P[],
  pairs: { start: number; end: number }[],
  color: string,
  minVis = 0.5,
  dots = true,
) {
  const { width: W, height: H } = ctx.canvas
  ctx.strokeStyle = color
  ctx.lineWidth = Math.max(1.5, W / 600)
  ctx.globalAlpha = 0.85
  for (const { start, end } of pairs) {
    const a = pts[start]
    const b = pts[end]
    if (!a || !b || (a.visibility ?? 1) < minVis || (b.visibility ?? 1) < minVis) continue
    ctx.beginPath()
    ctx.moveTo(a.x * W, a.y * H)
    ctx.lineTo(b.x * W, b.y * H)
    ctx.stroke()
  }
  if (!dots) {
    ctx.globalAlpha = 1
    return
  }
  ctx.fillStyle = color
  const used = new Set(pairs.flatMap((c) => [c.start, c.end]))
  for (const i of used) {
    const p = pts[i]
    if (!p || (p.visibility ?? 1) < minVis) continue
    ctx.beginPath()
    ctx.arc(p.x * W, p.y * H, Math.max(2, W / 400), 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1
}

/** Shoulders down to the hips, or about one shoulder width down when the hips are out of frame. */
function torsoBox(pts: P[], aspect: number) {
  const ls = pts[POSE.L_SHOULDER]
  const rs = pts[POSE.R_SHOULDER]
  if ((ls.visibility ?? 1) < 0.5 || (rs.visibility ?? 1) < 0.5) return null
  const x0 = Math.min(ls.x, rs.x)
  const x1 = Math.max(ls.x, rs.x)
  const widthY = ((x1 - x0) * aspect) // shoulder width in y units
  const hips = [pts[POSE.L_HIP], pts[POSE.R_HIP]].filter((p) => (p.visibility ?? 1) >= 0.5)
  const top = Math.min(ls.y, rs.y) - 0.02
  const bottom = hips.length ? Math.max(...hips.map((h) => h.y)) : Math.min(1, top + widthY * 1.1)
  const padX = (x1 - x0) * 0.08
  return { x: Math.max(0, x0 - padX), y: Math.max(0, top), w: Math.min(1, x1 + padX) - Math.max(0, x0 - padX), h: Math.min(1, bottom) - Math.max(0, top) }
}

const UPPER_BODY = PoseLandmarker.POSE_CONNECTIONS.filter((c) => c.start >= 11 && c.end >= 11 && c.start <= 24 && c.end <= 24)

export function drawFrame(ctx: CanvasRenderingContext2D, r: TrackResult, aspect: number, baseline: Baseline | null): FrameChecks {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
  let face: FaceCheck | null = null
  let posture: PostureCheck | null = null

  const poseRaw = r.pose?.landmarks?.[0]
  if (poseRaw) {
    posture = checkPosture(poseRaw, aspect)
    const pts = poseRaw.map(mirror)
    const color = posture ? (posture.ok ? GOOD : posture.headDown || posture.slouch ? BAD : WARN) : INFO
    drawLines(ctx, pts, UPPER_BODY, color)
    const torso = torsoBox(pts, aspect)
    if (torso && posture) drawBox(ctx, torso, color, posture.label)
  }

  const faceRaw = r.face?.faceLandmarks?.[0]
  if (faceRaw) {
    const shapes: Record<string, number> = {}
    for (const c of r.face?.faceBlendshapes?.[0]?.categories ?? []) shapes[c.categoryName] = c.score
    const matrix = r.face?.facialTransformationMatrixes?.[0]?.data ?? null
    face = checkFace(shapes, matrix ? Array.from(matrix) : null, baseline)
    const pts = faceRaw.map(mirror)
    const color = face.eyeContact ? GOOD : WARN
    for (const contour of [
      FaceLandmarker.FACE_LANDMARKS_FACE_OVAL,
      FaceLandmarker.FACE_LANDMARKS_LEFT_EYE,
      FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE,
      FaceLandmarker.FACE_LANDMARKS_LIPS,
    ])
      drawLines(ctx, pts, contour, color, 0, false)
    drawLines(ctx, pts, FaceLandmarker.FACE_LANDMARKS_LEFT_IRIS, color, 0)
    drawLines(ctx, pts, FaceLandmarker.FACE_LANDMARKS_RIGHT_IRIS, color, 0)
    const box = bbox(pts, 0.01, false)
    if (box) drawBox(ctx, box, color, `${face.label} · ${EMOTION_LABELS[face.emotion]}`)
  }

  const hands = r.hands?.landmarks ?? []
  hands.forEach((h, i) => {
    const pts = h.map(mirror)
    drawLines(ctx, pts, HandLandmarker.HAND_CONNECTIONS, INFO, 0)
    const box = bbox(pts, 0.015, false)
    const side = r.hands?.handedness?.[i]?.[0]?.categoryName
    if (box) drawBox(ctx, box, INFO, side ? `${side === 'Left' ? 'Right' : 'Left'} hand` : 'Hand')
  })

  return { face, posture, handsVisible: hands.length }
}
