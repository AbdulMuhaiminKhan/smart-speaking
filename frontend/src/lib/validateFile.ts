export const MAX_BYTES = 2 * 1024 ** 3
export const MAX_SECONDS = 15 * 60
export const MIN_SECONDS = 5
const EXTENSIONS = ['.mp4', '.webm', '.mov', '.m4v']

export function checkExtension(name: string): string | null {
  const lower = name.toLowerCase()
  return EXTENSIONS.some((ext) => lower.endsWith(ext))
    ? null
    : 'Please choose an mp4, webm or mov video.'
}

export function checkSize(bytes: number): string | null {
  if (bytes === 0) return 'This file is empty.'
  if (bytes > MAX_BYTES) return 'This file is larger than 2 GB.'
  return null
}

export function checkDuration(seconds: number | null): string | null {
  if (seconds === null || !Number.isFinite(seconds)) return null // server checks it
  if (seconds < MIN_SECONDS) return `This clip is under ${MIN_SECONDS} seconds.`
  if (seconds > MAX_SECONDS + 30) return 'This clip is longer than 15 minutes.'
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
