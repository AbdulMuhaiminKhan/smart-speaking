import type { Issue, PacingResult, Report } from '../api/client'
import { CATEGORY_LABELS, CATEGORY_ORDER, scoreColor } from '../lib/categories'
import { formatTime } from '../lib/format'

interface Props {
  report: Report
  pacing: PacingResult | null
  onSeek: (t: number) => void
}

const card = 'rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900'

function ScoreGrid({ report }: { report: Report }) {
  const cats = CATEGORY_ORDER.map((c) => report.scores.categories[c]).filter(Boolean)
  return (
    <div className={`${card} flex flex-wrap items-center gap-6`}>
      <div className="pr-6 sm:border-r sm:border-slate-200 dark:sm:border-slate-800">
        <p className="text-sm text-slate-500">Overall</p>
        <p className={`text-5xl font-semibold tabular-nums ${scoreColor(report.overall)}`}>
          {report.overall !== null ? Math.round(report.overall) : '–'}
        </p>
      </div>
      <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {cats.map((c) => (
          <div key={c.category} title={c.reason ?? undefined}>
            <p className="text-xs text-slate-500">{CATEGORY_LABELS[c.category]}</p>
            <p className={`text-2xl font-semibold tabular-nums ${scoreColor(c.score)}`}>
              {c.score !== null ? Math.round(c.score) : '–'}
            </p>
            {c.status === 'not_scored' && <p className="text-[11px] text-slate-400">Coming soon</p>}
          </div>
        ))}
      </div>
    </div>
  )
}

function WpmChart({ pacing }: { pacing: PacingResult }) {
  const pts = pacing.wpm_series.filter((p) => p.value !== null) as { t: number; value: number }[]
  if (pts.length < 2) return null
  const W = 600
  const H = 120
  const maxT = pts[pts.length - 1].t
  const minT = pts[0].t
  const maxV = Math.max(200, ...pts.map((p) => p.value))
  const x = (t: number) => ((t - minT) / (maxT - minT || 1)) * (W - 40) + 30
  const y = (v: number) => H - 20 - (v / maxV) * (H - 30)
  const path = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)} ${y(p.value).toFixed(1)}`).join(' ')
  return (
    <div className={card}>
      <h3 className="mb-2 font-semibold">Pace over time</h3>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Words per minute over time">
        <rect x={30} y={y(170)} width={W - 40} height={y(110) - y(170)} className="fill-emerald-500/10" />
        <text x={0} y={y(170) + 4} className="fill-slate-400 text-[10px]">170</text>
        <text x={0} y={y(110) + 4} className="fill-slate-400 text-[10px]">110</text>
        <path d={path} fill="none" strokeWidth={2} className="stroke-brand-600" />
        <text x={30} y={H - 4} className="fill-slate-400 text-[10px]">{formatTime(minT)}</text>
        <text x={W - 10} y={H - 4} textAnchor="end" className="fill-slate-400 text-[10px]">{formatTime(maxT)}</text>
      </svg>
      <p className="text-xs text-slate-500">Green band: comfortable pace (110 to 170 words per minute).</p>
    </div>
  )
}

const severityDot: Record<Issue['severity'], string> = {
  major: 'bg-red-500',
  minor: 'bg-amber-400',
  info: 'bg-slate-400',
}

function Timeline({ issues, onSeek }: { issues: Issue[]; onSeek: (t: number) => void }) {
  return (
    <div className={card}>
      <h3 className="mb-3 font-semibold">Mistakes timeline</h3>
      {issues.length === 0 ? (
        <p className="text-sm text-slate-500">No issues found.</p>
      ) : (
        <ul className="max-h-80 space-y-1 overflow-y-auto pr-2">
          {issues.map((i) => (
            <li key={i.id}>
              <button
                type="button"
                onClick={() => onSeek(Math.max(0, i.start - 1))}
                className="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <span className="w-10 shrink-0 font-mono text-xs text-slate-400">{formatTime(i.start)}</span>
                <span className={`h-2 w-2 shrink-0 rounded-full ${severityDot[i.severity]}`} />
                <span className="flex-1">{i.message}</span>
                <span className="text-xs text-slate-400">{CATEGORY_LABELS[i.category]}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ReportView({ report, pacing, onSeek }: Props) {
  return (
    <div className="space-y-6">
      <ScoreGrid report={report} />

      <div className="grid gap-6 md:grid-cols-2">
        <div className={card}>
          <h3 className="mb-2 font-semibold text-emerald-700 dark:text-emerald-400">What you did well</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {report.strengths.length ? report.strengths.map((s) => <li key={s}>{s}</li>) : <li>Keep practicing to build strengths.</li>}
          </ul>
        </div>
        <div className={card}>
          <h3 className="mb-2 font-semibold text-red-700 dark:text-red-400">Biggest gaps</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {report.gaps.length ? report.gaps.map((g) => <li key={g.rule_id}>{g.message}</li>) : <li>No major gaps. Nice work.</li>}
          </ul>
        </div>
      </div>

      {report.top_fixes.length > 0 && (
        <div className={card}>
          <h3 className="mb-3 font-semibold">Your top {report.top_fixes.length} fixes for next time</h3>
          <ol className="space-y-3">
            {report.top_fixes.map((f, i) => (
              <li key={f.title} className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-600 text-xs font-semibold text-white">{i + 1}</span>
                <div className="text-sm">
                  <p className="font-medium">{f.title}</p>
                  <p className="text-slate-600 dark:text-slate-400">{f.how}</p>
                  <p className="mt-1 text-slate-500">
                    <span className="font-medium">Drill:</span> {f.drill}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {pacing && <WpmChart pacing={pacing} />}
      <Timeline issues={report.issues} onSeek={onSeek} />

      <div className="grid gap-6 md:grid-cols-3">
        {[...report.sections]
          .sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category))
          .filter((s) => s.status === 'scored')
          .map((s) => (
            <div key={s.category} className={card}>
              <div className="mb-2 flex items-baseline justify-between">
                <h3 className="font-semibold">{CATEGORY_LABELS[s.category]}</h3>
                <span className={`font-semibold tabular-nums ${scoreColor(s.score)}`}>{s.score !== null ? Math.round(s.score) : '–'}</span>
              </div>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {s.what_happened.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
              {s.why_it_matters && <p className="mt-3 text-sm text-slate-500">{s.why_it_matters}</p>}
              {s.how_to_fix.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm">
                  {s.how_to_fix.map((h) => (
                    <li key={h}>→ {h}</li>
                  ))}
                </ul>
              )}
              {s.drill && (
                <p className="mt-3 rounded-md bg-slate-50 p-2 text-sm dark:bg-slate-800">
                  <span className="font-medium">Practice drill:</span> {s.drill}
                </p>
              )}
            </div>
          ))}
      </div>
    </div>
  )
}
