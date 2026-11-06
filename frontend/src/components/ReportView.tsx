import type { BodyResult, Issue, PacingResult, Report, VoiceResult } from '../api/client'
import { LineChart, Radar } from './charts'
import { CATEGORY_LABELS, CATEGORY_ORDER, scoreColor } from '../lib/categories'
import { formatTime } from '../lib/format'

interface Props {
  report: Report
  pacing: PacingResult | null
  voice: VoiceResult | null
  body: BodyResult | null
  onSeek: (t: number) => void
}

const card = 'rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900'

function ScoreGrid({ report }: { report: Report }) {
  const cats = CATEGORY_ORDER.map((c) => report.scores.categories[c]).filter(Boolean)
  return (
    <div className={`${card} grid items-center gap-6 md:grid-cols-[1fr_2fr]`}>
      {cats.filter((c) => c.score !== null).length >= 3 ? (
        <Radar items={cats.filter((c) => c.score !== null).map((c) => ({ label: CATEGORY_LABELS[c.category], value: c.score }))} />
      ) : (
        <div />
      )}
      <div>
        <p className="text-sm text-slate-500">Overall score</p>
        <p className={`text-5xl font-semibold tabular-nums ${scoreColor(report.overall)}`}>
          {report.overall !== null ? Math.round(report.overall) : '–'}
        </p>
        {report.summary && <p className="mt-3 text-slate-700 dark:text-slate-300">{report.summary}</p>}
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {cats.map((c) => (
            <div key={c.category} title={c.reason ?? undefined}>
              <p className="text-xs text-slate-500">{CATEGORY_LABELS[c.category]}</p>
              <p className={`text-xl font-semibold tabular-nums ${scoreColor(c.score)}`}>
                {c.score !== null ? Math.round(c.score) : '–'}
              </p>
              {c.status === 'not_scored' && <p className="text-[11px] leading-tight text-slate-400">{c.reason}</p>}
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-400">
          {report.generated_by === 'llm'
            ? `Coaching written by a local AI (${report.llm_model}) from your measured metrics only.`
            : report.llm_error
              ? `${report.llm_error} The coaching below uses built-in templates.`
              : 'Coaching uses built-in templates.'}
        </p>
      </div>
    </div>
  )
}

function Charts({ pacing, voice, body, onSeek }: { pacing: PacingResult | null; voice: VoiceResult | null; body: BodyResult | null; onSeek: (t: number) => void }) {
  const charts = [
    pacing && pacing.wpm_series.length > 1 && (
      <LineChart key="wpm" title="Pace over time" points={pacing.wpm_series} unit="Words per minute" band={[110, 170]} bandLabel="comfortable pace" yMin={0} onSeek={onSeek} />
    ),
    voice && (
      <LineChart key="pitch" title="Pitch over time" points={voice.pitch_series} unit="Pitch in Hz (more movement sounds more expressive)" onSeek={onSeek} />
    ),
    voice && (
      <LineChart key="volume" title="Volume over time" points={voice.volume_series} unit="Loudness in dB" onSeek={onSeek} />
    ),
    body && body.eye_contact_ratio !== null && (
      <LineChart key="eye" title="Eye contact over time" points={body.eye_contact_series.map((p) => ({ t: p.t, value: p.value === null ? null : p.value * 100 }))} unit="Percent of time looking at the camera (estimate)" band={[75, 100]} bandLabel="good eye contact" yMin={0} yMax={100} format={(v) => `${v.toFixed(0)}%`} onSeek={onSeek} />
    ),
  ].filter(Boolean)
  if (!charts.length) return null
  return <div className={`${card} grid gap-6 md:grid-cols-2`}>{charts}</div>
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

export function ReportView({ report, pacing, voice, body, onSeek }: Props) {
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

      <Charts pacing={pacing} voice={voice} body={body} onSeek={onSeek} />
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
              {s.category === 'pronunciation' && (
                <p className="mt-2 text-xs text-slate-500">
                  This is an estimate. It compares your sounds with a standard US English reference, so accents can be
                  flagged even when you are easy to understand.
                </p>
              )}
              {(s.category === 'eye_contact' || s.category === 'posture' || s.category === 'body_language') && (
                <p className="mt-2 text-xs text-slate-500">Estimated from camera tracking.</p>
              )}
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

      {report.clarity && (
        <div className={card}>
          <h3 className="mb-2 font-semibold">Sentence clarity</h3>
          <p className="text-sm text-slate-700 dark:text-slate-300">{report.clarity.feedback}</p>
          {report.clarity.examples.length > 0 && (
            <ul className="mt-3 space-y-3 text-sm">
              {report.clarity.examples.map((e) => (
                <li key={e.original} className="rounded-md bg-slate-50 p-3 dark:bg-slate-800">
                  <p className="text-slate-500">
                    <span className="font-medium">You said:</span> “{e.original}”
                  </p>
                  <p className="mt-1">
                    <span className="font-medium">Try:</span> “{e.suggestion}”
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
