// The script with what you said, skipped, added or changed, each linked to the video.
import type { LanguageResult } from '../api/client'
import { useI18n } from '../i18n'
import { formatTime } from '../lib/format'

export function ScriptDriftCard({ language, onSeek }: { language: LanguageResult | null; onSeek: (t: number) => void }) {
  const { t } = useI18n()
  const sc = language?.script
  if (!sc) return null
  const parts = sc.parts ?? []
  const count = (k: string) => parts.filter((p) => p.kind === k).length
  return (
    <section className="card">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-semibold">{t('script.report_title')}</h3>
        <p className="text-sm text-slate-500">
          {t('script.summary', {
            coverage: Math.round(sc.coverage * 100),
            extra: Math.round(sc.extra_ratio * 100),
            skipped: count('skipped') + count('changed'),
            added: count('added'),
          })}
        </p>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs">
        <span className="text-slate-500">{t('script.legend_said')}</span>
        <span className="text-red-600 line-through">{t('script.legend_skipped')}</span>
        <span className="rounded bg-amber-100 px-1 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">{t('script.legend_added')}</span>
      </div>
      {parts.length > 0 ? (
        <p dir="auto" className="mt-4 max-h-96 overflow-y-auto leading-loose">
          {parts.map((p, i) => {
            const jump = () => onSeek(Math.max(0, p.start - 1))
            if (p.kind === 'said') return <span key={i}>{p.script} </span>
            return (
              <span key={i}>
              <button
                type="button"
                onClick={jump}
                title={`${formatTime(p.start)} · ${t(`script.kind_${p.kind}`)}`}
                className="text-start hover:ring-2 hover:ring-brand-400"
              >
                {p.script && <span className="text-red-600 line-through decoration-2 dark:text-red-400">{p.script}</span>}
                {p.script && p.spoken && ' '}
                {p.spoken && (
                  <span className="rounded bg-amber-100 px-1 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">{p.spoken}</span>
                )}
              </button>{' '}
              </span>
            )
          })}
        </p>
      ) : (
        <ul className="mt-3 list-disc ps-5 text-sm">
          {sc.skipped.map((x) => (
            <li key={x} className="text-red-600">{x}</li>
          ))}
        </ul>
      )}
    </section>
  )
}
