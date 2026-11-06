import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition ${
    isActive
      ? 'bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-white'
      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
  }`

export function Layout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-semibold">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white">S</span>
            SmartSpeaking
          </NavLink>
          <nav className="flex flex-wrap items-center gap-1">
            <NavLink to="/" end className={link}>
              Dashboard
            </NavLink>
            <NavLink to="/live" className={link}>
              Live
            </NavLink>
            <NavLink to="/upload" className={link}>
              Upload
            </NavLink>
            <NavLink to="/sessions" className={link}>
              Sessions
            </NavLink>
            <NavLink to="/settings" className={link}>
              Settings
            </NavLink>
            <button
              type="button"
              title={user?.email}
              onClick={() => void signOut().then(() => navigate('/login'))}
              className="ml-2 rounded-md px-3 py-2 text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white"
            >
              Sign out
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-5xl px-4 pb-8 text-xs text-slate-500">
        Your recordings are processed on this computer and never leave it.
      </footer>
    </div>
  )
}
