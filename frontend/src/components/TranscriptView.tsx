import type { Issue, PacingResult, Transcript } from '../api/client'
import { formatTime } from '../lib/format'

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
}

const PAUSE: Record<string, string> = {
  effective: 'text-emerald-500',
  hesitation: 'text-amber-500',
  awkward: 'text-red-500',
}

export function TranscriptLegend() {
  return (
    <div className="mb-3 flex flex-wrap gap-2 text-xs">
      <span className={`rounded px-1.5 ${MARK.filler}`}>filler</span>
      <span className={`rounded px-1.5 ${MARK.hedge}`}>hedge</span>
      <span className={`rounded px-1.5 ${MARK.repetition}`}>repeat</span>
      <span className={PAUSE.effective}>‖ good pause</span>
      <span className={PAUSE.hesitation}>‖ hesitation</span>
      <span className={PAUSE.awkward}>‖ long silence</span>
      <span className="underline decoration-amber-400 decoration-dotted underline-offset-4">unclear word</span>
    </div>
  )
}

export function TranscriptView({ transcript, currentTime, onSeek, issues = [], pauses = [] }: Props) {
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
          <p className="leading-relaxed">
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
                    title={`${formatTime(w.start)} · confidence ${(w.probability * 100).toFixed(0)}%`}
                    className={`rounded px-0.5 transition ${kind ? MARK[kind] : ''} ${
                      active ? 'ring-2 ring-brand-500' : ''
                    } ${unsure ? 'underline decoration-amber-400 decoration-dotted underline-offset-4' : ''} hover:bg-slate-100 dark:hover:bg-slate-800`}
                  >
                    {w.text}
                  </button>
                  {pause && (
                    <span className={`mx-0.5 font-semibold ${PAUSE[pause.kind]}`} title={`${pause.duration.toFixed(1)} s pause`}>
                      ‖
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
