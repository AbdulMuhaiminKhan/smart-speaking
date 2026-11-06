import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type PracticeSession } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import { formatTime } from '../lib/format'

export function SessionsPage() {
  const [sessions, setSessions] = useState<PracticeSession[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listSessions()
      .then(setSessions)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : 'Could not load sessions.'))
  }, [])

  if (error) return <p className="text-red-700 dark:text-red-300">{error}</p>
  if (!sessions) return <p className="text-slate-500">Loading…</p>

  return (
    <div>
      <h1 className="text-2xl font-semibold">Your sessions</h1>
      {sessions.length === 0 ? (
        <p className="mt-4 text-slate-600 dark:text-slate-400">
          No sessions yet.{' '}
          <Link to="/" className="text-brand-600">
            Upload your first recording
          </Link>
          .
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
          {sessions.map((s) => (
            <li key={s.id}>
              <Link
                to={`/sessions/${s.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <div>
                  <p className="font-medium">{s.title}</p>
                  <p className="text-sm text-slate-500">
                    {new Date(s.created_at).toLocaleString()}
                    {s.duration_s !== null && ` · ${formatTime(s.duration_s)}`}
                  </p>
                </div>
                <StatusBadge status={s.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
