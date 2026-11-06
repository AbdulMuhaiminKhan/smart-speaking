import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError, authApi } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const input = 'mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700'

function Shell({ title, children, footer }: { title: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div className="mx-auto mt-10 max-w-sm">
      <div className="mb-6 flex items-center gap-2 text-lg font-semibold">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-white">S</span>
        SmartSpeaking
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h1 className="mb-4 text-xl font-semibold">{title}</h1>
        {children}
      </div>
      <p className="mt-4 text-center text-sm text-slate-500">{footer}</p>
      <p className="mt-6 text-center text-xs text-slate-400">
        Everything runs on this computer. Your recordings never leave it.
      </p>
    </div>
  )
}

export function LoginPage() {
  const { user, setUser } = useAuth()
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
      setError(err instanceof ApiError ? err.message : 'Sign-in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title="Sign in" footer={<>No account yet? <Link to="/register" className="text-brand-600">Create one</Link></>}>
      <form onSubmit={(e) => void submit(e)} className="space-y-4">
        <label className="block text-sm font-medium">
          Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
        </label>
        {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </Shell>
  )
}

export function RegisterPage() {
  const { user, setUser } = useAuth()
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
      setError('Use at least 8 characters for your password.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      setUser(await authApi.register(email, password, name))
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title="Create your account" footer={<>Already have one? <Link to="/login" className="text-brand-600">Sign in</Link></>}>
      <form onSubmit={(e) => void submit(e)} className="space-y-4">
        <label className="block text-sm font-medium">
          Name (optional)
          <input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} className={input} />
        </label>
        <label className="block text-sm font-medium">
          Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
          <span className="mt-1 block text-xs font-normal text-slate-500">At least 8 characters. Stored only as a secure hash.</span>
        </label>
        {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60">
          {busy ? 'Creating…' : 'Create account'}
        </button>
      </form>
    </Shell>
  )
}
