// Bar under the video with a marker for every issue. Click a marker to jump there.
import { useState } from 'react'
import type { Category, Issue } from '../api/client'
import { CATEGORY_LABELS, CATEGORY_ORDER } from '../lib/categories'
import { formatTime } from '../lib/format'

const CATEGORY_COLORS: Record<Category, string> = {
  voice: 'bg-violet-500',
  pacing: 'bg-sky-500',
  language: 'bg-amber-500',
  pronunciation: 'bg-rose-500',
  eye_contact: 'bg-emerald-500',
  posture: 'bg-orange-500',
  body_language: 'bg-teal-500',
}

interface Props {
  issues: Issue[]
  duration: number
  currentTime: number
  onSeek: (t: number) => void
}

export function VideoTimeline({ issues, duration, currentTime, onSeek }: Props) {
  const [hover, setHover] = useState<Issue | null>(null)
  if (!duration) return null
  const pct = (t: number) => `${Math.min(100, Math.max(0, (t / duration) * 100))}%`
  const lanes = CATEGORY_ORDER.filter((c) => issues.some((i) => i.category === c))

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium">Timeline</span>
        <span className="text-xs text-slate-500">{hover ? `${formatTime(hover.start)} · ${hover.message}` : 'Hover or click a marker'}</span>
      </div>
      <div
        className="relative cursor-pointer space-y-1"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect()
          onSeek(((e.clientX - rect.left) / rect.width) * duration)
        }}
      >
        {lanes.map((cat) => (
          <div key={cat} className="relative h-4 rounded bg-slate-100 dark:bg-slate-800" title={CATEGORY_LABELS[cat]}>
            {issues
              .filter((i) => i.category === cat)
              .map((i) => (
                <button
                  key={i.id}
                  type="button"
                  aria-label={`${formatTime(i.start)} ${i.message}`}
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  onClick={(e) => {
                    e.stopPropagation()
                    onSeek(Math.max(0, i.start - 1))
                  }}
                  className={`absolute top-0 h-4 rounded-sm ${CATEGORY_COLORS[cat]} ${i.severity === 'major' ? 'opacity-100' : 'opacity-60'} hover:opacity-100`}
                  style={{ left: pct(i.start), width: `max(4px, ${pct(i.end - i.start)})` }}
                />
              ))}
          </div>
        ))}
        <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-slate-900 dark:bg-white" style={{ left: pct(currentTime) }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
        {lanes.map((c) => (
          <span key={c} className="flex items-center gap-1">
            <span className={`h-2 w-2 rounded-full ${CATEGORY_COLORS[c]}`} />
            {CATEGORY_LABELS[c]}
          </span>
        ))}
      </div>
    </div>
  )
}
