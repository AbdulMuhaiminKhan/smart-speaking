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

const W = 960
const H = 230
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
          className="fill-emerald-500/12"
        />
      )}
      {/* Five staff lines across the range, a bar line per session. */}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} x1={L} x2={W - R} y1={y(lo + f * span)} y2={y(lo + f * span)} className="stroke-slate-300 dark:stroke-slate-700" strokeWidth={1} />
      ))}
      {points.map((p, i) => (
        <line key={p.id} x1={x(i)} x2={x(i)} y1={y(hi)} y2={y(lo)} className="stroke-slate-200 dark:stroke-slate-800" strokeWidth={1} />
      ))}
      <line x1={W - R} x2={W - R} y1={y(hi)} y2={y(lo)} className="stroke-slate-500" strokeWidth={2.5} />
      {ticks.map((v) => (
        <text key={v} x={L - 8} y={y(v) + 4} textAnchor="end" fontSize={12} className="fill-slate-500">
          {format(v)}
        </text>
      ))}
      <path d={d} fill="none" strokeWidth={1.5} strokeLinejoin="round" className="stroke-slate-500" />
      {pts.map((p, k) => {
        const last = k === pts.length - 1
        return (
          <ellipse
            key={p.id}
            cx={x(p.i)}
            cy={y(p.value)}
            rx={8}
            ry={5.6}
            transform={`rotate(-22 ${x(p.i)} ${y(p.value)})`}
            strokeWidth={2}
            className={`cursor-pointer ${last ? 'fill-brand-600 stroke-brand-600' : 'fill-slate-800 stroke-slate-800 dark:fill-slate-100 dark:stroke-slate-100'} hover:fill-brand-500`}
            onClick={() => navigate(`/sessions/${p.id}`)}
          >
            <title>{`${p.title} · ${formatDate(p.date, false)}: ${format(p.value)}`}</title>
          </ellipse>
        )
      })}
      <text x={L} y={H - 8} fontSize={12} className="fill-slate-500">
        {formatDate(points[0].date, false)}
      </text>
      <text x={W - R} y={H - 8} fontSize={12} textAnchor="end" className="fill-slate-500">
        {formatDate(points[n - 1].date, false)}
      </text>
    </svg>
  )
}
