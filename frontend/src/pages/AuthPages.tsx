import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import { useI18n } from '../i18n'
import { errorText } from '../lib/errors'

const input = 'mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700'

function Shell({ title, children, footer }: { title: string; children: React.ReactNode; footer: React.ReactNode }) {
  const { t } = useI18n()
  return (
    <div className="mx-auto mt-10 max-w-sm px-4">
      <div className="mb-6 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-white">S</span>
          {t('app.name')}
        </div>
        <LanguageSwitcher />
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h1 className="mb-4 text-xl font-semibold">{title}</h1>
        {children}
      </div>
      <p className="mt-4 text-center text-sm text-slate-500">{footer}</p>
      <p className="mt-6 text-center text-xs text-slate-400">
        {t('auth.tagline')}
      </p>
    </div>
  )
}

export function LoginPage() {
  const { user, setUser } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={from} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setUser(await authApi.login(email, password))
      navigate(from, { replace: true })
    } catch (err) {
      setError(errorText(err, t, 'auth.sign_in_failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title={t('auth.sign_in')} footer={<>{t('auth.no_account')} <Link to="/register" className="text-brand-600">{t('auth.create_one')}</Link></>}>
      <form onSubmit={(e) => void submit(e)} className="space-y-4">
        <label className="block text-sm font-medium">
          {t('auth.email')}
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
        </label>
        <label className="block text-sm font-medium">
          {t('auth.password')}
          <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
        </label>
        {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60">
          {busy ? t('auth.signing_in') : t('auth.sign_in')}
        </button>
      </form>
    </Shell>
  )
}

export function RegisterPage() {
  const { user, setUser } = useAuth()
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (password.length < 8) {
      setError(t('auth.password_short'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const created = await authApi.register(email, password, name)
      // Start the new account in the language chosen on this page.
      const withLang =
        created.settings.ui_language === lang
          ? created
          : await authApi.updateSettings({ ...created.settings, ui_language: lang, language: lang }).catch(() => created)
      setUser(withLang)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorText(err, t, 'auth.create_failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title={t('auth.create_title')} footer={<>{t('auth.have_account')} <Link to="/login" className="text-brand-600">{t('auth.sign_in')}</Link></>}>
      <form onSubmit={(e) => void submit(e)} className="space-y-4">
        <label className="block text-sm font-medium">
          {t('auth.name_optional')}
          <input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} className={input} />
        </label>
        <label className="block text-sm font-medium">
          {t('auth.email')}
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
        </label>
        <label className="block text-sm font-medium">
          {t('auth.password')}
          <input type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
          <span className="mt-1 block text-xs font-normal text-slate-500">{t('auth.password_hint')}</span>
        </label>
        {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60">
          {busy ? t('auth.creating') : t('auth.create')}
        </button>
      </form>
    </Shell>
  )
}
