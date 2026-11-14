// Streak calendar, weekly goal ring, personal targets and achievement badges.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Achievement, Achievements, GoalStatus } from '../api/client'
import { useI18n } from '../i18n'
import { Icon, type IconName } from './Icon'

const card = 'card'

const BADGE_ICON: Record<string, IconName> = {
  first_session: 'mic',
  five_sessions: 'star',
  twenty_sessions: 'trophy',
  streak_3: 'flame',
  streak_7: 'flame',
  score_80: 'target',
  score_90: 'sparkle',
  low_fillers: 'clear',
  steady_pace: 'gauge',
  clear_speaker: 'check',
  eye_contact_pro: 'eye',
  script_master: 'scroll',
  explorer: 'compass',
  polyglot: 'globe',
  improver: 'chart',
}

/** The week as one measure: a beat per planned session, a note head for each one done. */
function Measure({ value, goal }: { value: number; goal: number }) {
  const beats = Math.max(goal, value, 1)
  const met = goal > 0 && value >= goal
  const w = 36 + beats * 26
  return (
    <svg viewBox={`0 0 ${w} 48`} className="h-12 max-w-full" style={{ width: w }} aria-hidden="true">
      {[8, 16, 24, 32, 40].map((y) => (
        <line key={y} x1="2" x2={w - 2} y1={y} y2={y} className="stroke-slate-300 dark:stroke-slate-600" strokeWidth="1" />
      ))}
      <line x1="2" x2="2" y1="8" y2="40" className="stroke-slate-400" strokeWidth="1" />
      <line x1={w - 5} x2={w - 5} y1="8" y2="40" className="stroke-slate-400" strokeWidth="1" />
      <line x1={w - 2} x2={w - 2} y1="8" y2="40" className="stroke-slate-500" strokeWidth="2.5" />
      {Array.from({ length: beats }, (_, k) => {
        const done = k < value
        const x = 24 + k * 26
        return (
          <ellipse
            key={k}
            cx={x}
            cy="24"
            rx="6.5"
            ry="4.6"
            transform={`rotate(-22 ${x} 24)`}
            strokeWidth="1.8"
            className={
              done
                ? met
                  ? 'fill-brass-400 stroke-brass-500'
                  : 'fill-slate-800 stroke-slate-800 dark:fill-slate-100 dark:stroke-slate-100'
                : 'fill-none stroke-slate-400'
            }
          />
        )
      })}
    </svg>
  )
}

function StreakDays({ days }: { days: string[] }) {
  const { formatDate } = useI18n()
  const set = new Set(days)
  const [today] = useState(() => new Date())
  const cells = Array.from({ length: 28 }, (_, k) => {
    const d = new Date(today)
    d.setDate(today.getDate() - (27 - k))
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return { key, on: set.has(key), label: formatDate(d, false) }
  })
  return (
    <div dir="ltr" className="grid grid-cols-14 gap-1" style={{ gridTemplateColumns: 'repeat(14, minmax(0, 1fr))' }}>
      {cells.map((c) => (
        <span
          key={c.key}
          title={c.label}
          className={`aspect-square rounded-[3px] ${c.on ? 'bg-brass-400' : 'bg-slate-100 dark:bg-slate-800'}`}
        />
      ))}
    </div>
  )
}

function goalText(g: GoalStatus, t: ReturnType<typeof useI18n>['t']): { label: string; value: string } {
  const cur = g.current === null ? '–' : g.id === 'fillers' ? g.current.toFixed(1) : String(Math.round(g.current))
  // Isolate the number so a range like 120-160 keeps its order inside Urdu text.
  return { label: t(`goal.${g.id}`, { target: `\u2066${g.target}\u2069` }), value: cur }
}

