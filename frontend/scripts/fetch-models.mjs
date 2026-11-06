// Copies the MediaPipe WASM runtime and downloads the model files into public/,
// so the browser loads everything from this app and never from a CDN.
import { copyFile, mkdir, readdir, rename, stat, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const wasmSrc = join(root, 'node_modules/@mediapipe/tasks-vision/wasm')
const wasmDest = join(root, 'public/mediapipe/wasm')
const modelsDest = join(root, 'public/mediapipe/models')

const MODELS = {
  'pose_landmarker_lite.task':
    'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task',
  'face_landmarker.task':
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task',
  'hand_landmarker.task':
    'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
}

async function exists(p) {
  try {
    return (await stat(p)).size > 0
  } catch {
    return false
  }
}

await mkdir(wasmDest, { recursive: true })
for (const f of await readdir(wasmSrc)) await copyFile(join(wasmSrc, f), join(wasmDest, f))

await mkdir(modelsDest, { recursive: true })
for (const [name, url] of Object.entries(MODELS)) {
  const dest = join(modelsDest, name)
  if (await exists(dest)) continue
  process.stdout.write(`Downloading ${name}… `)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`)
  await writeFile(`${dest}.part`, Buffer.from(await res.arrayBuffer()))
  await rename(`${dest}.part`, dest)
  console.log('done')
}
