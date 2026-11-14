import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadSession, type Lang, type Prompt, type SessionMode } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ProgressBar } from '../components/ProgressBar'
import { LiveAudioStream, type LiveStats } from '../live/audioStream'
import type { Baseline } from '../live/bodyRules'
import { drawFrame, type FrameChecks } from '../live/overlay'
import { BodyTracker } from '../live/tracker'
import { extensionFor, Recording } from '../live/recorder'
import { useI18n } from '../i18n'
import { LANGS, type MessageKey } from '../i18n/core'
import { errorText } from '../lib/errors'
import { formatTime } from '../lib/format'
import { PromptPicker } from '../components/PromptPicker'
import { isPromptMode, lightAt, MODE_TARGETS, PREP_SECONDS, randomPrompt, timingLights } from '../lib/prompts'

type Phase = 'idle' | 'starting' | 'prep' | 'recording' | 'uploading'

const LIVE_MODES: SessionMode[] = ['free_talk', 'timed_pitch', 'impromptu', 'elevator_pitch', 'interview', 'table_topics']
// Modes that stop by themselves at the target; the others run a little over, as in real life.
const HARD_STOP: SessionMode[] = ['timed_pitch', 'elevator_pitch']
const OVERRUN_S = 30

const CALIBRATION_S = 3
const EYE_WINDOW = 150 // frames in the rolling eye-contact window (about 10 s)

function wpmTone(wpm: number | null): string {
  if (wpm === null) return 'text-slate-400'
  if (wpm > 170 || wpm < 110) return 'text-amber-500'
  return 'text-emerald-500'
}

function wpmHint(wpm: number | null): MessageKey {
  if (wpm === null) return 'live.pace_start'
  if (wpm > 170) return 'live.pace_fast'
  if (wpm < 110) return 'live.pace_slow'
  return 'live.pace_good'
}

