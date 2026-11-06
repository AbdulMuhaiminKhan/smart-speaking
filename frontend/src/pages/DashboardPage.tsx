import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, authApi, type Category, type Progress } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { CATEGORY_LABELS, CATEGORY_ORDER, scoreColor } from '../lib/categories'

const card = 'rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900'

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className={card}>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-sm text-slate-500">{hint}</p>}
    </div>
  )
}

function ProgressChart({ progress, category }: { progress: Progress; category: Category | 'overall' }) {
  const pts = progress.sessions
    .map((s, i) => ({ i, s, v: category === 'overall' ? s.overall : (s.categories[category] ?? null) }))
    .filter((p): p is typeof p & { v: number } => p.v !== null && p.v !== undefined)
  if (pts.length < 2) {
    return <p className="py-10 text-center text-sm text-slate-500">Analyze at least two recordings to see your progress here.</p>
  }
  const W = 640
  const H = 200
  const L = 36
  const R = 16
  const T = 12
  const B = 28
  const n = progress.sessions.length
  const x = (i: number) => L + (i / Math.max(1, n - 1)) * (W - L - R)
  const y = (v: number) => T + (1 - v / 100) * (H - T - B)
  const d = pts.map((p, k) => `${k ? 'L' : 'M'}${x(p.i).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Score per session">
      {[0, 50, 80, 100].map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="stroke-slate-200 dark:stroke-slate-800" strokeDasharray={v === 80 ? '4 4' : undefined} />
          <text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize={11} className="fill-slate-400">{v}</text>
        </g>
      ))}
      <path d={d} fill="none" strokeWidth={2.5} className="stroke-brand-600" />
      {pts.map((p) => (
        <Link key={p.s.id} to={`/sessions/${p.s.id}`}>
          <circle cx={x(p.i)} cy={y(p.v)} r={5} className="fill-white stroke-brand-600 dark:fill-slate-900" strokeWidth={2}>
            <title>{`${p.s.title}: ${Math.round(p.v)}`}</title>
          </circle>
        </Link>
      ))}
      <text x={L} y={H - 8} fontSize={11} className="fill-slate-400">{new Date(progress.sessions[0].created_at).toLocaleDateString()}</text>
      <text x={W - R} y={H - 8} fontSize={11} textAnchor="end" className="fill-slate-400">{new Date(progress.sessions[n - 1].created_at).toLocaleDateString()}</text>
    </svg>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const [progress, setProgress] = useState<Progress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [category, setCategory] = useState<Category | 'overall'>('overall')

  useEffect(() => {
    authApi.progress().then(setProgress).catch((e: unknown) => setError(e instanceof ApiError ? e.message : 'Could not load your progress.'))
  }, [])

  const change = progress?.change ?? null
  const latestCats = progress?.sessions.at(-1)?.categories ?? {}

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Welcome back{user?.name ? `, ${user.name}` : ''}</h1>
          <p className="text-slate-600 dark:text-slate-400">Practice, get feedback, and watch your scores climb.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/live" className="rounded-md bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700">Practice live</Link>
          <Link to="/upload" className="rounded-md border border-slate-300 px-4 py-2 font-medium dark:border-slate-700">Upload a video</Link>
        </div>
      </div>

      {error && <p className="text-red-700 dark:text-red-300">{error}</p>}
      {!progress && !error && <p className="text-slate-500">Loading…</p>}

      {progress && progress.count === 0 && (
        <div className={`${card} text-center`}>
          <p className="font-medium">No analyzed recordings yet</p>
          <p className="mt-1 text-sm text-slate-500">Record a short talk in Live mode or upload a video to get your first report.</p>
        </div>
      )}

      {progress && progress.count > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            <Stat label="Sessions" value={String(progress.count)} />
            <Stat label="Latest score" value={progress.latest !== null ? String(Math.round(progress.latest)) : '–'} hint={change !== null ? `${change >= 0 ? '+' : ''}${change} vs previous` : undefined} />
            <Stat label="Best score" value={progress.best !== null ? String(Math.round(progress.best)) : '–'} />
            <Stat label="Average" value={progress.average !== null ? String(Math.round(progress.average)) : '–'} />
          </div>

          <div className={card}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">Progress</h2>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as Category | 'overall')}
                className="rounded-md border border-slate-300 bg-transparent px-2 py-1 text-sm dark:border-slate-700"
                aria-label="Score to show"
              >
                <option value="overall">Overall</option>
                {CATEGORY_ORDER.map((c) => (
                  <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </div>
            <ProgressChart progress={progress} category={category} />
            <p className="text-xs text-slate-500">Dashed line: 80, a strong score. Click a point to open that session.</p>
          </div>

          <div className={card}>
            <h2 className="mb-3 font-semibold">Latest session by category</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
              {CATEGORY_ORDER.map((c) => {
                const v = latestCats[c] ?? null
                const delta = progress.category_change[c]
                return (
                  <div key={c}>
                    <p className="text-xs text-slate-500">{CATEGORY_LABELS[c]}</p>
                    <p className={`text-2xl font-semibold tabular-nums ${scoreColor(v)}`}>{v !== null ? Math.round(v) : '–'}</p>
                    {delta !== null && delta !== undefined && (
                      <p className={`text-xs ${delta >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {delta >= 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(0)} vs your average
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className={card}>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-semibold">Recent sessions</h2>
              <Link to="/sessions" className="text-sm text-brand-600">See all</Link>
            </div>
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {[...progress.sessions].reverse().slice(0, 5).map((s) => (
                <li key={s.id}>
                  <Link to={`/sessions/${s.id}`} className="flex items-center justify-between py-2 hover:text-brand-600">
                    <span>{s.title}</span>
                    <span className={`font-semibold tabular-nums ${scoreColor(s.overall)}`}>{s.overall !== null ? Math.round(s.overall) : '–'}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
