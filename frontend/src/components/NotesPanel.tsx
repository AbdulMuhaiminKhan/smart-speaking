// Notes pinned to moments of the video: add one at the current time, edit, delete, jump.
import { useState } from 'react'
import { api, type Note } from '../api/client'
import { useI18n } from '../i18n'
import { formatTime } from '../lib/format'
import { Icon } from './Icon'

interface Props {
  sessionId: string
  notes: Note[]
  onChange: (notes: Note[]) => void
  currentTime: number
  onSeek: (t: number) => void
  pause: () => void
}

export function NotesPanel({ sessionId, notes, onChange, currentTime, onSeek, pause }: Props) {
  const { t } = useI18n()
  const [draft, setDraft] = useState<{ id: string | null; t: number; text: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  function startNew() {
    pause()
    setDraft({ id: null, t: Math.round(currentTime * 10) / 10, text: '' })
  }

  async function save() {
    if (!draft || !draft.text.trim()) return
    setError(null)
    try {
      const saved = draft.id
        ? await api.editNote(sessionId, draft.id, draft.t, draft.text)
        : await api.addNote(sessionId, draft.t, draft.text)
      const rest = notes.filter((n) => n.id !== saved.id)
      onChange([...rest, saved].sort((a, b) => a.t - b.t))
      setDraft(null)
    } catch {
      setError(t('notes.save_failed'))
    }
  }

  async function remove(n: Note) {
    try {
      await api.deleteNote(sessionId, n.id)
      onChange(notes.filter((x) => x.id !== n.id))
    } catch {
      setError(t('err.delete_failed'))
    }
  }

  return (
    <section className="card p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <Icon name="note" size={18} /> {t('notes.title')}
        </h2>
        <button
          type="button"
          onClick={startNew}
          className="btn-quiet px-3 py-1.5"
        >
          {t('notes.add_at', { time: formatTime(currentTime) })}
        </button>
      </div>
      {draft && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void save()
          }}
          className="mt-3 space-y-2"
        >
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Icon name="pin" size={16} />
            <span className="font-mono">{formatTime(draft.t)}</span>
          </div>
          <textarea
            autoFocus
            dir="auto"
            rows={2}
            maxLength={2000}
            value={draft.text}
            onChange={(e) => setDraft({ ...draft, text: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void save()
              if (e.key === 'Escape') setDraft(null)
            }}
            placeholder={t('notes.placeholder')}
            className="w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
          />
          <div className="flex gap-2">
            <button className="btn-primary px-3 py-1.5" disabled={!draft.text.trim()}>
              {t('common.save')}
            </button>
            <button type="button" onClick={() => setDraft(null)} className="rounded-md px-3 py-1.5 text-sm text-slate-500">
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {notes.length === 0 && !draft ? (
        <p className="mt-2 text-sm text-slate-500">{t('notes.empty')}</p>
      ) : (
        <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
          {notes.map((n) => (
            <li key={n.id} className="group flex items-start gap-3 py-2">
              <button type="button" onClick={() => onSeek(n.t)} className="font-mono text-xs text-brand-600 hover:underline">
                {formatTime(n.t)}
              </button>
              <p dir="auto" className="flex-1 whitespace-pre-wrap text-sm">
                {n.text}
              </p>
              <div className="flex gap-1 opacity-60 group-hover:opacity-100">
                <button type="button" onClick={() => setDraft({ id: n.id, t: n.t, text: n.text })} className="rounded px-1.5 text-xs text-slate-500 hover:text-brand-600">
                  {t('notes.edit')}
                </button>
                <button type="button" aria-label={t('common.delete')} onClick={() => void remove(n)} className="rounded px-1 text-slate-400 hover:text-red-600">
                  <Icon name="trash" size={15} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
