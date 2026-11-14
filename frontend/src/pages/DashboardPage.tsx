import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi, type Achievements, type Category, type Goals, type Progress, type SessionScores } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { GoalsPanel } from '../components/GoalsPanel'
import { TrendChart } from '../components/TrendChart'
import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n/core'
import { CATEGORY_ORDER, scoreColor } from '../lib/categories'
import { errorText } from '../lib/errors'
import { recentChange } from '../lib/trends'

const card = 'card'

type Metric = 'score' | 'fillers' | 'wpm' | 'clarity'

interface MetricDef {
  label: MessageKey
  unit: MessageKey
  value: (s: SessionScores, category: Category | 'overall') => number | null
  band?: [number, number]
  yMin?: number
  yMax?: number
  digits: number
  lowerIsBetter?: boolean
}

const METRICS: Record<Metric, MetricDef> = {
  score: {
    label: 'trend.score',
    unit: 'trend.score_unit',
    value: (s, c) => (c === 'overall' ? s.overall : (s.categories[c] ?? null)),
    band: [80, 100],
    yMin: 0,
    yMax: 100,
    digits: 0,
  },
  fillers: {
    label: 'trend.fillers',
    unit: 'trend.fillers_unit',
    value: (s) => s.metrics?.fillers_per_min ?? null,
    band: [0, 3],
    yMin: 0,
    digits: 1,
    lowerIsBetter: true,
  },
  wpm: {
    label: 'trend.wpm',
    unit: 'trend.wpm_unit',
    value: (s) => s.metrics?.wpm ?? null,
    band: [120, 160],
    digits: 0,
  },
  clarity: {
    label: 'trend.clarity',
    unit: 'trend.clarity_unit',
    value: (s) => s.metrics?.clarity_pct ?? null,
    band: [90, 100],
    yMax: 100,
    digits: 0,
  },
}

