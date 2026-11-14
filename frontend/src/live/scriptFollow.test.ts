import { describe, expect, it } from 'vitest'
import { followPosition, norm, skippedRanges, tokenize } from './scriptFollow'

const script = tokenize(
  'Good morning everyone. Today I will share three ideas about saving energy at home. ' +
    'First, turn the heating down one degree. Second, wash clothes cold. Third, switch off standby.',
).map((w) => w.key)

describe('script following', () => {
  it('normalizes like the server', () => {
    expect(norm('Morning,')).toBe('morning')
    expect(norm('كيا')).toBe('کیا')
  })
  it('moves forward with the speaker', () => {
    const pos = followPosition(script, ['today', 'i', 'will', 'share', 'three'], 3)
    expect(script[pos - 1]).toBe('three')
  })
  it('notices a jump ahead (a skipped passage)', () => {
    const pos = followPosition(script, ['second', 'wash', 'clothes', 'cold'], 6)
    expect(script[pos - 1]).toBe('cold')
  })
  it('stays put when the words are not in the script', () => {
    expect(followPosition(script, ['completely', 'different', 'words', 'here'], 6)).toBe(6)
  })
})

describe('skipped passages', () => {
  it('flags only the script words that were not heard', () => {
    const s = tokenize('one two three four five six seven eight nine ten').map((w) => w.key)
    expect(skippedRanges(s, 0, 10, ['um', 'one', 'two', 'nine', 'ten'])).toEqual([[2, 8]])
    expect(skippedRanges(s, 0, 5, ['one', 'three', 'five'])).toEqual([])
  })
})
