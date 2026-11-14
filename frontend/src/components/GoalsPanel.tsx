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

function Ring({ value, goal }: { value: number; goal: number }) {
  const r = 34
  const c = 2 * Math.PI * r
  const frac = Math.min(1, goal ? value / goal : 0)
  return (
    <svg viewBox="0 0 80 80" className="h-20 w-20 -rotate-90" aria-hidden="true">
      <circle cx="40" cy="40" r={r} strokeWidth="8" fill="none" className="stroke-slate-100 dark:stroke-slate-800" />
      <circle
        cx="40"
        cy="40"
        r={r}
        strokeWidth="8"
        fill="none"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - frac)}
        className={`${frac >= 1 ? 'stroke-emerald-500' : 'stroke-brand-600'} transition-[stroke-dashoffset] duration-700`}
      />
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
          className={`aspect-square rounded-[3px] ${c.on ? 'bg-orange-500' : 'bg-slate-100 dark:bg-slate-800'}`}
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
          ? 'border-amber-300 bg-amber-50 dark:border-amber-700/60 dark:bg-amber-950/30'
          : 'border-slate-200 opacity-70 dark:border-slate-800'
      }`}
      title={tk(`ach.${a.id}_desc`, '')}
    >
      <span
        className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${
          a.earned ? 'bg-amber-400 text-amber-950' : 'bg-slate-100 text-slate-400 dark:bg-slate-800'
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
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-full bg-orange-100 text-orange-600 dark:bg-orange-950/50">
              <Icon name="flame" size={24} />
            </span>
            <div>
              <p className="text-3xl font-semibold tabular-nums">{data.streak.current}</p>
              <p className="text-sm text-slate-500">{t('goal.streak_days')}</p>
            </div>
          </div>
          <div className="mt-4">
            <StreakDays days={data.streak.days} />
          </div>
          <p className="mt-2 text-xs text-slate-500">{t('goal.best_streak', { n: data.streak.best })}</p>
        </div>

        <div className={`${card} flex items-center gap-4`}>
          <div className="relative">
            <Ring value={data.week_sessions} goal={weekly ? Number(weekly.target) : 0} />
            <span dir="ltr" className="absolute inset-0 grid place-items-center text-lg font-semibold tabular-nums">
              {data.week_sessions}
              {weekly && <span className="text-xs text-slate-400">/{weekly.target}</span>}
            </span>
          </div>
          <div>
            <p className="font-medium">{t('goal.this_week')}</p>
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
                    <span className={`grid h-5 w-5 place-items-center rounded-full ${g.met ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-400 dark:bg-slate-800'}`}>
                      <Icon name="check" size={13} />
                    </span>
                    <span className="flex-1">{label}</span>
                    <span className="font-semibold tabular-nums">{value}</span>
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
