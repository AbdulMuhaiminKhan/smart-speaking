// Detailed voice delivery and body language numbers for one session, with a verdict per metric.
import type { BodyResult, PacingResult, VoiceResult } from '../api/client'
import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n/core'
import { grade, type Verdict } from '../lib/grade'
import { LineChart } from './charts'


const DOT: Record<Verdict, string> = {
  good: 'bg-emerald-500',
  ok: 'bg-amber-400',
  work: 'bg-red-500',
  none: 'bg-slate-300 dark:bg-slate-600',
}

interface Row {
  label: MessageKey
  value: string | null
  verdict: Verdict
  hint?: MessageKey
}

const pct = (x: number | null | undefined) => (x === null || x === undefined ? null : `${Math.round(x * 100)}%`)
const num = (x: number | null | undefined, d = 1, unit = '') => (x === null || x === undefined ? null : `${x.toFixed(d)}${unit}`)

function Metrics({ rows }: { rows: Row[] }) {
  const { t } = useI18n()
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {rows
        .filter((r) => r.value !== null)
        .map((r) => (
          <div key={r.label} className="flex items-start gap-3">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${DOT[r.verdict]}`} title={t(`verdict.${r.verdict}`)} />
            <div className="min-w-0 flex-1">
              <dt className="text-sm text-slate-500">{t(r.label)}</dt>
              <dd className="font-semibold tabular-nums">{r.value}</dd>
              {r.hint && <p className="text-xs text-slate-500">{t(r.hint)}</p>}
            </div>
          </div>
        ))}
    </dl>
  )
}

const card = 'rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900'

export function VoiceDeliveryCard({ voice, pacing, onSeek }: { voice: VoiceResult | null; pacing: PacingResult | null; onSeek: (t: number) => void }) {
  const { t } = useI18n()
  if (!voice && !pacing) return null
  const rows: Row[] = []
  if (voice) {
    rows.push(
      {
        label: 'delivery.pitch_variation',
        value: num(voice.pitch_std_semitones, 1, ' st'),
        verdict: grade(voice.pitch_std_semitones, [2.5, 8], [2, 10]),
        hint: voice.monotone ? 'delivery.monotone_yes' : 'delivery.pitch_variation_hint',
      },
      {
        label: 'delivery.pitch_range',
        value: num(voice.pitch_range_semitones, 1, ' st'),
        verdict: grade(voice.pitch_range_semitones, [6, 20], [4, 24]),
      },
      { label: 'delivery.pitch_median', value: num(voice.pitch_median_hz, 0, ' Hz'), verdict: 'none' },
      {
        label: 'delivery.volume_variation',
        value: num(voice.intensity_std_db, 1, ' dB'),
        verdict: grade(voice.intensity_std_db, [3, 9], [2, 12]),
        hint: 'delivery.volume_variation_hint',
      },
      {
        label: 'delivery.quiet',
        value: pct(voice.quiet_ratio),
        verdict: grade(voice.quiet_ratio, [0, 0.1], [0, 0.2]),
      },
      {
        label: 'delivery.energy_trend',
        value: voice.energy_trend_db_per_min === null ? null : `${voice.energy_trend_db_per_min > 0 ? '+' : ''}${voice.energy_trend_db_per_min.toFixed(1)} dB/min`,
        verdict: grade(voice.energy_trend_db_per_min, [-1, 10], [-2, 10]),
        hint: 'delivery.energy_trend_hint',
      },
    )
  }
  if (pacing) {
    rows.push(
      {
        label: 'delivery.pauses',
        value: t('delivery.pauses_value', { n: pacing.pause_count, good: pacing.effective_pause_count, long: pacing.awkward_pause_count }),
        verdict: pacing.awkward_pause_count > 3 ? 'work' : pacing.awkward_pause_count > 0 ? 'ok' : 'good',
      },
      {
        label: 'delivery.pause_share',
        value: pct(pacing.pause_ratio),
        verdict: grade(pacing.pause_ratio, [0.1, 0.3], [0.05, 0.4]),
        hint: 'delivery.pause_share_hint',
      },
      { label: 'delivery.longest_pause', value: num(pacing.longest_pause_s, 1, ' s'), verdict: grade(pacing.longest_pause_s, [0, 2.5], [0, 4]) },
      {
        label: 'delivery.articulation',
        value: `${Math.round(pacing.wpm_articulation)} ${t('common.wpm')}`,
        verdict: grade(pacing.wpm_articulation, [130, 190], [110, 210]),
        hint: 'delivery.articulation_hint',
      },
    )
  }
  const variation = voice?.pitch_variation_series ?? []
  return (
    <section className={card}>
      <h3 className="font-semibold">{t('delivery.voice_title')}</h3>
      <p className="mb-4 text-xs text-slate-500">{t('delivery.voice_note')}</p>
      <Metrics rows={rows} />
      {variation.filter((p) => p.value !== null).length > 1 && (
        <div className="mt-5">
          <LineChart
            title={t('delivery.variation_chart')}
            points={variation}
            unit={t('delivery.variation_unit')}
            band={[2.5, 8]}
            bandLabel={t('delivery.variation_band')}
            yMin={0}
            format={(v) => v.toFixed(1)}
            onSeek={onSeek}
          />
        </div>
      )}
    </section>
  )
}

export function BodyLanguageCard({ body }: { body: BodyResult | null }) {
  const { t } = useI18n()
  if (!body || body.face_detected_ratio + body.pose_detected_ratio === 0) return null
  const rows: Row[] = [
    {
      label: 'delivery.eye_contact',
      value: pct(body.eye_contact_ratio),
      verdict: grade(body.eye_contact_ratio, [0.75, 1], [0.6, 1]),
    },
    {
      label: 'delivery.gestures',
      value: num(body.gestures_per_min, 1, ` / min`),
      verdict: grade(body.gestures_per_min, [4, 30], [2, 40]),
      hint: 'delivery.gestures_hint',
    },
    {
      label: 'delivery.open_palms',
      value: pct(body.open_gesture_ratio),
      verdict: grade(body.open_gesture_ratio, [0.4, 1], [0.2, 1]),
    },
    {
      label: 'delivery.hands_visible',
      value: pct(body.hands_visible_ratio),
      verdict: grade(body.hands_visible_ratio, [0.5, 1], [0.25, 1]),
    },
    { label: 'delivery.slouch', value: pct(body.slouch_ratio), verdict: grade(body.slouch_ratio, [0, 0.1], [0, 0.25]) },
    { label: 'delivery.head_down', value: pct(body.head_down_ratio), verdict: grade(body.head_down_ratio, [0, 0.1], [0, 0.25]) },
    { label: 'delivery.sway', value: pct(body.sway_ratio), verdict: grade(body.sway_ratio, [0, 0.1], [0, 0.25]) },
    { label: 'delivery.fidget', value: pct(body.fidget_ratio), verdict: grade(body.fidget_ratio, [0, 0.1], [0, 0.25]) },
    { label: 'delivery.arms_crossed', value: pct(body.arms_crossed_ratio), verdict: grade(body.arms_crossed_ratio, [0, 0.05], [0, 0.15]) },
    {
      label: 'delivery.face_touch',
      value: String(body.face_touch_count),
      verdict: body.face_touch_count === 0 ? 'good' : body.face_touch_count <= 2 ? 'ok' : 'work',
    },
    { label: 'delivery.smile', value: pct(body.smile_ratio), verdict: 'none' },
  ]
  return (
    <section className={card}>
      <h3 className="font-semibold">{t('delivery.body_title')}</h3>
      <p className="mb-4 text-xs text-slate-500">{t('delivery.body_note')}</p>
      <Metrics rows={rows} />
    </section>
  )
}
