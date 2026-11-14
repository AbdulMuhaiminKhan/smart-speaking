import { describe, expect, it } from 'vitest'
import { grade } from './grade'

describe('grade', () => {
  it('rates a value against good and acceptable ranges', () => {
    expect(grade(0.8, [0.75, 1], [0.6, 1])).toBe('good')
    expect(grade(0.65, [0.75, 1], [0.6, 1])).toBe('ok')
    expect(grade(0.3, [0.75, 1], [0.6, 1])).toBe('work')
    expect(grade(null, [0, 1], [0, 1])).toBe('none')
  })
})
