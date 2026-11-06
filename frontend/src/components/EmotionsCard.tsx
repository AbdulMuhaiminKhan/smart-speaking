import type { BodyResult, EmotionPoint, VoiceEmotionResult } from '../api/client'
import { formatTime } from '../lib/format'

const LABELS: Record<string, string> = {
  neutral: 'Neutral',
  happy: 'Happy',
  surprised: 'Surprised',
  sad: 'Sad',
  angry: 'Angry',
  fearful: 'Worried',
  disgusted: 'Displeased',
}

const COLORS: Record<string, string> = {
  neutral: 'bg-slate-400',
  happy: 'bg-emerald-500',
  surprised: 'bg-sky-500',
  sad: 'bg-indigo-500',
  angry: 'bg-red-500',
  fearful: 'bg-amber-500',
  disgusted: 'bg-lime-600',
}

function Mix({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values)
    .filter(([, v]) => v > 0.005)
    .sort((a, b) => b[1] - a[1])
  if (!entries.length) return null
  return (
    <div>
      <p className="mb-1 text-sm font-medium">{title}</p>
      <div className="flex h-3 overflow-hidden rounded-full">
        {entries.map(([k, v]) => (
          <div key={k} className={COLORS[k] ?? 'bg-slate-300'} style={{ width: `${v * 100}%` }} title={`${LABELS[k] ?? k} ${Math.round(v * 100)}%`} />
        ))}
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {entries.slice(0, 4).map(([k, v]) => `${LABELS[k] ?? k} ${Math.round(v * 100)}%`).join(' · ')}
      </p>
    </div>
  )
}

function Strip({ title, points, duration, onSeek }: { title: string; points: EmotionPoint[]; duration: number; onSeek: (t: number) => void }) {
  if (!points.length || !duration) return null
  return (
    <div>
      <p className="mb-1 text-xs text-slate-500">{title} over time</p>
      <div className="relative h-4 rounded bg-slate-100 dark:bg-slate-800">
        {points.map((p) => {
          const left = Math.max(0, (p.t - 2.5) / duration) * 100
          return (
            <button
              key={p.t}
              type="button"
              title={`${formatTime(p.t)} · ${LABELS[p.emotion] ?? p.emotion}`}
              onClick={() => onSeek(Math.max(0, p.t - 2))}
              className={`absolute top-0 h-4 ${COLORS[p.emotion] ?? 'bg-slate-300'} opacity-80 hover:opacity-100`}
              style={{ left: `${left}%`, width: `${Math.min(100 - left, (5 / duration) * 100)}%` }}
            />
          )
        })}
      </div>
    </div>
  )
}

interface Props {
  body: BodyResult | null
  voiceEmotion: VoiceEmotionResult | null
  duration: number
  onSeek: (t: number) => void
}

export function EmotionsCard({ body, voiceEmotion, duration, onSeek }: Props) {
  const hasFace = body && Object.keys(body.emotions ?? {}).length > 0
  const hasVoice = voiceEmotion && Object.keys(voiceEmotion.emotions).length > 0
  if (!hasFace && !hasVoice) return null
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="font-semibold">Emotions</h3>
      <p className="mb-4 text-xs text-slate-500">
        Estimates. The face reading comes from your facial movements, the voice reading from a small speech emotion model.
        Both read strong, acted emotion better than everyday speech.
      </p>
      <div className="grid gap-5 md:grid-cols-2">
        {hasFace && (
          <div className="space-y-3">
            <Mix title="Face" values={body.emotions} />
            <Strip title="Face" points={body.emotion_timeline ?? []} duration={duration} onSeek={onSeek} />
          </div>
        )}
        {hasVoice && (
          <div className="space-y-3">
            <Mix title="Voice" values={voiceEmotion.emotions} />
            <Strip title="Voice" points={voiceEmotion.timeline} duration={duration} onSeek={onSeek} />
          </div>
        )}
      </div>
    </div>
  )
}
