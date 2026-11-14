import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PracticeSession } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import { useI18n } from '../i18n'
import { errorText } from '../lib/errors'
import { formatTime } from '../lib/format'

export function SessionsPage() {
  const [sessions, setSessions] = useState<PracticeSession[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { t, formatDate } = useI18n()

  useEffect(() => {
    api
      .listSessions()
      .then(setSessions)
      .catch((e: unknown) => setError(errorText(e, t, 'err.load_sessions')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (error) return <p className="text-red-700 dark:text-red-300">{error}</p>
  if (!sessions) return <p className="text-slate-500">{t('common.loading')}</p>

  return (
    <div>
      <h1 className="text-2xl font-semibold">{t('sessions.title')}</h1>
      {sessions.length === 0 ? (
        <p className="mt-4 text-slate-600 dark:text-slate-400">
          {t('sessions.empty')}{' '}
          <Link to="/upload" className="text-brand-600">
            {t('sessions.upload_first')}
          </Link>
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
                    {formatDate(s.created_at)}
                    {s.duration_s !== null && ` · ${formatTime(s.duration_s)}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={s.status} />
                  <button
                    type="button"
                    aria-label={t('sessions.delete_label', { title: s.title })}
                    onClick={(e) => {
                      e.preventDefault()
                      if (!confirm(t('sessions.confirm_delete', { title: s.title }))) return
                      api
                        .deleteSession(s.id)
                        .then(() => setSessions((all) => all?.filter((x) => x.id !== s.id) ?? null))
                        .catch(() => setError(t('err.delete_failed')))
                    }}
                    className="rounded px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950"
                  >
                    {t('common.delete')}
                  </button>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
