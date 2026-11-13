import type { MessageKey } from '../i18n/core'

// Each check returns a message key (see i18n/en.ts), or null when the file is fine.
export const MAX_BYTES = 2 * 1024 ** 3
export const MAX_SECONDS = 15 * 60
export const MIN_SECONDS = 5
const EXTENSIONS = ['.mp4', '.webm', '.mov', '.m4v']

export function checkExtension(name: string): MessageKey | null {
  const lower = name.toLowerCase()
  return EXTENSIONS.some((ext) => lower.endsWith(ext)) ? null : 'upload.err_ext'
}

export function checkSize(bytes: number): MessageKey | null {
  if (bytes === 0) return 'upload.err_empty'
  if (bytes > MAX_BYTES) return 'upload.err_big'
  return null
}

export function checkDuration(seconds: number | null): MessageKey | null {
  if (seconds === null || !Number.isFinite(seconds)) return null // server checks it
  if (seconds < MIN_SECONDS) return 'upload.err_short'
  if (seconds > MAX_SECONDS + 30) return 'upload.err_long'
  return null
}

// Reads the duration in the browser so we can reject long files before uploading.
export function readDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    const done = (value: number | null) => {
      URL.revokeObjectURL(url)
      resolve(value)
    }
    video.onloadedmetadata = () => done(Number.isFinite(video.duration) ? video.duration : null)
    video.onerror = () => done(null)
    setTimeout(() => done(null), 5000)
    video.src = url
  })
}
