export type Verdict = 'good' | 'ok' | 'work' | 'none'

/** good when inside [good], ok when inside [ok], otherwise needs work. */
export function grade(v: number | null | undefined, good: [number, number], ok: [number, number]): Verdict {
  if (v === null || v === undefined || Number.isNaN(v)) return 'none'
  if (v >= good[0] && v <= good[1]) return 'good'
  if (v >= ok[0] && v <= ok[1]) return 'ok'
  return 'work'
}

