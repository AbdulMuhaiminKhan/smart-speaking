export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`
}

export const STAGE_LABELS: Record<string, string> = {
  preprocess: 'Reading the video and extracting audio',
  transcribe: 'Transcribing your speech',
  language: 'Checking pace, pauses and word choice',
  voice: 'Analyzing pitch, volume and tone',
  pronunciation: 'Checking pronunciation',
  body: 'Tracking eye contact, posture and gestures',
  report: 'Scoring your talk',
  coaching: 'Your local AI coach is writing feedback',
}