export function LivePage() {
  const navigate = useNavigate()
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const tRef = useRef(t)
  tRef.current = t
  const [speechLang, setSpeechLang] = useState<Lang>(user?.settings.language ?? lang)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioRef = useRef<LiveAudioStream | null>(null)
  const recRef = useRef<Recording | null>(null)
  const startedAt = useRef(0)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const trackerRef = useRef<BodyTracker | null>(null)
  const loopRef = useRef<number | null>(null)
  const baselineRef = useRef<Baseline | null>(null)
  const calib = useRef<{ yaw: number[]; pitch: number[]; down: number[] }>({ yaw: [], pitch: [], down: [] })
  const eyeHistory = useRef<boolean[]>([])
  const eyeTotals = useRef({ yes: 0, all: 0 })
  const emotionCounts = useRef<Record<string, number>>({})
  const [emotionMix, setEmotionMix] = useState<[string, number][]>([])
  const [checks, setChecks] = useState<FrameChecks | null>(null)
  const [eyeRecent, setEyeRecent] = useState<number | null>(null)
  const [calibrating, setCalibrating] = useState(false)
  const [overlayOn, setOverlayOn] = useState(true)
  const overlayOnRef = useRef(true)
  const [trackerNote, setTrackerNote] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [stats, setStats] = useState<LiveStats | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [mode, setMode] = useState<SessionMode>('free_talk')
  const [target, setTarget] = useState<number | null>(null)
  const [prompt, setPrompt] = useState('')
  const promptsRef = useRef<Prompt[]>([])
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [prepLeft, setPrepLeft] = useState(0)
  const skipPrep = useRef<(() => void) | null>(null)
  const [title, setTitle] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)

  // Release the camera and models when leaving the page.
  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      if (loopRef.current) cancelAnimationFrame(loopRef.current)
      trackerRef.current?.close()
    },
    [],
  )

  useEffect(() => {
    overlayOnRef.current = overlayOn
    if (!overlayOn) {
      const c = canvasRef.current
      c?.getContext('2d')?.clearRect(0, 0, c.width, c.height)
    }
  }, [overlayOn])

  function median(xs: number[]): number {
    const s = [...xs].sort((a, b) => a - b)
    return s.length ? s[Math.floor(s.length / 2)] : 0
  }

  function startTracking() {
    const video = videoRef.current
    const canvas = canvasRef.current
    const tracker = trackerRef.current
    if (!video || !canvas || !tracker) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    baselineRef.current = null
    calib.current = { yaw: [], pitch: [], down: [] }
    eyeHistory.current = []
    eyeTotals.current = { yes: 0, all: 0 }
    emotionCounts.current = {}
    setEmotionMix([])
    setCalibrating(true)
    const t0 = performance.now()
    let lastVideoTime = -1
    let lastUi = 0

    const tick = () => {
      loopRef.current = requestAnimationFrame(tick)
      if (video.readyState < 2 || video.currentTime === lastVideoTime) return
      lastVideoTime = video.currentTime
      if (canvas.width !== video.videoWidth) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
      }
      const now = performance.now()
      let result
      try {
        result = tracker.detect(video, now)
      } catch {
        return
      }
      const aspect = video.videoWidth / Math.max(1, video.videoHeight)
      // Checks always run; the drawing is wiped when the overlay is switched off.
      const frame = drawFrame(ctx, result, aspect, baselineRef.current, tRef.current)
      if (!overlayOnRef.current) ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Calibration: assume the speaker looks at the camera for the first seconds.
      if (!baselineRef.current && frame.face) {
        calib.current.yaw.push(frame.face.yaw)
        calib.current.pitch.push(frame.face.pitch)
        calib.current.down.push(frame.face.down)
        if ((now - t0) / 1000 >= CALIBRATION_S) {
          baselineRef.current = {
            yaw: median(calib.current.yaw),
            pitch: median(calib.current.pitch),
            down: median(calib.current.down),
          }
          setCalibrating(false)
        }
      } else if (baselineRef.current) {
        const eye = frame.face?.eyeContact ?? false
        eyeHistory.current.push(eye)
        if (eyeHistory.current.length > EYE_WINDOW) eyeHistory.current.shift()
        eyeTotals.current.all++
        if (eye) eyeTotals.current.yes++
        if (frame.face) emotionCounts.current[frame.face.emotion] = (emotionCounts.current[frame.face.emotion] ?? 0) + 1
      }
      if (now - lastUi > 250) {
        lastUi = now
        setChecks(frame)
        const h = eyeHistory.current
        setEyeRecent(h.length >= 10 ? h.filter(Boolean).length / h.length : null)
        const total = Object.values(emotionCounts.current).reduce((a, b) => a + b, 0)
        if (total) {
          setEmotionMix(
            Object.entries(emotionCounts.current)
              .map(([k, v]) => [k, v / total] as [string, number])
              .sort((a, b) => b[1] - a[1])
              .slice(0, 3),
          )
        }
      }
    }
    loopRef.current = requestAnimationFrame(tick)
  }

  useEffect(() => {
    if (phase !== 'recording') return
    const id = window.setInterval(() => setElapsed((Date.now() - startedAt.current) / 1000), 250)
    return () => window.clearInterval(id)
  }, [phase])

  // Stop automatically at the target (or a little after it for open-ended modes).
  useEffect(() => {
    if (phase !== 'recording' || target === null) return
    const limit = HARD_STOP.includes(mode) ? target : mode === 'interview' ? Infinity : target + OVERRUN_S
    if (elapsed >= limit) void stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsed, phase, target, mode])

  // A new spoken language gets a prompt in that language.
  useEffect(() => {
    if (isPromptMode(mode) && phase === 'idle') setPrompt(randomPrompt(mode, speechLang))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speechLang])

  function chooseMode(m: SessionMode) {
    setMode(m)
    setTarget(MODE_TARGETS[m]?.[0] ?? null)
    setPrompt(isPromptMode(m) ? randomPrompt(m, speechLang) : '')
  }

  /** Counts down the thinking time; resolves early if the speaker skips it. */
  function prepCountdown(seconds: number): Promise<void> {
    return new Promise((resolve) => {
      let left = seconds
      setPrepLeft(left)
      setPhase('prep')
      const id = window.setInterval(() => {
        left -= 1
        setPrepLeft(left)
        if (left <= 0) done()
      }, 1000)
      const done = () => {
        window.clearInterval(id)
        skipPrep.current = null
        resolve()
      }
      skipPrep.current = done
    })
  }

  function nextQuestion() {
    if (mode !== 'interview') return
    const asked = new Set(promptsRef.current.map((p) => p.text))
    let q = randomPrompt('interview', speechLang, prompt)
    for (let i = 0; i < 10 && asked.has(q); i++) q = randomPrompt('interview', speechLang, q)
    setPrompt(q)
    promptsRef.current = [...promptsRef.current, { t: Math.round((Date.now() - startedAt.current) / 100) / 10, text: q }]
    setPrompts(promptsRef.current)
  }

  async function start() {
    setError(null)
    setNotice(null)
    setStats(null)
    setPhase('starting')
    const audioCtx = LiveAudioStream.createContext() // must happen before the first await
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        // Raw microphone: noise suppression and auto gain cut quiet speech and distort
        // the volume metrics. Echo cancellation is not needed because nothing plays back.
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play().catch(() => undefined)
      }
      setTrackerNote(null)
      const trackerReady = (trackerRef.current ? Promise.resolve(trackerRef.current) : BodyTracker.create())
        .then((t) => {
          trackerRef.current = t
          startTracking()
        })
        .catch(() => setTrackerNote(t('live.tracker_failed')))
      const audio = new LiveAudioStream({
        onStats: setStats,
        onError: (m) => setNotice(m === 'unavailable' ? t('live.feedback_unavailable') : t('live.model_failed')),
      })
      audioRef.current = audio
      const prep = isPromptMode(mode) ? (PREP_SECONDS[mode] ?? 0) : 0
      if (prep > 0) await prepCountdown(prep)
      await audio.start(stream, audioCtx, speechLang).catch(() => setNotice(t('live.feedback_unavailable')))
      const rec = new Recording(stream)
      recRef.current = rec
      rec.start()
      startedAt.current = Date.now()
      promptsRef.current = prompt ? [{ t: 0, text: prompt }] : []
      setPrompts(promptsRef.current)
      setElapsed(0)
      setPhase('recording')
      void trackerReady
    } catch (e) {
      const name = e instanceof DOMException ? e.name : ''
      setError(
        name === 'NotAllowedError'
          ? t('live.blocked')
          : name === 'NotFoundError'
            ? t('live.no_device')
            : t('live.start_failed'),
      )
      void audioCtx.close()
      setPhase('idle')
    }
  }

  async function stop() {
    if (phase !== 'recording') return
    setPhase('uploading')
    const rec = recRef.current
    const blob = rec ? await rec.stop() : null
    await audioRef.current?.stop()
    if (loopRef.current) cancelAnimationFrame(loopRef.current)
    loopRef.current = null
    canvasRef.current?.getContext('2d')?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    if (videoRef.current) videoRef.current.srcObject = null
    if (!blob || blob.size === 0 || !rec) {
      setError(t('live.nothing_recorded'))
      setPhase('idle')
      return
    }
    try {
      const name = title.trim() || t('live.default_title', { date: new Date().toLocaleString() })
      const session = await uploadSession({
        file: blob,
        filename: `live${extensionFor(rec.mimeType)}`,
        title: name,
        source: 'live',
        mode,
        targetSeconds: target ?? undefined,
        prompts: promptsRef.current,
        language: speechLang,
        onProgress: setUploadProgress,
      })
      navigate(`/sessions/${session.id}`)
    } catch (e) {
      setError(errorText(e, t, 'err.upload_failed'))
      setPhase('idle')
    }
  }

  const wpm = stats?.wpm_recent ?? null
  const remaining = target !== null && mode !== 'interview' ? Math.max(0, target - elapsed) : null
  const light = phase === 'recording' ? lightAt(timingLights(mode, target), elapsed) : 'none'
  const LIGHT_CLASS = { none: '', green: 'bg-emerald-500', amber: 'bg-amber-400', red: 'bg-red-500' } as const

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{t('live.title')}</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">{t('live.subtitle')}</p>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_18rem]">
        {/* Fixed 16:9 box: video and overlay share exactly the same area and cropping,
            so the boxes stay on the body even when the side panel is taller. */}
        <div className="space-y-4">
          <div dir="ltr" className="relative aspect-video overflow-hidden rounded-xl bg-slate-900">
            <video ref={videoRef} muted playsInline className="absolute inset-0 h-full w-full -scale-x-100 object-cover" />
            <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full object-cover" />
            {phase === 'recording' && calibrating && (
              <div className="absolute inset-x-0 bottom-4 mx-auto w-fit rounded-full bg-black/70 px-4 py-2 text-sm text-white">
                {t('live.look_at_camera')}
              </div>
            )}
            {phase === 'idle' && (
              <div className="absolute inset-0 grid place-items-center text-slate-300">{t('live.camera_off')}</div>
            )}
            {phase === 'prep' && (
              <div className="absolute inset-0 grid place-items-center bg-slate-950/70 p-6 text-center text-white">
                <div>
                  <p className="text-sm uppercase tracking-widest text-slate-300">{t('modes.prep')}</p>
                  <p className="mt-2 text-6xl font-semibold tabular-nums">{prepLeft}</p>
                  <p dir="auto" className="mx-auto mt-4 max-w-lg text-xl">{prompt}</p>
                  <button
                    type="button"
                    onClick={() => skipPrep.current?.()}
                    className="mt-6 rounded-md bg-white px-4 py-2 text-sm font-medium text-slate-900"
                  >
                    {t('modes.start_now')}
                  </button>
                </div>
              </div>
            )}
            {phase === 'recording' && prompt && (
              <div dir="auto" className="absolute inset-x-3 bottom-3 rounded-lg bg-black/65 px-4 py-2 text-center text-white">
                {prompt}
              </div>
            )}
            {light !== 'none' && (
              <div
                className={`absolute right-3 top-3 h-8 w-8 rounded-full ring-4 ring-white/40 ${LIGHT_CLASS[light]}`}
                title={t(`modes.light_${light}`)}
                aria-label={t(`modes.light_${light}`)}
              />
            )}
            {phase === 'recording' && (
              <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-sm text-white">
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
                {remaining !== null ? t('live.left', { time: formatTime(remaining) }) : formatTime(elapsed)}
              </div>
            )}
          </div>

        {phase === 'idle' && (
          <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <label className="min-w-56 flex-1">
              <span className="text-sm font-medium">{t('live.title_optional')}</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              />
            </label>
            <div className="w-full">
              <span className="text-sm font-medium">{t('upload.mode')}</span>
              <div className="mt-1 flex flex-wrap gap-2">
                {LIVE_MODES.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => chooseMode(m)}
                    title={t(`modes.${m}_hint`)}
                    className={`rounded-md border px-3 py-2 text-sm ${
                      mode === m ? 'border-brand-600 bg-brand-50 dark:bg-slate-800' : 'border-slate-300 dark:border-slate-700'
                    }`}
                  >
                    {t(`mode.${m}`)}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-xs text-slate-500">{t(`modes.${mode}_hint`)}</p>
            </div>
            {(MODE_TARGETS[mode]?.length ?? 0) > 1 && (
              <div>
                <span className="text-sm font-medium">{t('live.length')}</span>
                <div className="mt-1 flex gap-2">
                  {MODE_TARGETS[mode]!.map((sec) => (
                    <button
                      key={sec}
                      type="button"
                      onClick={() => setTarget(sec)}
                      className={`rounded-md border px-3 py-2 text-sm ${
                        target === sec ? 'border-brand-600 bg-brand-50 dark:bg-slate-800' : 'border-slate-300 dark:border-slate-700'
                      }`}
                    >
                      {sec < 60 ? t('common.seconds', { n: sec }) : t('mode.minutes', { n: sec / 60 })}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {isPromptMode(mode) && (
              <PromptPicker mode={mode} lang={speechLang} value={prompt} onChange={setPrompt} className="w-full" />
            )}
            <label>
              <span className="text-sm font-medium">{t('live.speech_language')}</span>
              <select
                value={speechLang}
                onChange={(e) => setSpeechLang(e.target.value as Lang)}
                className="mt-1 block rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              >
                {LANGS.map((l) => (
                  <option key={l} value={l} lang={l}>
                    {t(`lang.${l}`)}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void start()}
              className="rounded-md bg-brand-600 px-5 py-2.5 font-medium text-white hover:bg-brand-700"
            >
              {t('live.start')}
            </button>
          </div>
        )}
        {phase === 'starting' && <p className="text-slate-500">{t('live.starting')}</p>}
        {phase === 'recording' && mode === 'interview' && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={nextQuestion}
              className="rounded-md border border-brand-600 px-4 py-2 text-sm font-medium text-brand-700 dark:text-white"
            >
              {t('modes.next_question')}
            </button>
            <span className="text-sm text-slate-500">{t('modes.questions_asked', { n: prompts.length })}</span>
          </div>
        )}
        {phase === 'recording' && (
          <button
            type="button"
            onClick={() => void stop()}
            className="rounded-md bg-red-600 px-5 py-2.5 font-medium text-white hover:bg-red-700"
          >
            {t('live.stop')}
          </button>
        )}
        {phase === 'uploading' && <ProgressBar value={uploadProgress} label={t('live.saving')} />}
        </div>
        <aside className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">{t('live.pace')}</p>
            <p className={`text-4xl font-semibold tabular-nums ${wpmTone(wpm)}`}>{wpm ?? '–'}</p>
            <p className="text-sm text-slate-500">{t('common.wpm')} · {t(wpmHint(wpm))}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">{t('live.fillers')}</p>
            <p className={`text-4xl font-semibold tabular-nums ${(stats?.fillers ?? 0) > 5 ? 'text-amber-500' : ''}`}>
              {stats?.fillers ?? 0}
            </p>
            <p className="truncate text-sm text-slate-500">
              {stats && Object.keys(stats.filler_counts).length
                ? Object.entries(stats.filler_counts)
                    .map(([k, v]) => `${k} ×${v}`)
                    .join(', ')
                : t('common.none_yet')}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">{t('live.eye_contact')}</p>
            <p className={`text-4xl font-semibold tabular-nums ${eyeRecent === null ? 'text-slate-400' : eyeRecent >= 0.75 ? 'text-emerald-500' : 'text-amber-500'}`}>
              {eyeRecent === null ? '–' : `${Math.round(eyeRecent * 100)}%`}
            </p>
            <p className="text-sm text-slate-500">
              {calibrating ? t('live.calibrating') : checks?.face ? t(checks.face.labelKey) : phase === 'recording' ? t('live.no_face') : t('live.last_10s')}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">{t('live.posture')}</p>
            <p className={`text-lg font-semibold ${!checks?.posture ? 'text-slate-400' : checks.posture.ok ? 'text-emerald-500' : 'text-red-500'}`}>
              {checks?.posture ? t(checks.posture.labelKey) : phase === 'recording' ? t('live.no_shoulders') : '–'}
            </p>
            <p className="text-sm text-slate-500">
              {checks ? t('live.hands_visible', { n: checks.handsVisible }) : ''}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">{t('live.expression')}</p>
            <p className="text-lg font-semibold">{checks?.face ? t(`emotion.${checks.face.emotion}`) : '–'}</p>
            <p className="text-sm text-slate-500">
              {emotionMix.length
                ? emotionMix.map(([k, v]) => `${t(`emotion.${k as 'neutral'}`)} ${Math.round(v * 100)}%`).join(' · ')
                : t('live.expression_hint')}
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <input type="checkbox" checked={overlayOn} onChange={(e) => setOverlayOn(e.target.checked)} />
            {t('live.show_boxes')}
          </label>
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">{t('live.last_heard')}</p>
            <p dir="auto" className="mt-1 min-h-10 text-slate-700 dark:text-slate-300">{stats?.last_text || '…'}</p>
          </div>
        </aside>
      </div>


      {trackerNote && <p className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">{trackerNote}</p>}
      {notice && <p className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">{notice}</p>}
      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}
    </div>
  )
}
