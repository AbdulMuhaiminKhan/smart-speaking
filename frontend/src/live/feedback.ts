// Instant feedback computed in the browser: filler alerts, loudness and pauses.

/** Filler phrases whose count went up between two live updates (one entry per new use). */
export function newFillers(prev: Record<string, number>, next: Record<string, number>): string[] {
  const out: string[] = []
  for (const [phrase, n] of Object.entries(next)) {
    for (let i = prev[phrase] ?? 0; i < n; i++) out.push(phrase)
  }
  return out
}

export const SPEECH_RMS = 0.012 // above this a chunk counts as voice
export const PAUSE_WARN_S = 3 // a silence this long gets a gentle nudge

/** Tracks the current silence after speech started, with a short hold so breaths do not count. */
export class PauseTracker {
  private lastVoice = -1
  private started = false

  update(rms: number, nowMs: number): { speaking: boolean; silenceS: number } {
    if (rms >= SPEECH_RMS) {
      this.lastVoice = nowMs
      this.started = true
    }
    if (!this.started) return { speaking: false, silenceS: 0 }
    const silence = (nowMs - this.lastVoice) / 1000
    return { speaking: silence < 0.35, silenceS: silence < 0.35 ? 0 : silence }
  }
}

/** RMS to a 0..1 meter value on a decibel scale (-60 dB to 0 dB). */
export function meterLevel(rms: number): number {
  if (rms <= 0) return 0
  const db = 20 * Math.log10(rms)
  return Math.max(0, Math.min(1, (db + 60) / 60))
}

export type PaceZone = 'none' | 'slow' | 'good' | 'fast'

export function paceZone(wpm: number | null, low = 110, high = 170): PaceZone {
  if (wpm === null) return 'none'
  if (wpm < low) return 'slow'
  if (wpm > high) return 'fast'
  return 'good'
}
