import { describe, expect, it } from 'vitest'
import { recentChange } from '../lib/trends'

describe('recentChange', () => {
  it('compares the latest sessions with the ones before', () => {
    expect(recentChange([6, 5, 4, 3, 2, 1], 3)).toEqual({ recent: 2, before: 5 })
    expect(recentChange([4, null, 2], 3)).toEqual({ recent: 2, before: 4 })
  })
  it('needs two values', () => {
    expect(recentChange([3, null])).toBeNull()
  })
})