function Trends({ progress, goals }: { progress: Progress; goals?: Goals }) {
  const { t } = useI18n()
  const [metric, setMetric] = useState<Metric>('score')
  const [category, setCategory] = useState<Category | 'overall'>('overall')
  const base = METRICS[metric]
  // Your own goals set the green band where you have them.
  const band: [number, number] | undefined =
    metric === 'wpm' && goals?.wpm_low && goals.wpm_high
      ? [goals.wpm_low, goals.wpm_high]
      : metric === 'fillers' && goals?.max_fillers_per_min != null
        ? [0, goals.max_fillers_per_min]
        : metric === 'score' && goals?.min_score
          ? [goals.min_score, 100]
          : base.band
  const def = { ...base, band }
  const values = progress.sessions.map((s) => def.value(s, category))
  const fmt = (v: number) => v.toFixed(def.digits)
  const change = recentChange(values)

  let direction: 'better' | 'worse' | 'same' = 'same'
  if (change) {
    const delta = change.recent - change.before
    const inBand = (v: number) => !def.band || (v >= def.band[0] && v <= def.band[1])
    if (metric === 'wpm') {
      // For pace, closer to the comfortable range is better.
      const dist = (v: number) => (inBand(v) ? 0 : Math.min(Math.abs(v - def.band![0]), Math.abs(v - def.band![1])))
      const d = dist(change.recent) - dist(change.before)
      direction = Math.abs(d) < 3 ? 'same' : d < 0 ? 'better' : 'worse'
    } else {
      const threshold = metric === 'fillers' ? 0.3 : 2
      direction = Math.abs(delta) < threshold ? 'same' : (delta < 0) === !!def.lowerIsBetter ? 'better' : 'worse'
    }
  }

  return (
    <div className={card}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">{t('dash.trends')}</h2>
        <div className="flex flex-wrap items-center gap-1" role="tablist">
          {(Object.keys(METRICS) as Metric[]).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={metric === m}
              onClick={() => setMetric(m)}
              className={`rounded-md px-3 py-1 text-sm ${
                metric === m ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              {t(METRICS[m].label)}
            </button>
          ))}
          {metric === 'score' && (
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as Category | 'overall')}
              className="ms-1 rounded-md border border-slate-300 bg-transparent px-2 py-1 text-sm dark:border-slate-700"
              aria-label={t('dash.score_to_show')}
            >
              <option value="overall">{t('dash.overall')}</option>
              {CATEGORY_ORDER.map((c) => (
                <option key={c} value={c}>
                  {t(`cat.${c}`)}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
      <TrendChart
        points={progress.sessions.map((s, i) => ({ id: s.id, title: s.title, date: s.created_at, value: values[i] }))}
        label={t(def.unit)}
        band={def.band}
        yMin={def.yMin}
        yMax={def.yMax}
        format={fmt}
      />
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-2 text-xs text-slate-500">
        <span>
          {t(def.unit)} · {t('trend.target_band')}
          {metric === 'clarity' && ` · ${t('trend.clarity_note')}`}
        </span>
        {change && (
          <span
            className={
              direction === 'better' ? 'text-emerald-600' : direction === 'worse' ? 'text-red-600' : 'text-slate-500'
            }
          >
            {t('trend.recent', { recent: fmt(change.recent), before: fmt(change.before) })} · {t(`trend.${direction}`)}
          </span>
        )}
      </div>
    </div>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const [progress, setProgress] = useState<Progress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { t } = useI18n()
  const [ach, setAch] = useState<Achievements | null>(null)

  useEffect(() => {
    authApi.achievements().then(setAch).catch(() => setAch(null))
    authApi
      .progress()
      .then(setProgress)
      .catch((e: unknown) => setError(errorText(e, t, 'err.load_progress')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const change = progress?.change ?? null
  const latestCats = progress?.sessions.at(-1)?.categories ?? {}

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{user?.name ? t('dash.welcome_name', { name: user.name }) : t('dash.welcome')}</h1>
          {progress && progress.count > 0 ? (
            <p className="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600 dark:text-slate-400">
              <span>
                {t('dash.sessions')} <strong className="text-slate-900 tabular-nums dark:text-white">{progress.count}</strong>
              </span>
              <span>
                {t('dash.latest')}{' '}
                <bdi className={`font-bold tabular-nums ${scoreColor(progress.latest)}`}>
                  {progress.latest !== null ? Math.round(progress.latest) : '–'}
                </bdi>
                {change !== null && (
                  <>
                    {' '}
                    <bdi dir="ltr" className={`text-xs ${change >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      ({change >= 0 ? '+' : ''}
                      {change})
                    </bdi>
                  </>
                )}
              </span>
              <span>
                {t('dash.best')} <strong className="text-slate-900 tabular-nums dark:text-white">{progress.best !== null ? Math.round(progress.best) : '–'}</strong>
              </span>
              <span>
                {t('dash.average')} <strong className="text-slate-900 tabular-nums dark:text-white">{progress.average !== null ? Math.round(progress.average) : '–'}</strong>
              </span>
            </p>
          ) : (
            <p className="text-slate-600 dark:text-slate-400">{t('dash.subtitle')}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Link to="/live" className="btn-primary">
            {t('dash.practice_live')}
          </Link>
          <Link to="/upload" className="btn-quiet">
            {t('dash.upload_video')}
          </Link>
        </div>
      </div>

      {error && <p className="text-red-700 dark:text-red-300">{error}</p>}
      {!progress && !error && <p className="text-slate-500">{t('common.loading')}</p>}

      {progress && progress.count === 0 && (
        <div className={`${card} text-center`}>
          <p className="font-medium">{t('dash.empty_title')}</p>
          <p className="mt-1 text-sm text-slate-500">{t('dash.empty_body')}</p>
        </div>
      )}

      {progress && progress.count > 0 && (
        <>
          {ach && <GoalsPanel data={ach} part="goals" />}

          <Trends progress={progress} goals={user?.settings.goals} />

          <div className="grid gap-6 xl:grid-cols-[3fr_2fr]">
          <div className={card}>
            <h2 className="mb-3 font-semibold">{t('dash.by_category')}</h2>
            <div className="grid grid-cols-2 gap-x-3 gap-y-4 sm:grid-cols-4">
              {CATEGORY_ORDER.map((c) => {
                const v = latestCats[c] ?? null
                const delta = progress.category_change[c]
                return (
                  <div key={c}>
                    <p className="text-xs text-slate-500">{t(`cat.${c}`)}</p>
                    <p className={`text-2xl font-semibold tabular-nums ${scoreColor(v)}`}>{v !== null ? Math.round(v) : '–'}</p>
                    {delta !== null && delta !== undefined && (
                      <p className={`text-xs ${delta >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {delta >= 0 ? '▲' : '▼'} {t('dash.vs_average', { delta: Math.abs(delta).toFixed(0) })}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className={card}>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-semibold">{t('dash.recent')}</h2>
              <Link to="/sessions" className="text-sm text-brand-600">
                {t('dash.see_all')}
              </Link>
            </div>
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {[...progress.sessions]
                .reverse()
                .slice(0, 5)
                .map((s) => (
                  <li key={s.id}>
                    <Link to={`/sessions/${s.id}`} className="flex items-center justify-between gap-3 py-2 hover:text-brand-600">
                      <span className="flex-1">{s.title}</span>
                      {s.metrics?.wpm != null && (
                        <span className="hidden text-xs text-slate-500 sm:inline">
                          {Math.round(s.metrics.wpm)} {t('common.wpm')} · {t('trend.fillers_short', { n: (s.metrics.fillers_per_min ?? 0).toFixed(1) })}
                        </span>
                      )}
                      <span className={`font-semibold tabular-nums ${scoreColor(s.overall)}`}>
                        {s.overall !== null ? Math.round(s.overall) : '–'}
                      </span>
                    </Link>
                  </li>
                ))}
            </ul>
          </div>
          </div>

          {ach && <GoalsPanel data={ach} part="achievements" />}
        </>
      )}
    </div>
  )
}
