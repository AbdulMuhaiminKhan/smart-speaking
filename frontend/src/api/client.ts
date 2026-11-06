// Typed client for the SmartSpeaking API. Mirrors backend/app/schemas.

export type SessionStatus = 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed'
export type SessionMode = 'free_talk' | 'timed_pitch' | 'script'
export type ModelPreset = 'fast' | 'balanced' | 'accurate'

export interface PracticeSession {
  id: string
  title: string
  source: 'upload' | 'live'
  mode: SessionMode
  target_seconds: number | null
  language: string
  model_preset: ModelPreset
  original_filename: string
  size_bytes: number
  duration_s: number | null
  media_deleted: boolean
  status: SessionStatus
  stage: string | null
  progress: number
  error_code: string | null
  error_message: string | null
  warnings: string[]
  created_at: string
  completed_at: string | null
}

export interface Word {
  text: string
  start: number
  end: number
  probability: number
}

export interface Segment {
  id: number
  start: number
  end: number
  text: string
  words: Word[]
}

export interface Transcript {
  language: string
  duration_s: number
  model: string
  segments: Segment[]
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { code?: string; message?: string }
    return new ApiError(res.status, body.code ?? 'error', body.message ?? res.statusText)
  } catch {
    return new ApiError(res.status, 'error', res.statusText || 'Request failed')
  }
}

let onUnauthorized: (() => void) | null = null

/** The auth context registers this so an expired session sends the user to sign in. */
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { credentials: 'include', ...init })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the SmartSpeaking server. Is it running?')
  }
  if (!res.ok) {
    const err = await parseError(res)
    if (res.status === 401 && !path.startsWith('/api/auth/')) onUnauthorized?.()
    throw err
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  listSessions: () => request<PracticeSession[]>('/api/sessions'),
  getSession: (id: string) => request<PracticeSession>(`/api/sessions/${id}`),
  getTranscript: (id: string) => request<Transcript>(`/api/sessions/${id}/results/transcript`),
  retry: (id: string) => request<PracticeSession>(`/api/sessions/${id}/retry`, { method: 'POST' }),
  deleteSession: (id: string) => request<void>(`/api/sessions/${id}`, { method: 'DELETE' }),
  mediaUrl: (id: string) => `/api/sessions/${id}/media`,
}

export interface UploadOptions {
  file: Blob
  filename: string
  title?: string
  source?: 'upload' | 'live'
  mode?: SessionMode
  targetSeconds?: number
  scriptText?: string
  language?: string
  modelPreset?: ModelPreset
  onProgress?: (fraction: number) => void
  signal?: AbortSignal
}

// XHR instead of fetch because fetch has no upload progress events.
export function uploadSession(opts: UploadOptions): Promise<PracticeSession> {
  const form = new FormData()
  form.append('file', opts.file, opts.filename)
  if (opts.title) form.append('title', opts.title)
  form.append('source', opts.source ?? 'upload')
  form.append('mode', opts.mode ?? 'free_talk')
  if (opts.targetSeconds) form.append('target_seconds', String(opts.targetSeconds))
  if (opts.scriptText) form.append('script_text', opts.scriptText)
  form.append('language', opts.language ?? 'en')
  form.append('model_preset', opts.modelPreset ?? 'balanced')

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/sessions')
    xhr.withCredentials = true
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) opts.onProgress?.(e.loaded / e.total)
    }
    xhr.onload = () => {
      const body = xhr.response as Record<string, string> | null
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as unknown as PracticeSession)
      else reject(new ApiError(xhr.status, body?.code ?? 'error', body?.message ?? 'Upload failed'))
    }
    xhr.onerror = () => reject(new ApiError(0, 'network', 'The upload was interrupted.'))
    xhr.onabort = () => reject(new ApiError(0, 'aborted', 'Upload cancelled.'))
    opts.signal?.addEventListener('abort', () => xhr.abort())
    xhr.send(form)
  })
}

// ---- Report (Phase 2) ----

export type Category =
  | 'voice'
  | 'pacing'
  | 'language'
  | 'pronunciation'
  | 'eye_contact'
  | 'posture'
  | 'body_language'

