# SmartSpeaking

A local, free AI public speaking coach. Record or upload a talk and get a report on
your voice, pacing, filler words, language, pronunciation, eye contact, posture and
body language. Everything runs on your own machine with open-source models. Nothing
is sent to any cloud service.

> Status: Phase 3 of 6 (upload and live recording with tracking overlay, transcription, voice, pacing, language, eye contact, posture and body language, basic report). Scoring rules: [docs/scoring.md](docs/scoring.md).

## Quick start (Docker)

Requirements: Docker (OrbStack or Docker Desktop), about 10 GB of free disk.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080 and upload a video. The first analysis downloads the
Whisper model (about 480 MB for the default "Balanced" setting), so it takes longer.

On a Mac, install [Ollama](https://ollama.com) natively for the coaching report
(used from Phase 5). On a Linux server, run it in Docker with
`docker compose --profile ollama up`.

## Native development

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20+, ffmpeg, espeak-ng.

```bash
make api      # FastAPI on :8000 (starts Postgres and Redis in Docker)
make worker   # analysis worker
make web      # Vite dev server on :5173
```

## Tests

```bash
make test     # backend unit tests + frontend type check and build
make e2e      # real clip through the API and Whisper (downloads Whisper tiny once)
```

## Architecture

```
Browser (React)  --REST-->  FastAPI  --job-->  Redis (RQ)  --job-->  Worker
                               |                                      |
                               +-------> PostgreSQL + media folder <--+
                                                                      |
                                                    Ollama (metrics JSON only)
```

The worker runs the pipeline steps in `backend/app/pipeline/` one at a time:
preprocess (ffmpeg), transcribe (faster-whisper), and in later phases voice,
language, pronunciation, body language, scoring and the LLM report.

## Models

| Model | Purpose | Size |
| --- | --- | --- |
| faster-whisper tiny | Live words per minute and filler counter | 75 MB |
| faster-whisper base / small / large-v3-turbo | Transcript with word timestamps (Fast / Balanced / Accurate) | 145 MB / 480 MB / 1.6 GB |
| MediaPipe Pose Landmarker (full on the server, lite in the browser) | Posture, swaying, arms | 9 MB / 5.5 MB |
| MediaPipe Face Landmarker | Eye contact (head pose, iris, eye-look), expression | 3.6 MB |
| MediaPipe Hand Landmarker | Gestures, open hands, fidgeting, face touches | 7.5 MB |

More models are added in later phases; see `docs/models.md` when it lands.

## Privacy

Recordings are stored in a local Docker volume (`media`) and deleted with the
session. No analytics, no cloud APIs.
