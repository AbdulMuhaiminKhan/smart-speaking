// Line chart of one value per session, oldest to newest. Click a point to open that session.
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'

export interface TrendPoint {
  id: string
  title: string
  date: string
  value: number | null
}

interface Props {
  points: TrendPoint[]
  label: string
  band?: [number, number] // target range, shaded green
  yMin?: number
  yMax?: number
  format?: (v: number) => string
}

const W = 640
const H = 200
const L = 40
const R = 16
const T = 12
const B = 28

export function TrendChart({ points, label, band, yMin, yMax, format = (v) => String(Math.round(v)) }: Props) {
  const { t, formatDate } = useI18n()
  const navigate = useNavigate()
  const pts = points.map((p, i) => ({ ...p, i })).filter((p): p is typeof p & { value: number } => p.value !== null)
  if (pts.length < 2) {
    return <p className="py-10 text-center text-sm text-slate-500">{t('dash.need_two')}</p>
  }
  const vals = pts.map((p) => p.value)
  const lo = yMin ?? Math.min(...vals, band?.[0] ?? Infinity) * 0.9
  const hi = yMax ?? Math.max(...vals, band?.[1] ?? -Infinity) * 1.1
  const span = hi - lo || 1
  const n = points.length
  const x = (i: number) => L + (i / Math.max(1, n - 1)) * (W - L - R)
  const y = (v: number) => T + (1 - (Math.min(hi, Math.max(lo, v)) - lo) / span) * (H - T - B)
  const d = pts.map((p, k) => `${k ? 'L' : 'M'}${x(p.i).toFixed(1)} ${y(p.value).toFixed(1)}`).join(' ')
  const ticks = [lo, lo + span / 2, hi]
  return (
    <svg direction="ltr" viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={label}>
      {band && (
        <rect
          x={L}
          y={y(Math.min(band[1], hi))}
          width={W - L - R}
          height={Math.max(0, y(Math.max(band[0], lo)) - y(Math.min(band[1], hi)))}
          className="fill-emerald-500/10"
        />
      )}
      {ticks.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="stroke-slate-200 dark:stroke-slate-800" />
          <text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize={11} className="fill-slate-400">
            {format(v)}
          </text>
        </g>
      ))}
      <path d={d} fill="none" strokeWidth={2.5} strokeLinejoin="round" className="stroke-brand-600" />
      {pts.map((p) => (
        <circle
          key={p.id}
          cx={x(p.i)}
          cy={y(p.value)}
          r={5}
          strokeWidth={2}
          className="cursor-pointer fill-white stroke-brand-600 dark:fill-slate-900"
          onClick={() => navigate(`/sessions/${p.id}`)}
        >
          <title>{`${p.title} · ${formatDate(p.date, false)}: ${format(p.value)}`}</title>
        </circle>
      ))}
      <text x={L} y={H - 8} fontSize={11} className="fill-slate-400">
        {formatDate(points[0].date, false)}
      </text>
      <text x={W - R} y={H - 8} fontSize={11} textAnchor="end" className="fill-slate-400">
        {formatDate(points[n - 1].date, false)}
      </text>
    </svg>
  )
}
