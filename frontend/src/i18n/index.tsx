// Small, dependency-free translations: English, German and Urdu (right to left).
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { dirFor, hasKey, initialLang, localeFor, STORAGE_KEY, translate, type Lang, type TFunction, type Vars } from './core'

interface I18nState {
  lang: Lang
  dir: 'ltr' | 'rtl'
  setLang: (l: Lang) => void
  t: TFunction
  /** Optional key built at runtime; returns the fallback when the key is unknown. */
  tk: (key: string, fallback: string, vars?: Vars) => string
  formatDate: (iso: string | Date, withTime?: boolean) => string
}

const I18nContext = createContext<I18nState | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem(STORAGE_KEY, l)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = dirFor(lang)
  }, [lang])

  const value = useMemo<I18nState>(() => {
    const t: TFunction = (key, vars) => translate(lang, key, vars)
    const locale = localeFor(lang)
    return {
      lang,
      dir: dirFor(lang),
      setLang,
      t,
      tk: (key, fallback, vars) => (hasKey(key) ? translate(lang, key, vars) : fallback),
      formatDate: (iso, withTime = true) => {
        const d = typeof iso === 'string' ? new Date(iso) : iso
        return withTime
          ? d.toLocaleString(locale, { dateStyle: 'medium', timeStyle: 'short' })
          : d.toLocaleDateString(locale, { dateStyle: 'medium' })
      },
    }
  }, [lang, setLang])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useI18n(): I18nState {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}

