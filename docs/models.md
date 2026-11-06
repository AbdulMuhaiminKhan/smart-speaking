# Models

Every model is open source, free, and runs locally. Models download once on
first use into the `models` volume (backend) or `frontend/public/mediapipe`
(browser) and are never fetched again.

| Model | Used for | Where | Size | License |
| --- | --- | --- | --- | --- |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) tiny | Live WPM and filler counter | API, CPU | 75 MB | MIT |
| faster-whisper base / small / large-v3-turbo | Transcript (Fast / Balanced / Accurate preset) | Worker, CPU int8 or CUDA | 145 MB / 480 MB / 1.6 GB | MIT |
| [facebook/wav2vec2-lv-60-espeak-cv-ft](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) | Phoneme recognition | Worker | 1.26 GB | Apache 2.0 |
| [espeak-ng](https://github.com/espeak-ng/espeak-ng) via phonemizer | Expected phonemes per word | Worker | system package | GPL 3 (run as a separate library, not modified) |
| [superb/wav2vec2-base-superb-er](https://huggingface.co/superb/wav2vec2-base-superb-er) | Voice emotion (neutral, happy, angry, sad) | Worker | 380 MB | Apache 2.0 |
| [MediaPipe](https://ai.google.dev/edge/mediapipe) Pose Landmarker full / lite | Posture, arms, swaying | Worker (full), browser (lite) | 9 MB / 5.5 MB | Apache 2.0 |
| MediaPipe Face Landmarker | Head pose, iris, eye-look and expression blendshapes | Worker and browser | 3.6 MB | Apache 2.0 |
| MediaPipe Hand Landmarker | Gestures, open hands, fidgeting, face touches | Worker and browser | 7.5 MB | Apache 2.0 |
| [qwen2.5:7b](https://ollama.com/library/qwen2.5) (default) via Ollama | Coaching text, sentence clarity | Ollama | 4.7 GB | Apache 2.0 |
| [llama3.1:8b](https://ollama.com/library/llama3.1) (alternative) | Same | Ollama | 4.9 GB | Llama 3.1 Community License |
| qwen2.5:3b (low-RAM alternative) | Same, on 8 GB machines | Ollama | 1.9 GB | Qwen Research License |

Choose the LLM with `SS_OLLAMA_MODEL` in `.env`. Voice and pacing use no
models: Praat (parselmouth) and numpy compute pitch, volume and pauses.

## Speed vs accuracy

The Settings page picks the Whisper size for new recordings:

| Preset | Whisper model | Notes |
| --- | --- | --- |
| Fast | base | quickest, a few more transcription mistakes |
| Balanced (default) | small | good filler-word recall on CPU |
| Accurate | large-v3-turbo | best transcript, about 3 times slower on CPU |

## GPU

On Linux with an NVIDIA GPU and the CUDA build of PyTorch, Whisper and
wav2vec2 use the GPU automatically. Docker on macOS cannot use the Apple GPU,
which is why Ollama should run natively on a Mac.
