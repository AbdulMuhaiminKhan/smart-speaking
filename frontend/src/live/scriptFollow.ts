// Follows a speaker through their script using the live transcript, so the
// teleprompter can scroll with them and notice skipped passages.

const URDU = new Map([
  ['ي', 'ی'],
  ['ى', 'ی'],
  ['ك', 'ک'],
])

/** Same idea as the server's normalize(): lowercase, letters and digits only. */
export function norm(word: string): string {
  return word
    .toLowerCase()
    .replace(/’/g, "'")
    .replace(/[يىك]/g, (c) => URDU.get(c) ?? c)
    .replace(/[^\p{L}\p{N}']+/gu, '')
}

export function tokenize(script: string): { text: string; key: string }[] {
  return script
    .split(/\s+/)
    .filter(Boolean)
    .map((text) => ({ text, key: norm(text) }))
    .filter((w) => w.key)
}

const PROBE = 5 // recent words used to find the spot
const BACK = 15 // how far back we look (re-reading a line)
const AHEAD = 120 // how far ahead we look (skipping a passage)

/**
 * The script index just after the best match of the speaker's latest words, searching
 * near `from`. Returns `from` when nothing matches well enough.
 */
export function followPosition(script: string[], recent: string[], from: number): number {
  const probe = recent.map(norm).filter(Boolean).slice(-PROBE)
  if (probe.length < 2 || script.length === 0) return from
  let best = -1
  let bestScore = 0
  const lo = Math.max(0, from - BACK)
  const hi = Math.min(script.length, from + AHEAD)
  for (let end = lo + 1; end <= hi; end++) {
    // Count probe words found, in order, ending at `end`.
    let score = 0
    let k = end - 1
    for (let p = probe.length - 1; p >= 0 && k >= 0 && k >= end - probe.length - 2; p--) {
      if (script[k] === probe[p]) {
        score++
        k--
      } else if (k - 1 >= 0 && script[k - 1] === probe[p]) {
        score += 0.6
        k -= 2
      }
    }
    // Prefer matches close to where we were, so repeated phrases do not jump.
    const adjusted = score - Math.abs(end - from) * 0.004
    if (adjusted > bestScore) {
      bestScore = adjusted
      best = end
    }
  }
  return best > 0 && bestScore >= Math.min(3, probe.length) - 0.5 ? best : from
}

/** A forward jump this many words or more counts as a skipped passage. */
export const SKIP_WORDS = 8

/**
 * Word ranges in script[from, to) that were jumped over: runs of at least
 * MIN_SKIP_RUN script words that do not appear among the words just heard.
 */
export const MIN_SKIP_RUN = 4

export function skippedRanges(script: string[], from: number, to: number, heard: string[]): [number, number][] {
  const said = new Set(heard.map(norm).filter(Boolean))
  const out: [number, number][] = []
  let runStart = -1
  for (let i = from; i <= to; i++) {
    const missing = i < to && !said.has(script[i])
    if (missing && runStart < 0) runStart = i
    if (!missing && runStart >= 0) {
      if (i - runStart >= MIN_SKIP_RUN) out.push([runStart, i])
      runStart = -1
    }
  }
  return out
}
