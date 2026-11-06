import { describe, expect, it } from 'vitest'
import { bbox, checkFace, checkPosture, headAngles, POSE, type P } from './bodyRules'

function pose(over: Partial<Record<keyof typeof POSE, P>> = {}): P[] {
  const pts: P[] = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, visibility: 0 }))
  const base: Partial<Record<keyof typeof POSE, P>> = {
    NOSE: { x: 0.5, y: 0.3, visibility: 1 },
    L_EAR: { x: 0.56, y: 0.29, visibility: 1 },
    R_EAR: { x: 0.44, y: 0.29, visibility: 1 },
    L_SHOULDER: { x: 0.65, y: 0.48, visibility: 1 },
    R_SHOULDER: { x: 0.35, y: 0.48, visibility: 1 },
    ...over,
  }
  for (const [k, v] of Object.entries(base)) pts[POSE[k as keyof typeof POSE]] = v as P
  return pts
}

// Same cases as backend/tests/unit/test_body.py, so live hints match the report.
describe('checkPosture', () => {
  it('accepts upright posture', () => {
    expect(checkPosture(pose(), 1)?.label).toBe('Posture OK')
  })
  it('flags slouching and head down', () => {
    const p = checkPosture(pose({ NOSE: { x: 0.5, y: 0.45, visibility: 1 }, L_EAR: { x: 0.56, y: 0.42, visibility: 1 }, R_EAR: { x: 0.44, y: 0.42, visibility: 1 } }), 1)
    expect(p?.slouch && p.headDown).toBe(true)
    expect(p?.label).toBe('Head down')
  })
  it('flags tilted shoulders', () => {
    expect(checkPosture(pose({ L_SHOULDER: { x: 0.65, y: 0.53, visibility: 1 } }), 1)?.tilted).toBe(true)
  })
  it('returns null when shoulders are hidden', () => {
    expect(checkPosture(pose({ L_SHOULDER: { x: 0.65, y: 0.48, visibility: 0.1 } }), 1)).toBeNull()
  })
})

const rotY = (deg: number) => {
  const r = (deg * Math.PI) / 180
  // column-major 4x4: columns are x, y, z axes
  return [Math.cos(r), 0, -Math.sin(r), 0, 0, 1, 0, 0, Math.sin(r), 0, Math.cos(r), 0, 0, 0, 0, 1]
}

describe('face checks', () => {
  it('reads head yaw from the matrix', () => {
    expect(Math.abs(headAngles(rotY(30)).yaw)).toBeCloseTo(30, 1)
  })
  it('detects eye contact and looking away', () => {
    expect(checkFace({}, rotY(5), null).eyeContact).toBe(true)
    expect(checkFace({}, rotY(35), null).eyeContact).toBe(false)
    expect(checkFace({ eyeLookOutLeft: 0.8, eyeLookInRight: 0.8 }, null, null).eyeContact).toBe(false)
  })
  it('uses the calibration baseline', () => {
    expect(checkFace({}, rotY(25), null).eyeContact).toBe(false)
    expect(checkFace({}, rotY(25), { yaw: 22, pitch: 0, down: 0 }).eyeContact).toBe(true)
  })
})

describe('bbox', () => {
  it('ignores visibility for face and hand landmarks when asked', () => {
    const pts = [{ x: 0.2, y: 0.2, visibility: 0 }, { x: 0.4, y: 0.6, visibility: 0 }]
    expect(bbox(pts, 0)).toBeNull()
    expect(bbox(pts, 0, false)).toEqual({ x: 0.2, y: 0.2, w: 0.2, h: 0.39999999999999997 })
  })
})

describe('faceEmotion (mirrors the backend tests)', () => {
  it('classifies clear expressions and stays neutral while talking', async () => {
    const { faceEmotion } = await import('./bodyRules')
    expect(faceEmotion({}).emotion).toBe('neutral')
    expect(faceEmotion({ mouthSmileLeft: 0.7, mouthSmileRight: 0.7, cheekSquintLeft: 0.4, cheekSquintRight: 0.4 }).emotion).toBe('happy')
    expect(faceEmotion({ browDownLeft: 0.7, browDownRight: 0.7, mouthPressLeft: 0.4, mouthPressRight: 0.4 }).emotion).toBe('angry')
    expect(faceEmotion({ mouthFrownLeft: 0.6, mouthFrownRight: 0.6, browInnerUp: 0.4 }).emotion).toBe('sad')
    expect(faceEmotion({ jawOpen: 0.8 }).emotion).toBe('neutral')
  })
})
