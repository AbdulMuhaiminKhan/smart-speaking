// AudioWorklet: mixes to mono, resamples to 16 kHz, and posts Float32 chunks.
// Runs at the device's native rate (44.1 or 48 kHz) because some browsers
// refuse to connect a microphone to a 16 kHz AudioContext.
const TARGET_RATE = 16000

class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super()
    this.ratio = sampleRate / TARGET_RATE
    this.pos = 0 // fractional read position into the carried-over input
    this.carry = new Float32Array(0)
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input.length || !input[0].length) return true

    // Mix channels down to mono.
    const frames = input[0].length
    const mono = new Float32Array(this.carry.length + frames)
    mono.set(this.carry, 0)
    for (let i = 0; i < frames; i++) {
      let sum = 0
      for (let c = 0; c < input.length; c++) sum += input[c][i]
      mono[this.carry.length + i] = sum / input.length
    }

    // Linear interpolation resampling.
    const out = []
    let pos = this.pos
    while (pos + 1 < mono.length) {
      const i = Math.floor(pos)
      const frac = pos - i
      out.push(mono[i] * (1 - frac) + mono[i + 1] * frac)
      pos += this.ratio
    }
    const keepFrom = Math.floor(pos)
    this.carry = mono.slice(keepFrom)
    this.pos = pos - keepFrom

    if (out.length) this.port.postMessage(Float32Array.from(out))
    return true
  }
}

registerProcessor('pcm-capture', PcmCapture)
