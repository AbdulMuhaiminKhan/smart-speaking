# Architecture

SmartSpeaking is a React single-page app, a FastAPI backend, and an RQ worker
that runs the analysis pipeline. PostgreSQL stores users, sessions and
results; Redis holds the job queue; recordings live in a local folder (a
Docker volume). Ollama runs the local LLM.

## Services (docker-compose.yml)

| Service | What it does |
| --- | --- |
| `frontend` | nginx serving the built React app and proxying `/api` (including the live WebSocket) to the API |
| `api` | FastAPI: accounts, uploads, results, PDF export, live transcription WebSocket |
| `worker` | RQ worker running one analysis job at a time |
| `postgres` | users, auth sessions, practice sessions, step results (JSONB) |
| `redis` | job queue and the sign-in rate limiter |
| `ollama` | optional (`--profile ollama`), for Linux servers; on a Mac run Ollama natively |

## The analysis job

`backend/app/worker/jobs.py` runs the steps in order, saving each step's
output as an `analysis_results` row so the UI can show partial results and a
progress bar. Steps run one at a time so only one large model is in memory.

| Step | Module | Output |
| --- | --- | --- |
| 1 Preprocess | `pipeline/preprocess.py` | ffprobe checks (format, audio track, length), 16 kHz mono WAV; repairs browser webm files that have no duration |
| 2 Transcribe | `pipeline/transcribe.py` | faster-whisper transcript with word timestamps and confidence, filler-preserving prompt |
| 3 Pacing | `pipeline/pacing.py` | WPM overall and over time, pauses (effective, hesitation, awkward), timed-pitch delta |
| 4 Language | `pipeline/language.py` | fillers, hedges, repetitions, vocabulary variety, long sentences, script comparison |
| 5 Voice | `pipeline/voice.py` | pitch, volume, energy trend, monotone flag, tone label |
| 6 Pronunciation | `pipeline/pronunciation.py` | wav2vec2 phonemes aligned against espeak phonemes, unclear words |
| 7 Body | `pipeline/body.py`, `body_features.py` | MediaPipe pose, face and hands at 10 fps: eye contact, posture, gestures, fidgeting, swaying, expression |
| 8 Scoring | `pipeline/scoring.py`, `scoring_rules.yaml` | 0–100 per category and overall, from documented rules |
| 9 Report | `pipeline/report.py`, `issues.py` | strengths, gaps, fixes, sections, timestamped issues (template text) |
| 10 Coaching | `pipeline/report_llm.py` | LLM rewrite of the report, checked against the metrics; template fallback |

A problem with the input (unsupported file, no audio, too short or long, no
speech) stops the job with a clear message. A failure in an optional step
(pronunciation, body, coaching) is logged and that category is marked "not
scored" instead of failing the whole report.

## Live mode

- **In the browser:** MediaPipe Tasks Vision (served from `public/mediapipe`,
  never a CDN) tracks face, irises, pose and hands every frame and draws the
  overlay. `live/bodyRules.ts` mirrors the Python thresholds so live hints and
  the final report agree.
- **Audio:** an AudioWorklet resamples the microphone to 16 kHz and streams it
  over `/api/live/ws`. The API cuts the stream at quiet moments and transcribes
  each chunk with Whisper tiny for live WPM and filler counts. Nothing from the
  stream is stored.
- **Recording:** MediaRecorder records the camera and microphone; on stop the
  file is uploaded and analyzed like any upload.

## Accounts

Passwords are hashed with argon2id. Signing in creates a random token; the
browser gets it as an httpOnly, SameSite=Lax cookie, and only its SHA-256
hash is stored. Failed sign-ins are rate limited per email (10 per 15
minutes). Every session and result query is scoped to the signed-in user.

## Code layout

```
backend/app/
  api/        auth, sessions, progress, live WebSocket, health
  db/         SQLAlchemy models and engine
  pipeline/   one module per analysis step, lexicons/, scoring_rules.yaml
  schemas/    Pydantic models for the API and the metrics
  services/   storage, queue, auth, live transcription, charts, PDF
  templates/  report.html for the PDF
  worker/     the RQ job and worker entry point
frontend/src/
  pages/      Dashboard, Live, Upload, Sessions, Session report, Settings, sign-in
  components/ report view, charts, video timeline, transcript
  live/       tracker, overlay, body rules, audio streaming, recorder
  auth/       sign-in state and protected routes
```
