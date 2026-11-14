// The session drawn as a score: a five-line stave against time. Each category sits on its
// own line or space, every issue is a note head (filled for major, open for minor), long
// stretches carry a tie, bar lines mark time, and the tempo is set above like a marking.
import { useState } from 'react'
import type { Category, Issue } from '../api/client'
import { useI18n } from '../i18n'
import { CATEGORY_ORDER } from '../lib/categories'
import { formatTime } from '../lib/format'
import { issueMessage } from '../lib/issues'
import { tempoMarking } from '../lib/tempo'

const CATEGORY_COLORS: Record<Category, string> = {
  voice: 'text-violet-600 dark:text-violet-400',
  pacing: 'text-sky-600 dark:text-sky-400',
  language: 'text-amber-600 dark:text-amber-400',
  pronunciation: 'text-rose-600 dark:text-rose-400',
  eye_contact: 'text-emerald-600 dark:text-emerald-400',
  posture: 'text-orange-600 dark:text-orange-400',
  body_language: 'text-teal-600 dark:text-teal-400',
}

// Staff positions from the top: lines on even steps, spaces on odd ones.
const STEP = 9 // px between a line and the next space
const TOP = 30 // room for bar numbers and markers
const POSITION: Record<Category, number> = {
  voice: 0,
  pacing: 1,
  language: 2,
  pronunciation: 3,
  eye_contact: 4,
  posture: 5,
  body_language: 6,
}

export interface TimelineMarker {
  id: string
  t: number
  label: string
  kind: 'prompt' | 'note'
}

const MARKER_COLORS: Record<TimelineMarker['kind'], string> = {
  prompt: 'bg-brand-600',
  note: 'bg-white ring-2 ring-slate-800 dark:bg-slate-900 dark:ring-slate-100',
}

interface Props {
  issues: Issue[]
  markers?: TimelineMarker[]
  duration: number
  currentTime: number
  onSeek: (t: number) => void
  wpm?: number | null
}

function barLength(duration: number): number {
  for (const s of [5, 10, 15, 20, 30, 60, 120]) if (duration / s <= 14) return s
  return 300
}

