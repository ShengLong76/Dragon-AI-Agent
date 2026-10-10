import { afterEach, describe, expect, it, vi } from 'vitest'

import { GrokVoiceSession } from './voice-grok'
import type { VoiceLiveHandlers } from './voice-live'

// Grok already ran a ScriptProcessorNode on the local mic to upload PCM.
// The Listening bar never saw those samples — it only got onSpeakingChange
// when the assistant played audio, so the dots stayed flat while the model heard.

interface FakeProcessor {
  connect: () => void
  disconnect: () => void
  onaudioprocess: ((event: { inputBuffer: { getChannelData: (channel: number) => Float32Array } }) => void) | null
}

const processor: FakeProcessor = {
  connect: () => undefined,
  disconnect: () => undefined,
  onaudioprocess: null
}

class FakeAudioContext {
  currentTime = 0
  close = vi.fn(async () => undefined)
  createMediaStreamSource() {
    return { connect: () => undefined }
  }
  createScriptProcessor() {
    return processor
  }
  createBuffer() {
    return { copyToChannel: () => undefined }
  }
  createBufferSource() {
    return { connect: () => undefined, start: () => undefined, addEventListener: () => undefined }
  }
}

class FakeWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  readyState = FakeWebSocket.OPEN
  addEventListener(type: string, listener: () => void) {
    if (type === 'open') {
      queueMicrotask(listener)
    }
  }
  send() {}
  close() {}
}

function installGrokTransport() {
  const api = vi.fn(async () => ({
    ok: true,
    client_secret: 'secret',
    instructions: 'Be helpful',
    tool: 'ask_dragon',
    url: 'wss://example.test/voice',
    voice: 'ara'
  }))

  Object.defineProperty(window, 'hermesDesktop', { configurable: true, value: { api } })
  Object.defineProperty(window.navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: async () => ({
        getAudioTracks: () => [{ enabled: true }],
        getTracks: () => [{ stop: () => undefined }]
      })
    }
  })
  Object.defineProperty(window, 'AudioContext', { configurable: true, value: FakeAudioContext })
  Object.defineProperty(globalThis, 'WebSocket', { configurable: true, value: FakeWebSocket })
}

afterEach(() => {
  processor.onaudioprocess = null
  Reflect.deleteProperty(window, 'hermesDesktop')
  Reflect.deleteProperty(window.navigator, 'mediaDevices')
  Reflect.deleteProperty(window, 'AudioContext')
  Reflect.deleteProperty(globalThis, 'WebSocket')
})

function speechEvent(amplitude = 0.25) {
  const samples = new Float32Array(8).fill(amplitude)

  return { inputBuffer: { getChannelData: () => samples } }
}

describe('Grok Voice local mic meter', () => {
  it('reports capture-buffer RMS on onInputLevel while listening', async () => {
    installGrokTransport()

    const onInputLevel = vi.fn()
    const handlers: VoiceLiveHandlers = {
      onClosed: () => undefined,
      onDelegation: () => undefined,
      onError: () => undefined,
      onInputLevel
    }

    const session = new GrokVoiceSession(handlers)
    await session.start([])

    expect(processor.onaudioprocess).toEqual(expect.any(Function))

    processor.onaudioprocess?.(speechEvent())

    expect(onInputLevel).toHaveBeenCalledTimes(1)
    expect(onInputLevel.mock.calls[0]?.[0]).toBeGreaterThan(0)

    session.setMuted(true)
    processor.onaudioprocess?.(speechEvent())

    expect(onInputLevel).toHaveBeenLastCalledWith(0)

    session.close()
  })
})
