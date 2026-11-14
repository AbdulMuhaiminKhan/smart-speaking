import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n/core'
import { Icon, type IconName } from './Icon'
import { LanguageSwitcher } from './LanguageSwitcher'

/** The SmartSpeaking mark: a five-line stave with one note, drawn, not typed. */
export function Mark({ className = 'h-8 w-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" className="fill-brand-600" />
      {[9, 12.5, 16, 19.5, 23].map((y) => (
        <line key={y} x1="5" x2="27" y1={y} y2={y} stroke="white" strokeOpacity="0.45" strokeWidth="1" />
      ))}
      <ellipse cx="13" cy="19.5" rx="3.3" ry="2.4" transform="rotate(-20 13 19.5)" fill="white" />
      <path d="M16 19V7.5c2.5.6 4.6 2 5.4 4.4" stroke="white" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  )
}

const NAV: { to: string; label: MessageKey; icon: IconName; end?: boolean }[] = [
  { to: '/', label: 'nav.dashboard', icon: 'chart', end: true },
  { to: '/live', label: 'nav.live', icon: 'mic' },
  { to: '/upload', label: 'nav.upload', icon: 'upload' },
  { to: '/sessions', label: 'nav.sessions', icon: 'play' },
  { to: '/settings', label: 'nav.settings', icon: 'target' },
]

const railLink = ({ isActive }: { isActive: boolean }) =>
  `flex shrink-0 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? 'bg-white/12 text-white shadow-[inset_0_0_0_1px_rgb(255_255_255/0.08)]' : 'text-score-200 hover:bg-white/6 hover:text-white'
  }`

export function Layout() {
  const { user, signOut } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <aside className="z-20 bg-score-900 text-white lg:sticky lg:top-0 lg:h-screen">
        <div className="flex h-full flex-col gap-4 px-4 py-3 lg:py-6">
          <div className="flex items-center justify-between gap-2">
            <NavLink to="/" className="flex items-center gap-2.5 px-1 text-[15px] font-semibold tracking-tight">
              <Mark />
              {t('app.name')}
            </NavLink>
            <LanguageSwitcher className="h-8 border-white/20 bg-score-800 py-0 text-white lg:hidden" />
          </div>
          <nav className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden lg:mt-4 lg:flex-col lg:overflow-visible">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={railLink}>
                <Icon name={n.icon} size={18} />
                {t(n.label)}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto hidden space-y-3 lg:block">
            <LanguageSwitcher className="w-full border-white/20 bg-score-800 text-white" />
            <div className="flex items-center justify-between gap-2 border-t border-white/10 pt-3">
              <span className="truncate text-xs text-score-200" title={user?.email}>
                {user?.name || user?.email}
              </span>
              <button
                type="button"
                onClick={() => void signOut().then(() => navigate('/login'))}
                className="shrink-0 rounded px-2 py-1 text-xs text-score-200 hover:bg-white/10 hover:text-white"
              >
                {t('nav.sign_out')}
              </button>
            </div>
            <p className="flex gap-2 text-[11px] leading-snug text-score-200/80">
              <Icon name="lock" size={14} className="mt-0.5 shrink-0" />
              {t('footer.privacy')}
            </p>
          </div>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-10 lg:py-10">
        <Outlet />
        <div className="mt-12 flex items-center justify-between gap-3 border-t border-slate-200 pt-4 text-xs text-slate-500 lg:hidden dark:border-slate-800">
          <span>{t('footer.privacy')}</span>
          <button type="button" onClick={() => void signOut().then(() => navigate('/login'))} className="underline-offset-4 hover:underline">
            {t('nav.sign_out')}
          </button>
        </div>
      </main>
    </div>
  )
}
