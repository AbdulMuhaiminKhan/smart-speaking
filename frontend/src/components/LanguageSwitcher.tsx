import { authApi } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useI18n } from '../i18n'
import { LANGS, type Lang } from '../i18n/core'

/** App language picker. When signed in, the choice is saved to the account. */
export function LanguageSwitcher({ className = '' }: { className?: string }) {
  const { lang, setLang, t } = useI18n()
  const { user, setUser } = useAuth()

  function change(next: Lang) {
    setLang(next)
    if (user && user.settings.ui_language !== next) {
      authApi
        .updateSettings({ ...user.settings, ui_language: next })
        .then(setUser)
        .catch(() => undefined)
    }
  }

  return (
    <select
      value={lang}
      onChange={(e) => change(e.target.value as Lang)}
      aria-label={t('nav.language')}
      className={`rounded-md border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700 ${className}`}
    >
      {LANGS.map((l) => (
        <option key={l} value={l} lang={l}>
          {t(`lang.${l}`)}
        </option>
      ))}
    </select>
  )
}
