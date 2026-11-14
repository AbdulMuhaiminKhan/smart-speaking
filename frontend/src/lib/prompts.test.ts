import { describe, expect, it } from 'vitest'
import { LANGS } from '../i18n/core'
import { lightAt, PROMPT_MODES, promptBank, randomPrompt, timingLights } from './prompts'

describe('practice prompts', () => {
  it('has prompts for every mode in every language, the same count per language', () => {
    for (const mode of PROMPT_MODES) {
      const counts = LANGS.map((l) => promptBank(mode, l).length)
      expect(counts[0]).toBeGreaterThan(4)
      expect(new Set(counts).size).toBe(1)
    }
  })
  it('picks a different prompt than the current one', () => {
    const first = promptBank('interview', 'de')[0]
    expect(randomPrompt('interview', 'de', first, () => 0)).not.toBe(first)
  })
})

describe('timing lights', () => {
  it('uses Toastmasters times for Table Topics', () => {
    const l = timingLights('table_topics', 120)
    expect(lightAt(l, 59)).toBe('none')
    expect(lightAt(l, 60)).toBe('green')
    expect(lightAt(l, 95)).toBe('amber')
    expect(lightAt(l, 121)).toBe('red')
  })
  it('scales with the target elsewhere and is off without one', () => {
    expect(lightAt(timingLights('elevator_pitch', 60), 46)).toBe('amber')
    expect(timingLights('free_talk', null)).toBeNull()
  })
})
