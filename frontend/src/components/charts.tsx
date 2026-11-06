// Small dependency-free SVG charts used by the report.
import type { TimePoint } from '../api/client'
import { formatTime } from '../lib/format'

interface LineChartProps {
  title: string
  points: TimePoint[]
  unit: string
  band?: [number, number] // healthy range, shaded
  bandLabel?: string
  yMin?: number
  yMax?: number
  format?: (v: number) => string
  onSeek?: (t: number) => void
}

const W = 640
const H = 160
const PAD_L = 40
const PAD_R = 12
const PAD_T = 12
const PAD_B = 24

export function LineChart({ title, points, unit, band, bandLabel, yMin, yMax, format = (v) => v.toFixed(0), onSeek }: LineChartProps) {
  const pts = points.filter((p): p is { t: number; value: number } => p.value !== null)
  if (pts.length < 2) return null
  const t0 = Math.min(...points.map((p) => p.t))
  const t1 = Math.max(...points.map((p) => p.t))
  const vals = pts.map((p) => p.value)
  const lo = yMin ?? Math.min(...vals, band?.[0] ?? Infinity)
  const hi = yMax ?? Math.max(...vals, band?.[1] ?? -Infinity)
  const span = hi - lo || 1
  const x = (t: number) => PAD_L + ((t - t0) / (t1 - t0 || 1)) * (W - PAD_L - PAD_R)
  const y = (v: number) => PAD_T + (1 - (v - lo) / span) * (H - PAD_T - PAD_B)

  // Break the line where data is missing.
  const paths: string[] = []
  let current = ''
  for (const p of points) {
    if (p.value === null) {
      if (current) paths.push(current)
      current = ''
      continue
    }
    current += `${current ? 'L' : 'M'}${x(p.t).toFixed(1)} ${y(p.value).toFixed(1)}`
  }
  if (current) paths.push(current)
  const ticks = [lo, lo + span / 2, hi]

  return (
    <figure>
      <figcaption className="mb-1 text-sm font-medium">{title}</figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full cursor-pointer"
        role="img"
        aria-label={title}
        onClick={(e) => {
          if (!onSeek) return
          const rect = e.currentTarget.getBoundingClientRect()
          const px = ((e.clientX - rect.left) / rect.width) * W
          onSeek(t0 + ((px - PAD_L) / (W - PAD_L - PAD_R)) * (t1 - t0))
        }}
      >
        {band && (
          <rect
            x={PAD_L}
            y={y(Math.min(band[1], hi))}
            width={W - PAD_L - PAD_R}
            height={Math.max(0, y(Math.max(band[0], lo)) - y(Math.min(band[1], hi)))}
            className="fill-emerald-500/10"
          />
        )}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={W - PAD_R} y1={y(v)} y2={y(v)} className="stroke-slate-200 dark:stroke-slate-800" />
            <text x={PAD_L - 6} y={y(v) + 4} textAnchor="end" fontSize={11} className="fill-slate-400">
              {format(v)}
            </text>
          </g>
        ))}
        {paths.map((d) => (
          <path key={d} d={d} fill="none" strokeWidth={2} strokeLinejoin="round" className="stroke-brand-600" />
        ))}
        <text x={PAD_L} y={H - 6} fontSize={11} className="fill-slate-400">
          {formatTime(t0)}
        </text>
        <text x={W - PAD_R} y={H - 6} textAnchor="end" fontSize={11} className="fill-slate-400">
          {formatTime(t1)}
        </text>
      </svg>
      <p className="text-xs text-slate-500">
        {unit}
        {bandLabel ? ` · green band: ${bandLabel}` : ''}
        {onSeek ? ' · click to jump the video' : ''}
      </p>
    </figure>
  )
}

interface RadarProps {
  items: { label: string; value: number | null }[]
}

export function Radar({ items }: RadarProps) {
  const S = 300
  const C = S / 2
  const R = 105
  const n = items.length
  const angle = (i: number) => -Math.PI / 2 + (i / n) * Math.PI * 2
  const pt = (i: number, r: number) => [C + Math.cos(angle(i)) * r, C + Math.sin(angle(i)) * r]
  const rings = [25, 50, 75, 100]
  const shape = items
    .map((it, i) => pt(i, ((it.value ?? 0) / 100) * R))
    .map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)} ${py.toFixed(1)}`)
    .join(' ')
  return (
    <svg viewBox={`0 0 ${S} ${S}`} className="mx-auto w-full max-w-xs" role="img" aria-label="Category scores radar chart">
      {rings.map((r) => (
        <polygon
          key={r}
          points={items.map((_, i) => pt(i, (r / 100) * R).join(',')).join(' ')}
          fill="none"
          className="stroke-slate-200 dark:stroke-slate-700"
        />
      ))}
      {items.map((_, i) => {
        const [px, py] = pt(i, R)
        return <line key={i} x1={C} y1={C} x2={px} y2={py} className="stroke-slate-200 dark:stroke-slate-700" />
      })}
      <path d={`${shape} Z`} className="fill-brand-500/25 stroke-brand-600" strokeWidth={2} />
      {items.map((it, i) => {
        const [px, py] = pt(i, R + 22)
        return (
          <text key={it.label} x={px} y={py} textAnchor="middle" dominantBaseline="middle" fontSize={11} className="fill-slate-600 dark:fill-slate-300">
            <tspan x={px}>{it.label}</tspan>
            <tspan x={px} dy={13} fontWeight={600}>
              {it.value === null ? '–' : Math.round(it.value)}
            </tspan>
          </text>
        )
      })}
    </svg>
  )
}
