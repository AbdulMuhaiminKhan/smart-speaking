// AudioWorklet that forwards mono Float32 samples to the main thread.
// The AudioContext runs at 16 kHz, so the browser already resampled them.
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel && channel.length) this.port.postMessage(channel.slice(0))
    return true
  }
}
registerProcessor('pcm-capture', PcmCapture)
