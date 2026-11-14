import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import { Mark } from '../components/Layout'
import { useI18n } from '../i18n'
import { errorText } from '../lib/errors'

const input = 'field'

function Shell({ title, children, footer }: { title: string; children: React.ReactNode; footer: React.ReactNode }) {
  const { t } = useI18n()
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-score-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3 text-lg font-semibold">
          <Mark className="h-10 w-10" />
          {t('app.name')}
        </div>
        <div className="max-w-md">
          <p className="tempo text-3xl text-score-100">Moderato</p>
          <p className="mt-3 text-2xl font-semibold leading-snug tracking-tight">{t('auth.pitch')}</p>
          {/* A stave with a few marks, the product's own notation. */}
          <svg viewBox="0 0 400 70" className="mt-8 w-full" aria-hidden="true">
            {[10, 22, 34, 46, 58].map((y) => (
              <line key={y} x1="0" x2="400" y1={y} y2={y} stroke="white" strokeOpacity="0.25" />
            ))}
            {[100, 200, 300].map((x) => (
              <line key={x} x1={x} x2={x} y1="10" y2="58" stroke="white" strokeOpacity="0.25" />
            ))}
            {[
              [40, 46, true],
              [70, 34, true],
              [130, 28, false],
              [165, 40, true],
              [240, 22, true],
              [270, 52, false],
              [330, 34, true],
              [365, 28, true],
            ].map(([x, y, filled], i) => (
              <ellipse
                key={i}
                cx={x as number}
                cy={y as number}
                rx="7"
                ry="5"
                transform={`rotate(-22 ${x} ${y})`}
                fill={filled ? 'oklch(0.86 0.11 85)' : 'none'}
                stroke="oklch(0.86 0.11 85)"
                strokeWidth="2"
              />
            ))}
          </svg>
        </div>
        <p className="flex max-w-md gap-2 text-sm text-score-200">
          <Icon name="lock" size={18} className="mt-0.5 shrink-0" />
          {t('auth.tagline')}
        </p>
      </section>
      <section className="flex flex-col justify-center px-4 py-10 sm:px-10">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-lg font-semibold lg:invisible">
              <Mark />
              {t('app.name')}
            </div>
            <LanguageSwitcher />
          </div>
          <h1 className="mb-6 text-2xl font-semibold tracking-tight">{title}</h1>
          {children}
          <p className="mt-6 text-sm text-slate-500">{footer}</p>
          <p className="mt-10 text-xs text-slate-400 lg:hidden">{t('auth.tagline')}</p>
        </div>
      </section>
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
        <button disabled={busy} className="w-full btn-primary">
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
        <button disabled={busy} className="w-full btn-primary">
          {busy ? t('auth.creating') : t('auth.create')}
        </button>
      </form>
    </Shell>
  )
}
