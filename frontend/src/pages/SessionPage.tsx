import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  api,
  reportApi,
  type BodyResult,
  type PacingResult,
  type PracticeSession,
  type Report,
  type Transcript,
  type VoiceEmotionResult,
  type VoiceResult,
} from '../api/client'
import { ProgressBar } from '../components/ProgressBar'
import { StatusBadge } from '../components/StatusBadge'
import { ReportView } from '../components/ReportView'
import { VideoTimeline } from '../components/VideoTimeline'
import { TranscriptLegend, TranscriptView } from '../components/TranscriptView'
import { useI18n } from '../i18n'
import { errorText } from '../lib/errors'
import { formatTime } from '../lib/format'

const POLL_MS = 1000

export function SessionPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [session, setSession] = useState<PracticeSession | null>(null)
  const [transcript, setTranscript] = useState<Transcript | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [pacing, setPacing] = useState<PacingResult | null>(null)
  const [voice, setVoice] = useState<VoiceResult | null>(null)
  const [body, setBody] = useState<BodyResult | null>(null)
  const [voiceEmotion, setVoiceEmotion] = useState<VoiceEmotionResult | null>(null)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const { t, tk, formatDate } = useI18n()

  const load = useCallback(async () => {
    try {
      const s = await api.getSession(id)
      setSession(s)
      setError(null)
      return s
    } catch (e) {
      setError(errorText(e, t, 'err.load_session'))
      return null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Poll while the job is running.
  useEffect(() => {
    let timer: number | undefined
    let cancelled = false
    const tick = async () => {
      const s = await load()
      if (cancelled) return
      if (!s || s.status === 'queued' || s.status === 'processing' || s.status === 'uploaded') {
        timer = window.setTimeout(tick, POLL_MS)
      }
    }
    void tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [load])

  useEffect(() => {
    if (session?.status === 'completed' && !transcript) {
      api.getTranscript(id).then(setTranscript).catch(() => setTranscript(null))
      reportApi.getReport(id).then(setReport).catch(() => setReport(null))
      reportApi.getPacing(id).then(setPacing).catch(() => setPacing(null))
      void reportApi.getVoice(id).then(setVoice)
      void reportApi.getBody(id).then(setBody)
      void reportApi.getVoiceEmotion(id).then(setVoiceEmotion)
    }
  }, [session?.status, id, transcript])

  const seek = (t: number) => {
    const v = videoRef.current
    if (!v) return
    v.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    v.currentTime = t
    void v.play()
  }

  async function retry() {
    setTranscript(null)
    try {
      setSession(await api.retry(id))
      // restart polling
      const poll = async () => {
        const s = await load()
        if (s && (s.status === 'queued' || s.status === 'processing')) setTimeout(poll, POLL_MS)
      }
      void poll()
    } catch (e) {
      setError(errorText(e, t, 'err.retry_failed'))
    }
  }

  async function remove() {
    if (!confirm(t('session.confirm_delete'))) return
    try {
      await api.deleteSession(id)
      navigate('/sessions')
    } catch (e) {
      setError(errorText(e, t, 'err.delete_failed'))
    }
  }

  if (error && !session) {
    return (
      <div className="text-center">
        <p className="text-red-700 dark:text-red-300">{error}</p>
        <Link to="/sessions" className="mt-4 inline-block text-brand-600">
          {t('session.back')}
        </Link>
      </div>
    )
  }
  if (!session) return <p className="text-slate-500">{t('common.loading')}</p>

  const running = session.status === 'queued' || session.status === 'processing'
  const fileWarnings = session.warnings.map((w) => w.split(': ').slice(1).join(': ') || w)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{session.title}</h1>
            <StatusBadge status={session.status} />
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {formatDate(session.created_at)}
            {session.duration_s !== null && ` · ${formatTime(session.duration_s)}`}
          </p>
        </div>
        <div className="flex gap-2">
          {session.status === 'completed' && (
            <a
              href={reportApi.pdfUrl(id)}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              {t('session.export_pdf')}
            </a>
          )}
        <button
          type="button"
          onClick={() => void remove()}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:border-red-400 hover:text-red-700 dark:border-slate-700 dark:text-slate-300"
        >
          {t('common.delete')}
        </button>
        </div>
      </div>

      {running && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <ProgressBar
            value={session.progress}
            indeterminate={session.status === 'queued'}
            label={
              session.status === 'queued'
                ? t('session.waiting')
                : tk(`stage.${session.stage ?? ''}`, t('stage.default'))
            }
          />
          <p className="mt-3 text-xs text-slate-500">
            {t('session.can_leave')}
          </p>
        </div>
      )}

      {session.status === 'failed' && (
        <div role="alert" className="rounded-xl bg-red-50 p-5 text-red-800 dark:bg-red-950 dark:text-red-200">
          <p className="font-medium">{t('session.failed_title')}</p>
          <p className="mt-1 text-sm">{session.error_message}</p>
          {session.error_code === 'internal_error' || session.error_code === 'queue_unavailable' ? (
            <button
              type="button"
              onClick={() => void retry()}
              className="mt-3 rounded-md bg-red-700 px-3 py-1.5 text-sm text-white"
            >
              {t('session.try_again')}
            </button>
          ) : (
            <Link to="/upload" className="mt-3 inline-block text-sm underline">
              {t('session.upload_other')}
            </Link>
          )}
        </div>
      )}

      {fileWarnings.length > 0 && (
        <ul className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          {fileWarnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          {session.media_deleted ? (
            <div className="grid aspect-video place-items-center rounded-xl bg-slate-100 p-6 text-center text-sm text-slate-500 dark:bg-slate-800">
              {t('session.video_deleted')}
            </div>
          ) : (
          <video
              ref={videoRef}
              src={api.mediaUrl(id)}
              controls
              playsInline
              onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              onLoadedMetadata={(e) => setDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0)}
              className="w-full rounded-xl bg-black"
            />
          )}
          {report && (
            <VideoTimeline
              issues={report.issues}
              duration={duration || session.duration_s || 0}
              currentTime={currentTime}
              onSeek={seek}
            />
          )}
        </div>
        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-1 font-semibold">{t('session.transcript')}</h2>
          {transcript ? (
            <>
              <p className="mb-2 text-xs text-slate-500">{t('session.click_word')}</p>
              <TranscriptLegend />
              <div className="max-h-[28rem] overflow-y-auto pe-2">
                <TranscriptView
                  transcript={transcript}
                  currentTime={currentTime}
                  onSeek={seek}
                  issues={report?.issues}
                  pauses={pacing?.pauses}
                />
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              {running ? t('session.transcript_pending') : t('session.no_transcript')}
            </p>
          )}
        </section>
      </div>

      {report && (
        <ReportView
          report={report}
          pacing={pacing}
          voice={voice}
          body={body}
          voiceEmotion={voiceEmotion}
          duration={duration || session.duration_s || 0}
          onSeek={seek}
        />
      )}
    </div>
  )
}
