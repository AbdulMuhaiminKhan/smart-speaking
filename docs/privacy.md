# Privacy

SmartSpeaking is built so your recordings never leave your computer.

## What is processed where

- **In your browser (live mode):** camera frames are tracked by MediaPipe
  inside the page. The models and runtime are served by this app, not by a
  CDN. Frames are never sent anywhere.
- **On your machine (the API and worker):** uploads and live recordings are
  saved to a local folder (the `media` Docker volume, or `backend/data/media`
  in native development). All analysis runs locally.
- **The LLM (Ollama):** receives only the measured metrics and the transcript
  text, never audio or video, and runs on your machine.

No analytics, no telemetry, no cloud AI APIs. Hugging Face telemetry is
disabled in the Docker image, and models load from the local cache after the
first download.

## What is stored

| Data | Where | Removed when |
| --- | --- | --- |
| Account (email, name, argon2 password hash, settings) | PostgreSQL | you delete your account |
| Sign-in sessions (SHA-256 hash of the cookie token) | PostgreSQL | you sign out, it expires (30 days), or you delete your account |
| Original recording and extracted audio | media folder, one folder per session | you delete the session or account, or right after analysis if "Delete the video after analysis" is on |
| Transcript, metrics, scores and report | PostgreSQL | you delete the session or account |

Live-mode audio streamed for the live counters is transcribed in memory and
never written to disk.

## Deleting your data

- **One session:** the Delete button on the session or in the Sessions list
  removes its database rows and its whole media folder.
- **Everything:** Settings → Delete account (asks for your password) removes
  your account, every session, every report and every file.
- **Video only:** Settings → "Delete the video after analysis" keeps reports
  but removes recordings as soon as they are analyzed.

## Network access

The app needs the internet only to download models the first time (Whisper
and wav2vec2 from Hugging Face, MediaPipe models from Google's model storage,
the LLM through Ollama). After that it works offline.
