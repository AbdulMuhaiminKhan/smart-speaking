// Pure translation helpers (no React), shared by the provider, tests and canvas code.
import { de } from './de'
import { en, type MessageKey } from './en'
import { ur } from './ur'

export type Lang = 'en' | 'de' | 'ur'
export const LANGS: Lang[] = ['en', 'de', 'ur']
export type Vars = Record<string, string | number | null | undefined>
export type TFunction = (key: MessageKey, vars?: Vars) => string

const DICTS: Record<Lang, Record<MessageKey, string>> = { en, de, ur }
export const STORAGE_KEY = 'ss-lang'

export function isLang(x: unknown): x is Lang {
  return x === 'en' || x === 'de' || x === 'ur'
}

export function dirFor(lang: Lang): 'ltr' | 'rtl' {
  return lang === 'ur' ? 'rtl' : 'ltr'
}

/** BCP 47 locale for dates and numbers. Urdu keeps Western digits, as most Pakistani apps do. */
export function localeFor(lang: Lang): string {
  return lang === 'ur' ? 'ur-PK-u-nu-latn' : lang === 'de' ? 'de-DE' : 'en-GB'
}

export function translate(lang: Lang, key: MessageKey, vars?: Vars): string {
  const text: string = DICTS[lang][key] ?? en[key] ?? key
  if (!vars) return text
  return text.replace(/\{(\w+)\}/g, (m, name: string) => {
    const v = vars[name]
    return v === undefined || v === null ? m : String(v)
  })
}

/** True if the key exists, for lookups built from data (issue kinds, error codes). */
export function hasKey(key: string): key is MessageKey {
  return key in en
}

export function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (isLang(saved)) return saved
  } catch {
    // storage blocked: fall through to the browser language
  }
  const nav = (typeof navigator !== 'undefined' ? navigator.language : 'en').slice(0, 2)
  return isLang(nav) ? nav : 'en'
}

export type { MessageKey }
