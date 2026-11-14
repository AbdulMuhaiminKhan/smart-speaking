import { describe, expect, it } from 'vitest'
import { meterLevel, newFillers, paceZone, PauseTracker } from './feedback'

describe('live feedback', () => {
  it('finds the fillers that are new since the last update', () => {
    expect(newFillers({ um: 1 }, { um: 3, like: 1 })).toEqual(['um', 'um', 'like'])
    expect(newFillers({ um: 2 }, { um: 2 })).toEqual([])
  })

  it('measures silence only after speech started', () => {
    const p = new PauseTracker()
    expect(p.update(0, 0)).toEqual({ speaking: false, silenceS: 0 })
    expect(p.update(0.1, 1000).speaking).toBe(true)
    expect(p.update(0, 1200).speaking).toBe(true) // short gap: still speaking
    expect(p.update(0, 4000).silenceS).toBeCloseTo(3)
  })

  it('maps loudness and pace to display values', () => {
    expect(meterLevel(1)).toBe(1)
    expect(meterLevel(0.001)).toBe(0)
    expect(paceZone(100)).toBe('slow')
    expect(paceZone(140)).toBe('good')
    expect(paceZone(190)).toBe('fast')
    expect(paceZone(null)).toBe('none')
  })
})
