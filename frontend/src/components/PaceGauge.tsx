// Half-circle speedometer for live words per minute, with slow / good / fast zones.
import { useI18n } from '../i18n'
import { paceZone } from '../live/feedback'
import { tempoMarking } from '../lib/tempo'

const MIN = 60
const MAX = 220

function polar(v: number, r: number): [number, number] {
  const a = Math.PI * (1 - (Math.min(MAX, Math.max(MIN, v)) - MIN) / (MAX - MIN))
  return [100 + r * Math.cos(a), 100 - r * Math.sin(a)]
}

function arc(from: number, to: number, r: number): string {
  const [x0, y0] = polar(from, r)
  const [x1, y1] = polar(to, r)
  return `M${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`
}

export function PaceGauge({ wpm, low = 110, high = 170 }: { wpm: number | null; low?: number; high?: number }) {
  const { t } = useI18n()
  const LOW = low
  const HIGH = high
  const zone = paceZone(wpm, LOW, HIGH)
  const [nx, ny] = polar(wpm ?? MIN, 62)
  const color = { none: 'text-slate-400', slow: 'text-sky-500', good: 'text-emerald-500', fast: 'text-amber-500' }[zone]
  return (
    <div>
      <svg direction="ltr" viewBox="0 0 200 112" className="w-full" role="img" aria-label={t('live.pace')}>
        <path d={arc(MIN, LOW, 80)} className="stroke-sky-400/70" strokeWidth={14} fill="none" />
        <path d={arc(LOW, HIGH, 80)} className="stroke-emerald-500/80" strokeWidth={14} fill="none" />
        <path d={arc(HIGH, MAX, 80)} className="stroke-amber-400/80" strokeWidth={14} fill="none" />
        {wpm !== null && (
          <line
            x1={100}
            y1={100}
            x2={nx}
            y2={ny}
            strokeWidth={4}
            strokeLinecap="round"
            className="stroke-slate-800 transition-all duration-700 dark:stroke-white"
          />
        )}
        <circle cx={100} cy={100} r={6} className="fill-slate-800 dark:fill-white" />
      </svg>
      <p className={`-mt-1 text-center text-3xl font-semibold tabular-nums ${color}`}>{wpm ?? '–'}</p>
      {wpm !== null && <p dir="ltr" className="tempo text-center text-base text-slate-700 dark:text-slate-200">{tempoMarking(wpm)}</p>}
      <p className="text-center text-xs text-slate-500">
        {t('common.wpm')} · {t(`live.zone_${zone}`)}
      </p>
    </div>
  )
}
