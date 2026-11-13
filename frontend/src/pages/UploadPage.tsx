import { useRef, useState, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadSession, type Lang, type ModelPreset, type SessionMode } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ProgressBar } from '../components/ProgressBar'
import { useI18n } from '../i18n'
import { LANGS, type MessageKey } from '../i18n/core'
import { errorText } from '../lib/errors'
import { formatBytes, formatTime } from '../lib/format'
import { checkDuration, checkExtension, checkSize, MIN_SECONDS, readDuration } from '../lib/validateFile'

const PRESETS: ModelPreset[] = ['fast', 'balanced', 'accurate']

export function UploadPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useI18n()
  const [speechLang, setSpeechLang] = useState<Lang>(user?.settings.language ?? 'en')
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [duration, setDuration] = useState<number | null>(null)
  const [title, setTitle] = useState('')
  const [mode, setMode] = useState<SessionMode>('free_talk')
  const [target, setTarget] = useState(180)
  const [script, setScript] = useState('')
  const [preset, setPreset] = useState<ModelPreset>(user?.settings.model_preset ?? 'balanced')
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [dragging, setDragging] = useState(false)

  async function pick(f: File | undefined) {
    if (!f) return
    setError(null)
    const problem = checkExtension(f.name) ?? checkSize(f.size)
    if (problem) {
      setFile(null)
      setError(t(problem))
      return
    }
    const d = await readDuration(f)
    const durationProblem: MessageKey | null = checkDuration(d)
    if (durationProblem) {
      setFile(null)
      setError(t(durationProblem, { n: MIN_SECONDS }))
      return
    }
    setFile(f)
    setDuration(d)
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ''))
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    void pick(e.dataTransfer.files[0])
  }

  async function submit() {
    if (!file) return
    if (mode === 'script' && !script.trim()) {
      setError(t('upload.err_script'))
      return
    }
    setUploading(true)
    setError(null)
    setProgress(0)
    abortRef.current = new AbortController()
    try {
      const session = await uploadSession({
        file,
        filename: file.name,
        title,
        mode,
        targetSeconds: mode === 'timed_pitch' ? target : undefined,
        scriptText: mode === 'script' ? script : undefined,
        modelPreset: preset,
        language: speechLang,
        onProgress: setProgress,
        signal: abortRef.current.signal,
      })
      navigate(`/sessions/${session.id}`)
    } catch (e) {
      setError(errorText(e, t, 'err.upload_failed'))
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold">{t('upload.title')}</h1>
      <p className="mt-1 text-slate-600 dark:text-slate-400">{t('upload.subtitle')}</p>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`mt-6 cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragging
            ? 'border-brand-500 bg-brand-50 dark:bg-slate-900'
            : 'border-slate-300 bg-white hover:border-brand-500 dark:border-slate-700 dark:bg-slate-900'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov,.m4v"
          className="hidden"
          onChange={(e) => void pick(e.target.files?.[0])}
        />
        {file ? (
          <div>
            <p className="font-medium">{file.name}</p>
            <p className="mt-1 text-sm text-slate-500">
              {formatBytes(file.size)}
              {duration !== null && ` · ${formatTime(duration)}`} · {t('upload.click_change')}
            </p>
          </div>
        ) : (
          <div>
            <p className="font-medium">{t('upload.drop')}</p>
            <p className="mt-1 text-sm text-slate-500">{t('upload.stays')}</p>
          </div>
        )}
      </div>

      {file && (
        <div className="mt-6 space-y-5 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <label className="block">
            <span className="text-sm font-medium">{t('upload.field_title')}</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              className="mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
            />
          </label>

          <fieldset>
            <legend className="text-sm font-medium">{t('upload.mode')}</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {(['free_talk', 'timed_pitch', 'script'] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMode(value)}
                  className={`rounded-md border px-3 py-1.5 text-sm ${
                    mode === value
                      ? 'border-brand-600 bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-white'
                      : 'border-slate-300 dark:border-slate-700'
                  }`}
                >
                  {t(`mode.${value}`)}
                </button>
              ))}
            </div>
            {mode === 'timed_pitch' && (
              <div className="mt-3 flex gap-2">
                {[60, 180, 300].map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setTarget(s)}
                    className={`rounded-md border px-3 py-1 text-sm ${
                      target === s ? 'border-brand-600 text-brand-700 dark:text-white' : 'border-slate-300 dark:border-slate-700'
                    }`}
                  >
                    {t('mode.minutes', { n: s / 60 })}
                  </button>
                ))}
              </div>
            )}
            {mode === 'script' && (
              <textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                rows={6}
                placeholder={t('upload.script_placeholder')}
                dir="auto"
                className="mt-3 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
              />
            )}
          </fieldset>

          <fieldset>
            <legend className="text-sm font-medium">{t('upload.speed')}</legend>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPreset(p)}
                  className={`rounded-md border px-3 py-2 text-start text-sm ${
                    preset === p
                      ? 'border-brand-600 bg-brand-50 dark:bg-slate-800'
                      : 'border-slate-300 dark:border-slate-700'
                  }`}
                >
                  <span className="block font-medium">{t(`preset.${p}`)}</span>
                  <span className="block text-xs text-slate-500">{t(`preset.${p}_hint`)}</span>
                </button>
              ))}
            </div>
          </fieldset>

          <label className="block">
            <span className="text-sm font-medium">{t('upload.speech_language')}</span>
            <select
              value={speechLang}
              onChange={(e) => setSpeechLang(e.target.value as Lang)}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
            >
              {LANGS.map((l) => (
                <option key={l} value={l} lang={l}>
                  {t(`lang.${l}`)}
                </option>
              ))}
            </select>
          </label>

          {uploading ? (
            <div className="space-y-3">
              <ProgressBar value={progress} label={t('upload.uploading')} />
              <button
                type="button"
                onClick={() => abortRef.current?.abort()}
                className="text-sm text-slate-500 hover:text-slate-800"
              >
                {t('common.cancel')}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => void submit()}
              className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700"
            >
              {t('upload.submit')}
            </button>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}
    </div>
  )
}
