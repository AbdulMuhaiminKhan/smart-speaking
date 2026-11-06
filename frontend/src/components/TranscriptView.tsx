import type { Transcript } from '../api/client'
import { formatTime } from '../lib/format'

interface Props {
  transcript: Transcript
  currentTime: number
  onSeek: (seconds: number) => void
}

export function TranscriptView({ transcript, currentTime, onSeek }: Props) {
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
              return (
                <span key={i}>
                  <button
                    type="button"
                    onClick={() => onSeek(w.start)}
                    title={`${formatTime(w.start)} · confidence ${(w.probability * 100).toFixed(0)}%`}
                    className={`rounded px-0.5 transition ${
                      active ? 'bg-brand-100 text-brand-700 dark:bg-brand-700/40 dark:text-white' : ''
                    } ${unsure ? 'underline decoration-amber-400 decoration-dotted underline-offset-4' : ''} hover:bg-slate-100 dark:hover:bg-slate-800`}
                  >
                    {w.text}
                  </button>{' '}
                </span>
              )
            })}
          </p>
        </div>
      ))}
    </div>
  )
}
