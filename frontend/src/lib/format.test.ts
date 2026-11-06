import { describe, expect, it } from 'vitest'
import { formatBytes, formatTime } from './format'
import { checkDuration, checkExtension, checkSize, MAX_BYTES } from './validateFile'

describe('formatTime', () => {
  it('formats minutes and seconds', () => {
    expect(formatTime(0)).toBe('0:00')
    expect(formatTime(65.9)).toBe('1:05')
    expect(formatTime(-3)).toBe('0:00')
  })
})

describe('formatBytes', () => {
  it('picks a sensible unit', () => {
    expect(formatBytes(2048)).toBe('2 KB')
    expect(formatBytes(5 * 1024 ** 2)).toBe('5.0 MB')
    expect(formatBytes(3 * 1024 ** 3)).toBe('3.00 GB')
  })
})

describe('file checks', () => {
  it('accepts supported videos only', () => {
    expect(checkExtension('talk.MP4')).toBeNull()
    expect(checkExtension('talk.mov')).toBeNull()
    expect(checkExtension('notes.txt')).not.toBeNull()
  })
  it('rejects empty and huge files', () => {
    expect(checkSize(0)).not.toBeNull()
    expect(checkSize(MAX_BYTES + 1)).not.toBeNull()
    expect(checkSize(1000)).toBeNull()
  })
  it('checks duration but lets the server decide when unknown', () => {
    expect(checkDuration(null)).toBeNull()
    expect(checkDuration(2)).not.toBeNull()
    expect(checkDuration(20 * 60)).not.toBeNull()
    expect(checkDuration(120)).toBeNull()
  })
})
