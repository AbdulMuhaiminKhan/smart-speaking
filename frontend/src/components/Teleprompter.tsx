// Large scrolling script. Follows your voice when the live transcript is available,
// otherwise scrolls at a steady words-per-minute rate.
import { useEffect, useMemo, useRef } from 'react'
import { useI18n } from '../i18n'
import { tokenize } from '../live/scriptFollow'

interface Props {
  script: string
  position: number // index of the next word to say
  skipped: [number, number][] // word ranges you jumped over
  mirror: boolean
  fontSize: number
}

export function Teleprompter({ script, position, skipped, mirror, fontSize }: Props) {
  const { t } = useI18n()
  const words = useMemo(() => tokenize(script), [script])
  const box = useRef<HTMLDivElement>(null)
  const current = useRef<HTMLSpanElement>(null)
  const isSkipped = (i: number) => skipped.some(([a, b]) => i >= a && i < b)

  useEffect(() => {
    const el = current.current
    const c = box.current
    if (!el || !c) return
    // Keep the current word about a third of the way down.
    const top = el.offsetTop - c.clientHeight / 3
    c.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
  }, [position])

  return (
    <div className="relative">
      <div
        ref={box}
        dir="auto"
        aria-label={t('script.teleprompter')}
        className={`h-64 overflow-y-auto rounded-xl bg-slate-950 px-6 py-8 leading-relaxed text-slate-100 ${mirror ? '-scale-x-100' : ''}`}
        style={{ fontSize }}
      >
        <p>
          {words.map((w, i) => (
            <span
              key={i}
              ref={i === Math.min(position, words.length - 1) ? current : undefined}
              className={
                isSkipped(i)
                  ? 'text-red-400 line-through decoration-2'
                  : i < position
                    ? 'text-slate-500'
                    : i === position
                      ? 'rounded bg-brand-600 px-1 text-white'
                      : ''
              }
            >
              {w.text}{' '}
            </span>
          ))}
        </p>
      </div>
      <div className="pointer-events-none absolute inset-x-0 top-1/3 h-px bg-brand-500/40" />
    </div>
  )
}