function Badge({ a }: { a: Achievement }) {
  const { tk, formatDate } = useI18n()
  const body = (
    <div
      className={`flex h-full items-center gap-3 rounded-lg border p-2.5 text-start transition ${
        a.earned
          ? 'border-brass-300 bg-brass-300/15 dark:border-brass-500/50 dark:bg-brass-500/10'
          : 'border-slate-200 opacity-70 dark:border-slate-800'
      }`}
      title={tk(`ach.${a.id}_desc`, '')}
    >
      <span
        className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
          a.earned ? 'bg-brass-400 text-slate-950' : 'bg-slate-100 text-slate-400 dark:bg-slate-800'
        }`}
      >
        <Icon name={a.earned ? (BADGE_ICON[a.id] ?? 'star') : 'lock'} size={18} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-sm font-medium leading-tight">{tk(`ach.${a.id}`, a.id)}</span>
        {a.earned ? (
          a.earned_at && <span className="text-[11px] text-slate-500">{formatDate(a.earned_at, false)}</span>
        ) : (
          <span dir="ltr" className="block h-1 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <span className="block h-full bg-brand-500" style={{ width: `${Math.round(a.progress * 100)}%` }} />
          </span>
        )}
      </span>
    </div>
  )
  return a.session_id ? <Link to={`/sessions/${a.session_id}`}>{body}</Link> : body
}

export function GoalsPanel({ data, part }: { data: Achievements; part: 'goals' | 'achievements' }) {
  const { t } = useI18n()
  const weekly = data.goals.find((g) => g.id === 'sessions_per_week')
  const others = data.goals.filter((g) => g.id !== 'sessions_per_week')
  const earned = data.achievements.filter((a) => a.earned).length
  if (part === 'achievements') return <AchievementsCard data={data} earned={earned} />
  return (
      <div className="grid gap-4 md:grid-cols-3">
        <div className={card}>
          <p className="flex items-baseline gap-2">
            <span className="tempo text-4xl tabular-nums">{data.streak.current}</span>
            <span className="text-sm text-slate-500">{t('goal.streak_days')}</span>
          </p>
          <div className="mt-4">
            <StreakDays days={data.streak.days} />
          </div>
          <p className="mt-2 text-xs text-slate-500">{t('goal.best_streak', { n: data.streak.best })}</p>
        </div>

        <div className={card}>
          <div className="flex items-baseline justify-between gap-2">
            <p className="font-medium">{t('goal.this_week')}</p>
            <bdi dir="ltr" className="text-sm font-semibold tabular-nums">
              {data.week_sessions}
              {weekly && <span className="font-normal text-slate-400"> / {weekly.target}</span>}
            </bdi>
          </div>
          <div dir="ltr" className="my-2">
            <Measure value={data.week_sessions} goal={weekly ? Number(weekly.target) : 0} />
          </div>
          <div>
            <p className="text-sm text-slate-500">
              {weekly ? (weekly.met ? t('goal.week_done') : t('goal.week_left', { n: Number(weekly.target) - data.week_sessions })) : t('goal.no_weekly')}
            </p>
          </div>
        </div>

        <div className={card}>
          <div className="mb-2 flex items-center justify-between">
            <p className="font-medium">{t('goal.targets')}</p>
            <Link to="/settings#goals" className="text-xs text-brand-600">
              {t('goal.edit')}
            </Link>
          </div>
          {others.length === 0 ? (
            <p className="text-sm text-slate-500">{t('goal.none')}</p>
          ) : (
            <ul className="space-y-2">
              {others.map((g) => {
                const { label, value } = goalText(g, t)
                return (
                  <li key={g.id} className="flex items-center gap-2 text-sm">
                    <span
                      className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${g.met ? 'bg-emerald-600 text-white' : g.current === null ? 'border border-slate-300 text-slate-400' : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'}`}
                      title={t(g.met ? 'goal.met' : 'goal.not_met')}
                    >
                      <Icon name={g.met ? 'check' : 'cross'} size={12} />
                    </span>
                    <span className="flex-1">{label}</span>
                    <span className={`font-semibold tabular-nums ${g.met || g.current === null ? '' : 'text-red-700 dark:text-red-300'}`}>{value}</span>
                    <span className="sr-only">{t(g.met ? 'goal.met' : 'goal.not_met')}</span>
                  </li>
                )
              })}
            </ul>
          )}
          <p className="mt-2 text-xs text-slate-500">{t('goal.latest_note')}</p>
        </div>
      </div>
  )
}

function AchievementsCard({ data, earned }: { data: Achievements; earned: number }) {
  const { t } = useI18n()
  return (
      <div className={card}>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="font-semibold">{t('ach.title')}</h2>
          <span className="text-sm text-slate-500">{t('ach.count', { n: earned, total: data.achievements.length })}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {data.achievements.map((a) => (
            <Badge key={a.id} a={a} />
          ))}
        </div>
      </div>
  )
}
