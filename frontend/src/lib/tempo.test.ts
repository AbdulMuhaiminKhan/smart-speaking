import { describe, expect, it } from 'vitest'
import { tempoMarking } from './tempo'

describe('tempoMarking', () => {
  it('maps pace to a tempo word', () => {
    expect(tempoMarking(90)).toBe('Adagio')
    expect(tempoMarking(140)).toBe('Moderato')
    expect(tempoMarking(200)).toBe('Presto')
  })
})
