// Picks a MediaRecorder format the browser supports (webm in Chrome/Firefox, mp4 in Safari).

const CANDIDATES = [
  'video/webm;codecs=vp9,opus',
  'video/webm;codecs=vp8,opus',
  'video/webm',
  'video/mp4;codecs=avc1,mp4a',
  'video/mp4',
]

export function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined
  return CANDIDATES.find((t) => MediaRecorder.isTypeSupported(t))
}

export function extensionFor(mime: string): string {
  return mime.startsWith('video/mp4') ? '.mp4' : '.webm'
}

export class Recording {
  private recorder: MediaRecorder
  private chunks: Blob[] = []
  readonly mimeType: string

  constructor(stream: MediaStream) {
    const mime = pickMimeType()
    this.recorder = new MediaRecorder(stream, mime ? { mimeType: mime, videoBitsPerSecond: 2_500_000 } : undefined)
    this.mimeType = this.recorder.mimeType || mime || 'video/webm'
    this.recorder.ondataavailable = (e) => {
      if (e.data.size) this.chunks.push(e.data)
    }
  }

  start() {
    this.recorder.start(1000)
  }

  stop(): Promise<Blob> {
    return new Promise((resolve) => {
      this.recorder.onstop = () => resolve(new Blob(this.chunks, { type: this.mimeType }))
      if (this.recorder.state !== 'inactive') this.recorder.stop()
      else resolve(new Blob(this.chunks, { type: this.mimeType }))
    })
  }
}