export interface RuleResult {
  id: string
  metric: string
  value: number
  penalty: number
  max_penalty: number
  message: string
}

export interface CategoryScore {
  category: Category
  status: 'scored' | 'not_scored'
  score: number | null
  reason: string | null
  rules: RuleResult[]
}

export interface Issue {
  id: string
  category: Category
  kind: string
  start: number
  end: number
  severity: 'info' | 'minor' | 'major'
  message: string
  text: string | null
}

export interface Report {
  generated_by: 'template' | 'llm'
  llm_model: string | null
  llm_error: string | null
  summary: string | null
  clarity: { feedback: string; examples: { original: string; suggestion: string }[] } | null
  overall: number | null
  scores: { overall: number | null; categories: Record<Category, CategoryScore> }
  strengths: string[]
  gaps: { category: Category; rule_id: string; title: string; message: string; penalty: number }[]
  top_fixes: { title: string; how: string; drill: string }[]
  sections: {
    category: Category
    score: number | null
    status: 'scored' | 'not_scored'
    what_happened: string[]
    why_it_matters: string
    how_to_fix: string[]
    drill: string | null
  }[]
  issues: Issue[]
  highlights: Record<string, string | number | null>
}

export interface TimePoint {
  t: number
  value: number | null
}

export interface PacingResult {
  wpm_overall: number
  wpm_series: TimePoint[]
  pauses: { start: number; end: number; duration: number; kind: 'effective' | 'awkward' | 'hesitation' }[]
}

export interface VoiceResult {
  pitch_series: TimePoint[]
  volume_series: TimePoint[]
  tone: string
  tone_reasons: string[]
}

export interface EmotionPoint {
  t: number
  emotion: string
  share: number
}

export interface BodyResult {
  eye_contact_series: TimePoint[]
  eye_contact_ratio: number | null
  emotions: Record<string, number>
  emotion_timeline: EmotionPoint[]
}

export interface VoiceEmotionResult {
  emotions: Record<string, number>
  dominant: string
  timeline: EmotionPoint[]
}

const optional = <T,>(p: Promise<T>): Promise<T | null> => p.catch(() => null)

export const reportApi = {
  getReport: (id: string) => request<Report>(`/api/sessions/${id}/results/report`),
  getPacing: (id: string) => request<PacingResult>(`/api/sessions/${id}/results/pacing`),
  getVoice: (id: string) => optional(request<VoiceResult>(`/api/sessions/${id}/results/voice`)),
  getBody: (id: string) => optional(request<BodyResult>(`/api/sessions/${id}/results/body`)),
  getVoiceEmotion: (id: string) => optional(request<VoiceEmotionResult>(`/api/sessions/${id}/results/voice_emotion`)),
  pdfUrl: (id: string) => `/api/sessions/${id}/report.pdf`,
}

// ---- Accounts and progress (Phase 6) ----

export interface UserSettings {
  language: 'en'
  model_preset: ModelPreset
  auto_delete_video: boolean
}

export interface User {
  id: string
  email: string
  name: string | null
  settings: UserSettings
  created_at: string
}

export interface SessionScores {
  id: string
  title: string
  created_at: string
  duration_s: number | null
  overall: number | null
  categories: Partial<Record<Category, number | null>>
}

export interface Progress {
  sessions: SessionScores[]
  count: number
  average: number | null
  best: number | null
  latest: number | null
  change: number | null
  category_change: Partial<Record<Category, number | null>>
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const authApi = {
  me: () => request<User>('/api/auth/me'),
  register: (email: string, password: string, name?: string) =>
    request<User>('/api/auth/register', json('POST', { email, password, name: name || null })),
  login: (email: string, password: string) => request<User>('/api/auth/login', json('POST', { email, password })),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  updateSettings: (settings: UserSettings) => request<User>('/api/auth/me/settings', json('PUT', settings)),
  changePassword: (current_password: string, new_password: string) =>
    request<void>('/api/auth/me/password', json('POST', { current_password, new_password })),
  deleteAccount: (password: string) => request<void>('/api/auth/me', json('DELETE', { password })),
  progress: () => request<Progress>('/api/progress'),
}
