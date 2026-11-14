// Write, paste or open a speech script, and keep a few on this computer for next time.
import { useState } from 'react'
import { useI18n } from '../i18n'

interface Saved {
  id: string
  title: string
  text: string
}

const KEY = 'ss-scripts'

function load(): Saved[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]') as Saved[]
  } catch {
    return []
  }
}

function store(list: Saved[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, 20)))
  } catch {
    // storage full or blocked: saving is a convenience only
  }
}

export function ScriptEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useI18n()
  const [saved, setSaved] = useState<Saved[]>(load)
  const words = value.split(/\s+/).filter(Boolean).length

  async function open(file: File | undefined) {
    if (!file) return
    const text = await file.text()
    onChange(text.replace(/^#+\s*/gm, '').trim())
  }

  function save() {
    if (!value.trim()) return
    const title = value.trim().split(/\s+/).slice(0, 6).join(' ')
    const next = [{ id: String(Date.now()), title, text: value }, ...saved.filter((s) => s.text !== value)]
    setSaved(next)
    store(next)
  }

  function remove(id: string) {
    const next = saved.filter((s) => s.id !== id)
    setSaved(next)
    store(next)
  }

  return (
    <div className="w-full space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium">{t('script.your_script')}</span>
        <div className="flex items-center gap-2 text-sm">
          <label className="cursor-pointer rounded-md px-2 py-1 text-brand-600 hover:bg-brand-50 dark:hover:bg-slate-800">
            {t('script.open_file')}
            <input type="file" accept=".txt,.md,text/plain,text/markdown" className="hidden" onChange={(e) => void open(e.target.files?.[0])} />
          </label>
          <button type="button" onClick={save} disabled={!value.trim()} className="rounded-md px-2 py-1 text-brand-600 hover:bg-brand-50 disabled:opacity-40 dark:hover:bg-slate-800">
            {t('script.save')}
          </button>
        </div>
      </div>
      <textarea
        dir="auto"
        rows={6}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t('upload.script_placeholder')}
        className="w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
      />
      <p className="text-xs text-slate-500">{t('script.word_count', { n: words, min: Math.max(1, Math.round(words / 140)) })}</p>
      {saved.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {saved.map((s) => (
            <span key={s.id} className="inline-flex items-center rounded-full border border-slate-300 text-xs dark:border-slate-700">
              <button type="button" dir="auto" onClick={() => onChange(s.text)} className="px-3 py-1 hover:text-brand-600">
                {s.title}…
              </button>
              <button type="button" aria-label={t('common.delete')} onClick={() => remove(s.id)} className="pe-2 text-slate-400 hover:text-red-600">
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
