/** Mean of the last `k` values against the mean of the `k` before them. */
export function recentChange(values: (number | null)[], k = 3): { recent: number; before: number } | null {
  const v = values.filter((x): x is number => x !== null)
  if (v.length < 2) return null
  const size = Math.min(k, Math.floor(v.length / 2))
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length
  return { recent: mean(v.slice(-size)), before: mean(v.slice(-2 * size, -size)) }
}
