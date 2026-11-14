import type { Issue, PacingResult, Transcript } from '../api/client'
import { useI18n } from '../i18n'
import { formatTime } from '../lib/format'

/** Score marks for pauses: a breath mark (good pause), a caesura (hesitation), a fermata (long silence). */
export function PauseMark({ kind, className = '' }: { kind: 'effective' | 'hesitation' | 'awkward'; className?: string }) {
  return (
    <svg width="12" height="14" viewBox="0 0 12 14" className={`inline-block align-[-2px] ${className}`} aria-hidden="true">
      {kind === 'effective' && <path d="M6 2.5c1.6 0 2.4 1 2.4 2.2S7.4 7 5.6 7.6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />}
      {kind === 'hesitation' && <path d="M3 12L6.5 2M6.5 12L10 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />}
      {kind === 'awkward' && (
        <>
          <path d="M1.5 9a4.5 4.5 0 0 1 9 0" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="6" cy="8.6" r="1.3" fill="currentColor" />
        </>
      )}
    </svg>
  )
}

interface Props {
  transcript: Transcript
  currentTime: number
  onSeek: (seconds: number) => void
  issues?: Issue[]
  pauses?: PacingResult['pauses']
}

const MARK: Record<string, string> = {
  filler: 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100',
  hedge: 'bg-violet-100 text-violet-900 dark:bg-violet-900/50 dark:text-violet-100',
  repetition: 'bg-sky-100 text-sky-900 dark:bg-sky-900/50 dark:text-sky-100',
  mispronounced: 'bg-rose-100 text-rose-900 dark:bg-rose-900/50 dark:text-rose-100',
}

const PAUSE: Record<string, string> = {
  effective: 'text-emerald-500',
  hesitation: 'text-amber-500',
  awkward: 'text-red-500',
}

export function TranscriptLegend() {
  const { t } = useI18n()
  return (
    <div className="mb-3 flex flex-wrap gap-2 text-xs">
      <span className={`rounded px-1.5 ${MARK.filler}`}>{t('tr.filler')}</span>
      <span className={`rounded px-1.5 ${MARK.hedge}`}>{t('tr.hedge')}</span>
      <span className={`rounded px-1.5 ${MARK.repetition}`}>{t('tr.repeat')}</span>
      <span className={`rounded px-1.5 ${MARK.mispronounced}`}>{t('tr.unclear_estimate')}</span>
      <span className={PAUSE.effective}><PauseMark kind="effective" /> {t('tr.good_pause')}</span>
      <span className={PAUSE.hesitation}><PauseMark kind="hesitation" /> {t('tr.hesitation')}</span>
      <span className={PAUSE.awkward}><PauseMark kind="awkward" /> {t('tr.long_silence')}</span>
      <span className="underline decoration-amber-400 decoration-dotted underline-offset-4">{t('tr.unclear_word')}</span>
    </div>
  )
}

export function TranscriptView({ transcript, currentTime, onSeek, issues = [], pauses = [] }: Props) {
  const { t } = useI18n()
  const marks = issues.filter((i) => i.kind in MARK)
  const markFor = (start: number, end: number) =>
    marks.find((m) => start >= m.start - 0.01 && end <= m.end + 0.01)?.kind
  const pauseAfter = new Map(pauses.map((p) => [p.start.toFixed(3), p]))

  return (
    <div className="space-y-4">
      {transcript.segments.map((seg) => (
        <div key={seg.id} className="flex gap-3">
          <button
            type="button"
            onClick={() => onSeek(seg.start)}
            className="mt-0.5 shrink-0 font-mono text-xs text-slate-400 hover:text-brand-600"
          >
            {formatTime(seg.start)}
          </button>
          <p dir="auto" className="leading-relaxed">
            {seg.words.map((w, i) => {
              const active = currentTime >= w.start && currentTime < w.end
              const unsure = w.probability < 0.5
              const kind = markFor(w.start, w.end)
              const pause = pauseAfter.get(w.end.toFixed(3))
              return (
                <span key={i}>
                  <button
                    type="button"
                    onClick={() => onSeek(w.start)}
                    title={`${formatTime(w.start)} · ${t('tr.confidence', { n: (w.probability * 100).toFixed(0) })}`}
                    className={`rounded px-0.5 transition ${kind ? MARK[kind] : ''} ${
                      active ? 'ring-2 ring-brand-500' : ''
                    } ${unsure ? 'underline decoration-amber-400 decoration-dotted underline-offset-4' : ''} hover:bg-slate-100 dark:hover:bg-slate-800`}
                  >
                    {w.text}
                  </button>
                  {pause && (
                    <span className={`mx-0.5 font-semibold ${PAUSE[pause.kind]}`} title={t('tr.pause', { n: pause.duration.toFixed(1) })}>
                      <PauseMark kind={pause.kind} />
                    </span>
                  )}{' '}
                </span>
              )
            })}
          </p>
        </div>
      ))}
    </div>
  )
}
