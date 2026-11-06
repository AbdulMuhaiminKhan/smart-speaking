import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, uploadSession } from '../api/client'
import { ProgressBar } from '../components/ProgressBar'
import { LiveAudioStream, type LiveStats } from '../live/audioStream'
import type { Baseline } from '../live/bodyRules'
import { drawFrame, type FrameChecks } from '../live/overlay'
import { BodyTracker } from '../live/tracker'
import { extensionFor, Recording } from '../live/recorder'
import { formatTime } from '../lib/format'

type Phase = 'idle' | 'starting' | 'recording' | 'uploading'

const CALIBRATION_S = 3
const EYE_WINDOW = 150 // frames in the rolling eye-contact window (about 10 s)

function wpmTone(wpm: number | null): string {
  if (wpm === null) return 'text-slate-400'
  if (wpm > 170 || wpm < 110) return 'text-amber-500'
  return 'text-emerald-500'
}

function wpmHint(wpm: number | null): string {
  if (wpm === null) return 'Start speaking'
  if (wpm > 170) return 'Slow down a little'
  if (wpm < 110) return 'You can speed up'
  return 'Good pace'
}

export function LivePage() {
  const navigate = useNavigate()
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
  const [checks, setChecks] = useState<FrameChecks | null>(null)
  const [eyeRecent, setEyeRecent] = useState<number | null>(null)
  const [calibrating, setCalibrating] = useState(false)
  const [overlayOn, setOverlayOn] = useState(true)
  const overlayOnRef = useRef(true)
  const [trackerNote, setTrackerNote] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [stats, setStats] = useState<LiveStats | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [target, setTarget] = useState<number | null>(null)
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
      const frame = drawFrame(ctx, result, aspect, baselineRef.current)
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
      }
      if (now - lastUi > 250) {
        lastUi = now
        setChecks(frame)
        const h = eyeHistory.current
        setEyeRecent(h.length >= 10 ? h.filter(Boolean).length / h.length : null)
      }
    }
    loopRef.current = requestAnimationFrame(tick)
  }

  useEffect(() => {
    if (phase !== 'recording') return
    const id = window.setInterval(() => setElapsed((Date.now() - startedAt.current) / 1000), 250)
    return () => window.clearInterval(id)
  }, [phase])

  // Timed pitch: stop automatically at the target.
  useEffect(() => {
    if (phase === 'recording' && target !== null && elapsed >= target) void stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsed, phase, target])

  async function start() {
    setError(null)
    setNotice(null)
    setStats(null)
    setPhase('starting')
    const audioCtx = LiveAudioStream.createContext() // must happen before the first await
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
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
        .catch(() => setTrackerNote('Body tracking could not start in this browser. Audio feedback still works.'))
      const audio = new LiveAudioStream({ onStats: setStats, onError: setNotice })
      audioRef.current = audio
      await audio
        .start(stream, audioCtx)
        .catch(() => setNotice('Live feedback is unavailable. Recording still works.'))
      const rec = new Recording(stream)
      recRef.current = rec
      rec.start()
      startedAt.current = Date.now()
      setElapsed(0)
      setPhase('recording')
      void trackerReady
    } catch (e) {
      const name = e instanceof DOMException ? e.name : ''
      setError(
        name === 'NotAllowedError'
          ? 'Camera or microphone access was blocked. Allow it in your browser settings and try again.'
          : name === 'NotFoundError'
            ? 'No camera or microphone was found.'
            : 'Could not start the camera and microphone.',
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
      setError('Nothing was recorded.')
      setPhase('idle')
      return
    }
    try {
      const name = title.trim() || `Live practice ${new Date().toLocaleString()}`
      const session = await uploadSession({
        file: blob,
        filename: `live${extensionFor(rec.mimeType)}`,
        title: name,
        source: 'live',
        mode: target ? 'timed_pitch' : 'free_talk',
        targetSeconds: target ?? undefined,
        onProgress: setUploadProgress,
      })
      navigate(`/sessions/${session.id}`)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Upload failed.')
      setPhase('idle')
    }
  }

  const wpm = stats?.wpm_recent ?? null
  const remaining = target !== null ? Math.max(0, target - elapsed) : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Live practice</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Speak to your camera. You get live hints now and a full report when you stop.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div className="relative overflow-hidden rounded-xl bg-slate-900">
          <video ref={videoRef} muted playsInline className="aspect-video w-full -scale-x-100 object-cover" />
          <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full object-cover" />
          {phase === 'recording' && calibrating && (
            <div className="absolute inset-x-0 bottom-4 mx-auto w-fit rounded-full bg-black/70 px-4 py-2 text-sm text-white">
              Look at the camera for a moment…
            </div>
          )}
          {phase === 'idle' && (
            <div className="absolute inset-0 grid place-items-center text-slate-300">Camera is off</div>
          )}
          {phase === 'recording' && (
            <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-sm text-white">
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
              {remaining !== null ? `${formatTime(remaining)} left` : formatTime(elapsed)}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Pace</p>
            <p className={`text-4xl font-semibold tabular-nums ${wpmTone(wpm)}`}>{wpm ?? '–'}</p>
            <p className="text-sm text-slate-500">words per minute · {wpmHint(wpm)}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Filler words</p>
            <p className={`text-4xl font-semibold tabular-nums ${(stats?.fillers ?? 0) > 5 ? 'text-amber-500' : ''}`}>
              {stats?.fillers ?? 0}
            </p>
            <p className="truncate text-sm text-slate-500">
              {stats && Object.keys(stats.filler_counts).length
                ? Object.entries(stats.filler_counts)
                    .map(([k, v]) => `${k} ×${v}`)
                    .join(', ')
                : 'None yet'}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Eye contact</p>
            <p className={`text-4xl font-semibold tabular-nums ${eyeRecent === null ? 'text-slate-400' : eyeRecent >= 0.75 ? 'text-emerald-500' : 'text-amber-500'}`}>
              {eyeRecent === null ? '–' : `${Math.round(eyeRecent * 100)}%`}
            </p>
            <p className="text-sm text-slate-500">
              {calibrating ? 'Calibrating…' : checks?.face ? checks.face.label : phase === 'recording' ? 'No face in view' : 'last 10 seconds'}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Posture</p>
            <p className={`text-lg font-semibold ${!checks?.posture ? 'text-slate-400' : checks.posture.ok ? 'text-emerald-500' : 'text-red-500'}`}>
              {checks?.posture ? checks.posture.label : phase === 'recording' ? 'Shoulders not in view' : '–'}
            </p>
            <p className="text-sm text-slate-500">
              {checks ? `${checks.handsVisible} hand${checks.handsVisible === 1 ? '' : 's'} visible` : ''}
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
            <input type="checkbox" checked={overlayOn} onChange={(e) => setOverlayOn(e.target.checked)} />
            Show tracking boxes
          </label>
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs uppercase tracking-wide text-slate-500">Last heard</p>
            <p className="mt-1 min-h-10 text-slate-700 dark:text-slate-300">{stats?.last_text || '…'}</p>
          </div>
        </aside>
      </div>

      {phase === 'idle' && (
        <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <label className="min-w-56 flex-1">
            <span className="text-sm font-medium">Title (optional)</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
            />
          </label>
          <div>
            <span className="text-sm font-medium">Length</span>
            <div className="mt-1 flex gap-2">
              {[null, 60, 180, 300].map((s) => (
                <button
                  key={String(s)}
                  type="button"
                  onClick={() => setTarget(s)}
                  className={`rounded-md border px-3 py-2 text-sm ${
                    target === s ? 'border-brand-600 bg-brand-50 dark:bg-slate-800' : 'border-slate-300 dark:border-slate-700'
                  }`}
                >
                  {s === null ? 'Free talk' : `${s / 60} min pitch`}
                </button>
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={() => void start()}
            className="rounded-md bg-brand-600 px-5 py-2.5 font-medium text-white hover:bg-brand-700"
          >
            Start recording
          </button>
        </div>
      )}
      {phase === 'starting' && <p className="text-slate-500">Starting camera and microphone…</p>}
      {phase === 'recording' && (
        <button
          type="button"
          onClick={() => void stop()}
          className="rounded-md bg-red-600 px-5 py-2.5 font-medium text-white hover:bg-red-700"
        >
          Stop and analyze
        </button>
      )}
      {phase === 'uploading' && <ProgressBar value={uploadProgress} label="Saving your recording" />}

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
