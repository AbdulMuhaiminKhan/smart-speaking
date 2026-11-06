import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, authApi, type ModelPreset, type UserSettings } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const card = 'rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900'
const input = 'mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700'

export function SettingsPage() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [settings, setSettings] = useState<UserSettings>(user!.settings)
  const [saved, setSaved] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pw, setPw] = useState({ current: '', next: '' })
  const [deletePw, setDeletePw] = useState('')

  async function save(next: UserSettings) {
    setSettings(next)
    setError(null)
    try {
      setUser(await authApi.updateSettings(next))
      setSaved('Settings saved.')
      setTimeout(() => setSaved(null), 2000)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not save settings.')
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await authApi.changePassword(pw.current, pw.next)
      setPw({ current: '', next: '' })
      setSaved('Password changed.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change the password.')
    }
  }

  async function deleteAccount(e: FormEvent) {
    e.preventDefault()
    if (!confirm('Delete your account, every recording and every report? This cannot be undone.')) return
    try {
      await authApi.deleteAccount(deletePw)
      setUser(null)
      navigate('/login')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete the account.')
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      {saved && <p className="rounded-md bg-emerald-50 px-4 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">{saved}</p>}
      {error && <p role="alert" className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">{error}</p>}

      <section className={card}>
        <h2 className="mb-3 font-semibold">Analysis</h2>
        <label className="block text-sm font-medium">
          Language
          <select value={settings.language} onChange={(e) => void save({ ...settings, language: e.target.value as 'en' })} className={input}>
            <option value="en">English</option>
          </select>
          <span className="mt-1 block text-xs font-normal text-slate-500">More languages can be added later; the app is built for it.</span>
        </label>
        <fieldset className="mt-4">
          <legend className="text-sm font-medium">Speed vs accuracy</legend>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {(
              [
                ['fast', 'Fast', 'Whisper base'],
                ['balanced', 'Balanced', 'Whisper small'],
                ['accurate', 'Accurate', 'Whisper large-v3-turbo'],
              ] as [ModelPreset, string, string][]
            ).map(([value, label, hint]) => (
              <button
                key={value}
                type="button"
                onClick={() => void save({ ...settings, model_preset: value })}
                className={`rounded-md border px-3 py-2 text-left text-sm ${settings.model_preset === value ? 'border-brand-600 bg-brand-50 dark:bg-slate-800' : 'border-slate-300 dark:border-slate-700'}`}
              >
                <span className="block font-medium">{label}</span>
                <span className="block text-xs text-slate-500">{hint}</span>
              </button>
            ))}
          </div>
        </fieldset>
      </section>

      <section className={card}>
        <h2 className="mb-3 font-semibold">Privacy</h2>
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" className="mt-1" checked={settings.auto_delete_video} onChange={(e) => void save({ ...settings, auto_delete_video: e.target.checked })} />
          <span>
            <span className="font-medium">Delete the video after analysis</span>
            <span className="block text-slate-500">Keeps your report and transcript, removes the recording and audio from this computer.</span>
          </span>
        </label>
      </section>

      <section className={card}>
        <h2 className="mb-3 font-semibold">Password</h2>
        <form onSubmit={(e) => void changePassword(e)} className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-medium">
            Current password
            <input type="password" autoComplete="current-password" required value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} className={input} />
          </label>
          <label className="text-sm font-medium">
            New password
            <input type="password" autoComplete="new-password" required minLength={8} value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} className={input} />
          </label>
          <button className="w-fit rounded-md border border-slate-300 px-4 py-2 text-sm font-medium dark:border-slate-700">Change password</button>
        </form>
      </section>

      <section className={`${card} border-red-200 dark:border-red-900`}>
        <h2 className="mb-1 font-semibold text-red-700 dark:text-red-400">Delete account</h2>
        <p className="mb-3 text-sm text-slate-500">Deletes your account, every recording, transcript and report from this computer.</p>
        <form onSubmit={(e) => void deleteAccount(e)} className="flex flex-wrap items-end gap-3">
          <label className="text-sm font-medium">
            Your password
            <input type="password" autoComplete="current-password" required value={deletePw} onChange={(e) => setDeletePw(e.target.value)} className={input} />
          </label>
          <button className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Delete everything</button>
        </form>
      </section>
      <p className="text-xs text-slate-400">Signed in as {user?.email}</p>
    </div>
  )
}
