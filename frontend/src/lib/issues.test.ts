import { describe, expect, it } from 'vitest'
import type { Issue } from '../api/client'
import { translate, hasKey } from '../i18n/core'
import { issueMessage } from './issues'

const tkFor = (lang: 'en' | 'de' | 'ur') => (key: string, fallback: string, vars?: Record<string, string | number | null | undefined>) =>
  hasKey(key) ? translate(lang, key, vars) : fallback

const base: Issue = { id: 'x', category: 'language', kind: 'filler', start: 1, end: 1.4, severity: 'minor', message: 'Filler word "um"', text: 'um' }

describe('issueMessage', () => {
  it('translates by kind with the phrase', () => {
    expect(issueMessage(base, tkFor('en'))).toBe('Filler word "um"')
    expect(issueMessage(base, tkFor('de'))).toContain('um')
    expect(issueMessage(base, tkFor('de'))).not.toBe(base.message)
  })
  it('adds seconds to long body-language stretches', () => {
    const slouch: Issue = { ...base, category: 'posture', kind: 'slouch', start: 3, end: 9, message: 'Slouching (6 s)', text: null }
    expect(issueMessage(slouch, tkFor('en'))).toBe('Slouching (6 s)')
  })
  it('falls back to the server text for unknown kinds', () => {
    expect(issueMessage({ ...base, kind: 'brand_new' }, tkFor('ur'))).toBe(base.message)
  })
  it('tells mispronounced and unclear words apart', () => {
    const w: Issue = { ...base, category: 'pronunciation', kind: 'mispronounced', text: 'data', value: 0, message: '"data" was unclear (estimate)' }
    expect(issueMessage(w, tkFor('en'))).toBe('"data" was unclear (estimate)')
  })
})
