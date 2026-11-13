import { ApiError } from '../api/client'
import { hasKey, type MessageKey, type TFunction } from '../i18n/core'

/** A translated message for an API error, by its code, falling back to the server text. */
export function errorText(e: unknown, t: TFunction, fallback: MessageKey): string {
  if (e instanceof ApiError) {
    const key = `err.${e.code}`
    if (hasKey(key)) return t(key, { detail: e.message })
    return e.message || t(fallback)
  }
  return t(fallback)
}
