# SmartSpeaking

A free, local AI public speaking coach. Record yourself live or upload a video
of a talk, pitch or presentation, and get a detailed report on your voice,
pacing, filler words, language, pronunciation, eye contact, posture and body
language, with timestamps for every issue and concrete drills to fix them.

Everything runs on your own machine with open-source models. No recording,
transcript or metric is ever sent to a cloud service.

## Features

- **Live mode:** webcam and microphone in the browser, with tracking boxes and
  a skeleton around your face, hands and upper body, plus live words per
  minute, filler counter, eye contact and posture hints. The recording is then
  analyzed in full.
- **Upload mode:** mp4, webm or mov up to 15 minutes, with progress bars for
  the upload and the analysis.
- **Report:** overall and category scores (radar chart), 3 strengths and 3
  gaps, a per-category breakdown (what happened, why it matters, how to fix
  it, a practice drill), your top 3 fixes, sentence-clarity rewrites, charts
  of pace, pitch, volume and eye contact over time, a mistakes timeline that
  jumps the video, and a transcript with fillers, pauses and unclear words
  highlighted.
- **PDF export** of the full report.
- **Practice modes:** free talk, timed pitch (1, 3 or 5 minutes), and
  compare-to-script.
- **Accounts and progress:** email and password sign-in, a dashboard that
  tracks your scores across sessions, settings (language, speed vs accuracy,
  auto-delete video), delete a session or your whole account.

## Quick start (Docker)

Requirements: Docker (OrbStack or Docker Desktop) and about 15 GB of free disk.

```bash
cp .env.example .env
docker compose up --build
```

Then open http://localhost:8080 and create an account. The first account
created also takes over any recordings made before accounts existed.

**The AI coach (Ollama).** On a Mac, install [Ollama](https://ollama.com)
natively so it can use the GPU, then pull the model once:

```bash
ollama pull qwen2.5:7b
```

On a Linux server, run Ollama in Docker instead:

```bash
docker compose --profile ollama up --build
```

Then set `SS_OLLAMA_URL=http://ollama:11434` in `.env` and pull the model
inside the container. If Ollama is not running, reports still work, using
built-in coaching text.

**First run:** Whisper, the phoneme model and the MediaPipe models download
once (about 3 GB in total, see [Models](#models)), so the first analysis is
slower. After that the app works offline.

## Native development

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20+,
ffmpeg, espeak-ng and, for PDF export, Pango. On a Mac:

```bash
brew install uv node ffmpeg espeak-ng pango
```

```bash
make api      # FastAPI on :8000 (starts Postgres and Redis in Docker)
make worker   # analysis worker
make web      # Vite dev server on :5173
```

## Tests

```bash
make test     # backend unit tests, frontend unit tests, frontend build
make e2e      # a real clip through the API, Whisper, pronunciation and body tracking
make lint     # ruff, mypy (strict), oxlint
```

## Architecture

```
          ┌──────────────────────── Browser (React + Vite + Tailwind) ───────────────────────┐
          │  Live: MediaPipe pose/face/hand tracking in the page, MediaRecorder, mic stream  │
          │  Upload, report, charts, video timeline, dashboard, settings                     │
          └───────────────┬───────────────────────────────────────────────┬─────────────────┘
                          │ REST (cookie session)                          │ WebSocket (16 kHz PCM)
                          ▼                                                ▼
                 ┌──────────────────┐   job    ┌───────┐   job   ┌──────────────────────────┐
                 │  FastAPI (api)   │ ───────► │ Redis │ ──────► │  Worker (RQ)             │
                 │  auth, sessions, │          │  (RQ) │         │  1 preprocess (ffmpeg)   │
                 │  PDF, live ASR   │          └───────┘         │  2 transcribe (Whisper)  │
                 └────────┬─────────┘                            │  3 pacing + voice        │
                          │                                      │  4 language              │
                          ▼                                      │  5 pronunciation         │
           ┌──────────────────────────────┐                      │  6 body language         │
           │ PostgreSQL + media volume    │ ◄─────────────────── │  7 scoring (YAML rules)  │
           │ users, sessions, results     │                      │  8 report + AI coaching ─┼──► Ollama
           └──────────────────────────────┘                      └──────────────────────────┘   (metrics only)
```

More detail: [docs/architecture.md](docs/architecture.md). Scoring rules:
[docs/scoring.md](docs/scoring.md). Privacy: [docs/privacy.md](docs/privacy.md).

## Models

All models are free and open. Details and licenses: [docs/models.md](docs/models.md).

| Model | Purpose | Size |
| --- | --- | --- |
| faster-whisper tiny | Live words per minute and filler counter | 75 MB |
| faster-whisper base / small / large-v3-turbo | Transcript with word timestamps (Fast / Balanced / Accurate) | 145 MB / 480 MB / 1.6 GB |
| facebook/wav2vec2-lv-60-espeak-cv-ft | Phoneme recognition for the pronunciation estimate | 1.26 GB |
| espeak-ng (via phonemizer) | Expected pronunciation of each word | system package |
| MediaPipe Pose Landmarker (full on the server, lite in the browser) | Posture, swaying, arms | 9 MB / 5.5 MB |
| MediaPipe Face Landmarker | Eye contact (head pose, iris, eye-look), expression | 3.6 MB |
| MediaPipe Hand Landmarker | Gestures, open hands, fidgeting, face touches | 7.5 MB |
| qwen2.5:7b via Ollama (default; llama3.1:8b also works) | Coaching text and sentence clarity, from metrics only | 4.7 GB |

## Hardware requirements

| | Minimum | Recommended |
| --- | --- | --- |
| CPU | 4 cores | 8 cores (Apple M-series or recent x86) |
| RAM | 8 GB (use the Fast preset and `qwen2.5:3b`) | 16 GB |
| Disk | 15 GB | 25 GB |
| GPU | not needed | NVIDIA on Linux is used automatically for Whisper and wav2vec2 |

Measured on an Apple M5 MacBook Air (16 GB, CPU only in Docker, Ollama on the
Mac GPU): a 45 second clip takes about 1.5 minutes end to end, most of it the
AI coach (about 45 seconds).

## Limitations

- **Scores are estimates.** Pronunciation compares your sounds with a standard
  US English reference, so accents can be flagged. Eye contact, posture and
  body language come from webcam tracking, which glasses, lighting and camera
  angle affect. The app says so next to each score.
- **Eye contact** means looking at the camera. Looking at your screen, just
  below a webcam, can count as looking away. Live mode calibrates for this;
  uploads cannot.
- **Filler words** depend on Whisper writing them down. The transcription
  prompt pushes it to keep them, but some may still be dropped.
- **The tone label** (confident, nervous, flat, rushed) is a transparent
  heuristic, not a trained emotion model.
- **English only for now.** The code is built for more languages: add a
  lexicon in `backend/app/pipeline/lexicons/` and a voice in the pronunciation step.
- **Hands out of frame:** with a laptop webcam your hands are often not
  visible, so gesture scores have little to work with.
- **Docker on a Mac** has no GPU access, so run Ollama natively for speed.
- On x86 Linux, `pip install torch` pulls the CUDA build by default, which
  makes the backend image large.

## License

Code: see the repository. Model licenses: [docs/models.md](docs/models.md).
