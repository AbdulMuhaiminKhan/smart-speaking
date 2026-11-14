import { describe, expect, it } from 'vitest'
import { de } from './de'
import { en } from './en'
import { dirFor, translate } from './core'
import { ur } from './ur'

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('translations', () => {
  it.each([
    ['de', de],
    ['ur', ur],
  ])('%s has every key with the same placeholders', (_name, dict) => {
    for (const [key, text] of Object.entries(en)) {
      const other = (dict as Record<string, string>)[key]
      expect(other, key).toBeTruthy()
      expect(placeholders(other), key).toEqual(placeholders(text))
    }
  })

  it('fills placeholders and keeps unknown ones', () => {
    expect(translate('en', 'dash.welcome_name', { name: 'Abdul' })).toBe('Welcome back, Abdul')
    expect(translate('de', 'upload.err_short', { n: 5 })).toBe('Dieser Clip ist kürzer als 5 Sekunden.')
    expect(translate('en', 'dash.welcome_name')).toBe('Welcome back, {name}')
  })

  it('lays Urdu out right to left', () => {
    expect(dirFor('ur')).toBe('rtl')
    expect(dirFor('de')).toBe('ltr')
  })
})
