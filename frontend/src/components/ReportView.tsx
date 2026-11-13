import type { BodyResult, Issue, PacingResult, Report, VoiceEmotionResult, VoiceResult } from '../api/client'
import { EmotionsCard } from './EmotionsCard'
import { LineChart, Radar } from './charts'
import { useI18n } from '../i18n'
import { CATEGORY_ORDER, scoreColor } from '../lib/categories'
import { issueMessage } from '../lib/issues'
import { formatTime } from '../lib/format'

interface Props {
  report: Report
  pacing: PacingResult | null
  voice: VoiceResult | null
  body: BodyResult | null
  voiceEmotion: VoiceEmotionResult | null
  duration: number
  onSeek: (t: number) => void
}

const card = 'rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900'

function ScoreGrid({ report }: { report: Report }) {
  const { t } = useI18n()
  const cats = CATEGORY_ORDER.map((c) => report.scores.categories[c]).filter(Boolean)
  return (
    <div className={`${card} grid items-center gap-6 md:grid-cols-[1fr_2fr]`}>
      {cats.filter((c) => c.score !== null).length >= 3 ? (
        <Radar items={cats.filter((c) => c.score !== null).map((c) => ({ label: t(`cat.${c.category}`), value: c.score }))} />
      ) : (
        <div />
      )}
      <div>
        <p className="text-sm text-slate-500">{t('report.overall')}</p>
        <p className={`text-5xl font-semibold tabular-nums ${scoreColor(report.overall)}`}>
          {report.overall !== null ? Math.round(report.overall) : '–'}
        </p>
        {report.summary && <p dir="auto" className="mt-3 text-slate-700 dark:text-slate-300">{report.summary}</p>}
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {cats.map((c) => (
            <div key={c.category} title={c.reason ?? undefined}>
              <p className="text-xs text-slate-500">{t(`cat.${c.category}`)}</p>
              <p className={`text-xl font-semibold tabular-nums ${scoreColor(c.score)}`}>
                {c.score !== null ? Math.round(c.score) : '–'}
              </p>
              {c.status === 'not_scored' && <p className="text-[11px] leading-tight text-slate-400">{c.reason}</p>}
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-400">
          {report.generated_by === 'llm'
            ? t('report.coach_llm', { model: report.llm_model })
            : report.llm_error
              ? t('report.coach_template_error')
              : t('report.coach_template')}
        </p>
      </div>
    </div>
  )
}

function Charts({ pacing, voice, body, onSeek }: { pacing: PacingResult | null; voice: VoiceResult | null; body: BodyResult | null; onSeek: (t: number) => void }) {
  const { t } = useI18n()
  const charts = [
    pacing && pacing.wpm_series.length > 1 && (
      <LineChart key="wpm" title={t('chart.pace')} points={pacing.wpm_series} unit={t('chart.pace_unit')} band={[110, 170]} bandLabel={t('chart.pace_band')} yMin={0} onSeek={onSeek} />
    ),
    voice && (
      <LineChart key="pitch" title={t('chart.pitch')} points={voice.pitch_series} unit={t('chart.pitch_unit')} onSeek={onSeek} />
    ),
    voice && (
      <LineChart key="volume" title={t('chart.volume')} points={voice.volume_series} unit={t('chart.volume_unit')} onSeek={onSeek} />
    ),
    body && body.eye_contact_ratio !== null && (
      <LineChart key="eye" title={t('chart.eye')} points={body.eye_contact_series.map((p) => ({ t: p.t, value: p.value === null ? null : p.value * 100 }))} unit={t('chart.eye_unit')} band={[75, 100]} bandLabel={t('chart.eye_band')} yMin={0} yMax={100} format={(v) => `${v.toFixed(0)}%`} onSeek={onSeek} />
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
  const { t, tk } = useI18n()
  return (
    <div className={card}>
      <h3 className="mb-3 font-semibold">{t('report.mistakes')}</h3>
      {issues.length === 0 ? (
        <p className="text-sm text-slate-500">{t('report.no_issues')}</p>
      ) : (
        <ul className="max-h-80 space-y-1 overflow-y-auto pe-2">
          {issues.map((i) => (
            <li key={i.id}>
              <button
                type="button"
                onClick={() => onSeek(Math.max(0, i.start - 1))}
                className="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <span className="w-10 shrink-0 font-mono text-xs text-slate-400">{formatTime(i.start)}</span>
                <span className={`h-2 w-2 shrink-0 rounded-full ${severityDot[i.severity]}`} />
                <span className="flex-1">{issueMessage(i, tk)}</span>
                <span className="text-xs text-slate-400">{t(`cat.${i.category}`)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ReportView({ report, pacing, voice, body, voiceEmotion, duration, onSeek }: Props) {
  const { t } = useI18n()
  return (
    <div className="space-y-6">
      <ScoreGrid report={report} />

      <div className="grid gap-6 md:grid-cols-2">
        <div className={card}>
          <h3 className="mb-2 font-semibold text-emerald-700 dark:text-emerald-400">{t('report.well')}</h3>
          <ul dir="auto" className="list-disc space-y-1 ps-5 text-sm">
            {report.strengths.length ? report.strengths.map((s) => <li key={s}>{s}</li>) : <li>{t('report.well_empty')}</li>}
          </ul>
        </div>
        <div className={card}>
          <h3 className="mb-2 font-semibold text-red-700 dark:text-red-400">{t('report.gaps')}</h3>
          <ul dir="auto" className="list-disc space-y-1 ps-5 text-sm">
            {report.gaps.length ? report.gaps.map((g) => <li key={g.rule_id}>{g.message}</li>) : <li>{t('report.gaps_empty')}</li>}
          </ul>
        </div>
      </div>

      {report.top_fixes.length > 0 && (
        <div className={card}>
          <h3 className="mb-3 font-semibold">{t('report.top_fixes', { n: report.top_fixes.length })}</h3>
          <ol dir="auto" className="space-y-3">
            {report.top_fixes.map((f, i) => (
              <li key={f.title} className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-600 text-xs font-semibold text-white">{i + 1}</span>
                <div className="text-sm">
                  <p className="font-medium">{f.title}</p>
                  <p className="text-slate-600 dark:text-slate-400">{f.how}</p>
                  <p className="mt-1 text-slate-500">
                    <span className="font-medium">{t('report.drill')}</span> {f.drill}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      <Charts pacing={pacing} voice={voice} body={body} onSeek={onSeek} />
      <EmotionsCard body={body} voiceEmotion={voiceEmotion} duration={duration} onSeek={onSeek} />
      <Timeline issues={report.issues} onSeek={onSeek} />

      <div className="grid gap-6 md:grid-cols-3">
        {[...report.sections]
          .sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category))
          .filter((s) => s.status === 'scored')
          .map((s) => (
            <div key={s.category} className={card}>
              <div className="mb-2 flex items-baseline justify-between">
                <h3 className="font-semibold">{t(`cat.${s.category}`)}</h3>
                <span className={`font-semibold tabular-nums ${scoreColor(s.score)}`}>{s.score !== null ? Math.round(s.score) : '–'}</span>
              </div>
              <ul dir="auto" className="list-disc space-y-1 ps-5 text-sm">
                {s.what_happened.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
              {s.category === 'pronunciation' && (
                <p className="mt-2 text-xs text-slate-500">{t('report.pron_note')}</p>
              )}
              {(s.category === 'eye_contact' || s.category === 'posture' || s.category === 'body_language') && (
                <p className="mt-2 text-xs text-slate-500">{t('report.camera_note')}</p>
              )}
              {s.why_it_matters && <p dir="auto" className="mt-3 text-sm text-slate-500">{s.why_it_matters}</p>}
              {s.how_to_fix.length > 0 && (
                <ul dir="auto" className="mt-3 space-y-1 text-sm">
                  {s.how_to_fix.map((h) => (
                    <li key={h}><span className="inline-block rtl:-scale-x-100">→</span> {h}</li>
                  ))}
                </ul>
              )}
              {s.drill && (
                <p className="mt-3 rounded-md bg-slate-50 p-2 text-sm dark:bg-slate-800">
                  <span className="font-medium">{t('report.practice_drill')}</span> {s.drill}
                </p>
              )}
            </div>
          ))}
      </div>

      {report.clarity && (
        <div className={card}>
          <h3 className="mb-2 font-semibold">{t('report.clarity')}</h3>
          <p dir="auto" className="text-sm text-slate-700 dark:text-slate-300">{report.clarity.feedback}</p>
          {report.clarity.examples.length > 0 && (
            <ul className="mt-3 space-y-3 text-sm">
              {report.clarity.examples.map((e) => (
                <li key={e.original} className="rounded-md bg-slate-50 p-3 dark:bg-slate-800">
                  <p className="text-slate-500">
                    <span className="font-medium">{t('report.you_said')}</span> <bdi>“{e.original}”</bdi>
                  </p>
                  <p className="mt-1">
                    <span className="font-medium">{t('report.try')}</span> <bdi>“{e.suggestion}”</bdi>
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
