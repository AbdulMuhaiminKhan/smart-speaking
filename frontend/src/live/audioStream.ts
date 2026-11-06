// Streams microphone audio as 16 kHz int16 PCM over a WebSocket and reports live stats.

export interface LiveStats {
  type: 'stats'
  elapsed_s: number
  words: number
  wpm: number | null
  wpm_recent: number | null
  fillers: number
  filler_counts: Record<string, number>
  last_text: string
  speaking: boolean
}

type Message = LiveStats | { type: 'ready' } | { type: 'done' } | { type: 'error'; message: string }

export interface AudioStreamHandlers {
  onReady?: () => void
  onStats: (s: LiveStats) => void
  onError: (message: string) => void
}

const SEND_EVERY_SAMPLES = 4000 // 250 ms at 16 kHz

export class LiveAudioStream {
  private ctx: AudioContext | null = null
  private node: AudioWorkletNode | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private ws: WebSocket | null = null
  private buffer: Float32Array[] = []
  private buffered = 0
  private handlers: AudioStreamHandlers

  constructor(handlers: AudioStreamHandlers) {
    this.handlers = handlers
  }

  /** Create the AudioContext inside the click handler, before any await, so it is allowed to run. */
  static createContext(): AudioContext {
    return new AudioContext()
  }

  async start(stream: MediaStream, ctx: AudioContext, lang = 'en'): Promise<void> {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    this.ws = new WebSocket(`${proto}://${location.host}/api/live/ws?lang=${encodeURIComponent(lang)}`)
    this.ws.binaryType = 'arraybuffer'
    this.ws.onmessage = (e) => {
      const msg = JSON.parse(String(e.data)) as Message
      if (msg.type === 'stats') this.handlers.onStats(msg)
      else if (msg.type === 'ready') this.handlers.onReady?.()
      else if (msg.type === 'error') this.handlers.onError(msg.message)
    }
    this.ws.onerror = () => this.handlers.onError('Live feedback is unavailable. Recording still works.')

    this.ctx = ctx
    // Browsers start an AudioContext paused unless a click allowed it; resume to be sure.
    if (ctx.state !== 'running') await ctx.resume()
    await ctx.audioWorklet.addModule('/pcm-worklet.js')
    this.source = this.ctx.createMediaStreamSource(stream)
    this.node = new AudioWorkletNode(this.ctx, 'pcm-capture')
    this.node.port.onmessage = (e: MessageEvent<Float32Array>) => this.push(e.data)
    this.source.connect(this.node)
    // Some browsers only pull audio through nodes that reach the output; keep it silent.
    const mute = ctx.createGain()
    mute.gain.value = 0
    this.node.connect(mute).connect(ctx.destination)
  }

  private push(chunk: Float32Array) {
    this.buffer.push(chunk)
    this.buffered += chunk.length
    if (this.buffered < SEND_EVERY_SAMPLES) return
    const pcm = new Int16Array(this.buffered)
    let offset = 0
    for (const part of this.buffer) {
      for (let i = 0; i < part.length; i++) {
        const s = Math.max(-1, Math.min(1, part[i]))
        pcm[offset++] = s < 0 ? s * 0x8000 : s * 0x7fff
      }
    }
    this.buffer = []
    this.buffered = 0
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(pcm.buffer)
  }

  async stop(): Promise<void> {
    this.source?.disconnect()
    this.node?.disconnect()
    await this.ctx?.close().catch(() => undefined)
    const ws = this.ws
    if (ws && ws.readyState === WebSocket.OPEN) {
      await new Promise<void>((resolve) => {
        const timer = setTimeout(resolve, 4000)
        const prev = ws.onmessage
        ws.onmessage = (e) => {
          prev?.call(ws, e)
          if ((JSON.parse(String(e.data)) as Message).type === 'done') {
            clearTimeout(timer)
            resolve()
          }
        }
        ws.send('stop')
      })
      ws.close()
    }
    this.ws = null
  }
}