export function VideoTimeline({ issues, markers = [], duration, currentTime, onSeek, wpm }: Props) {
  const [hover, setHover] = useState<Issue | null>(null)
  const [hoverMarker, setHoverMarker] = useState<TimelineMarker | null>(null)
  const { t, tk } = useI18n()
  if (!duration) return null
  const pct = (x: number) => `${Math.min(100, Math.max(0, (x / duration) * 100))}%`
  const present = CATEGORY_ORDER.filter((c) => issues.some((i) => i.category === c))
  const bar = barLength(duration)
  const bars = Array.from({ length: Math.floor(duration / bar) + 1 }, (_, k) => k * bar)
  const y = (c: Category) => TOP + POSITION[c] * STEP
  const height = TOP + 8 * STEP + 10
  const tempo = wpm ? tempoMarking(wpm) : null

  return (
    <div className="card p-4">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-sm font-semibold">{t('timeline.title')}</span>
        <span className="min-h-4 text-xs text-slate-500" aria-live="polite">
          {hover
            ? `${formatTime(hover.start)} · ${issueMessage(hover, tk)}`
            : hoverMarker
              ? `${formatTime(hoverMarker.t)} · ${hoverMarker.label}`
              : t('timeline.hint')}
        </span>
      </div>
      <div dir="ltr">
        {tempo && (
          <p className="text-slate-800 dark:text-slate-100">
            <span className="tempo text-lg">{tempo}</span>
            <span className="ms-2 text-xs text-slate-500 tabular-nums">{Math.round(wpm!)} {t('common.wpm')}</span>
          </p>
        )}
        <div
          className="relative cursor-pointer select-none"
          style={{ height }}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect()
            onSeek(((e.clientX - rect.left) / rect.width) * duration)
          }}
        >
          {/* Bar lines and bar numbers (time). */}
          {bars.map((s) => (
            <div key={s} className="pointer-events-none absolute" style={{ left: pct(s), top: 0, bottom: 0 }}>
              <span className="absolute top-0 -translate-x-1/2 font-mono text-[10px] text-slate-400">{formatTime(s)}</span>
              <span className="absolute w-px bg-slate-300 dark:bg-slate-600" style={{ top: TOP, height: 8 * STEP }} />
            </div>
          ))}
          {/* Final double bar. */}
          <span className="pointer-events-none absolute right-0 w-[3px] border-l border-slate-400 bg-slate-500" style={{ top: TOP, height: 8 * STEP }} />
          {/* The five lines. */}
          {[0, 2, 4, 6, 8].map((k) => (
            <span key={k} className="pointer-events-none absolute inset-x-0 h-px bg-slate-300 dark:bg-slate-600" style={{ top: TOP + k * STEP }} />
          ))}
          {/* Prompt and note pins above the stave. */}
          {markers.map((m) => (
            <button
              key={m.id}
              type="button"
              aria-label={`${formatTime(m.t)} ${m.label}`}
              onMouseEnter={() => setHoverMarker(m)}
              onMouseLeave={() => setHoverMarker(null)}
              onFocus={() => setHoverMarker(m)}
              onClick={(e) => {
                e.stopPropagation()
                onSeek(m.t)
              }}
              className={`absolute top-3.5 h-3 w-3 -translate-x-1/2 ${m.kind === 'prompt' ? 'rotate-45 rounded-[2px]' : 'rounded-[1px]'} ${MARKER_COLORS[m.kind]} transition-transform hover:scale-125`}
              style={{ left: pct(m.t) }}
            />
          ))}
          {/* Ties for long stretches, then note heads. */}
          {issues.map((i) =>
            i.end - i.start >= 1.5 ? (
              <span
                key={`tie-${i.id}`}
                className={`pointer-events-none absolute h-[3px] rounded-full bg-current opacity-35 ${CATEGORY_COLORS[i.category]}`}
                style={{ left: pct(i.start), width: pct(i.end - i.start), top: y(i.category) - 1 }}
              />
            ) : null,
          )}
          {issues.map((i) => (
            <button
              key={i.id}
              type="button"
              aria-label={`${formatTime(i.start)} ${issueMessage(i, tk)}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              onClick={(e) => {
                e.stopPropagation()
                onSeek(Math.max(0, i.start - 1))
              }}
              className={`absolute -translate-x-1/2 -translate-y-1/2 transition-transform hover:scale-150 ${CATEGORY_COLORS[i.category]}`}
              style={{ left: pct(i.start), top: y(i.category) }}
            >
              <svg width="12" height="10" viewBox="0 0 12 10" aria-hidden="true">
                <ellipse
                  cx="6"
                  cy="5"
                  rx={i.severity === 'info' ? 2.4 : 4.4}
                  ry={i.severity === 'info' ? 2.4 : 3.1}
                  transform="rotate(-22 6 5)"
                  fill={i.severity === 'minor' ? 'none' : 'currentColor'}
                  stroke="currentColor"
                  strokeWidth="1.6"
                />
              </svg>
            </button>
          ))}
          {/* Playhead. */}
          <span className="pointer-events-none absolute bottom-0 w-0.5 rounded-full bg-brand-600" style={{ left: pct(currentTime), top: TOP - 6 }} />
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        {present.map((c) => (
          <span key={c} className="flex items-center gap-1.5">
            <svg width="10" height="8" viewBox="0 0 12 10" className={CATEGORY_COLORS[c]} aria-hidden="true">
              <ellipse cx="6" cy="5" rx="4.4" ry="3.1" transform="rotate(-22 6 5)" fill="currentColor" />
            </svg>
            {t(`cat.${c}`)}
          </span>
        ))}
        {present.length > 0 && <span className="text-slate-400">{t('timeline.legend_heads')}</span>}
      </div>
    </div>
  )
}
