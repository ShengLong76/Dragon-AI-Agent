import { afterEach, describe, expect, it, vi } from 'vitest'

import { setApiRequestConnection, setApiRequestProfile } from '@/hermes'

import { type VoiceLiveHandlers, VoiceLiveSession } from './voice-live'

// GPT-Live already had an AnalyserNode — but it sat on the *remote* (assistant)
// track and only flipped `onSpeakingChange`. The Listening chrome reads `level`
// while status is `listening`, so a meter that never saw the local mic stayed
// a row of static dots even though the agent heard the user.

class FakeAudioContext {
  state: AudioContextState = 'running'
  close = vi.fn(async () => {
    this.state = 'closed'
  })
  resume = vi.fn(async () => undefined)

  createAnalyser() {
    return {
      disconnect: vi.fn(),
      fftSize: 256,
      frequencyBinCount: 128,
      getByteTimeDomainData: (data: Uint8Array) => {
        data.fill(152)
      }
    }
  }

  createMediaStreamSource() {
    return { connect: vi.fn() }
  }
}

function installApi() {
  const api = vi.fn(async () => ({
    ok: true,
    session: { id: 's1' },
    transport: { sdp: 'answer', type: 'answer' }
  }))

  Object.defineProperty(window, 'hermesDesktop', { configurable: true, value: { api } })

  return api
}

function installWebRTC() {
  const channel = {
    addEventListener: () => undefined,
    close: () => undefined,
    readyState: 'closed' as RTCDataChannelState,
    send: () => undefined
  }

  const PeerConnection = class {
    addEventListener = () => undefined
    addTrack = () => undefined
    close = () => undefined
    connectionState = 'new'
    createDataChannel = () => channel
    createOffer = async () => ({})
    iceGatheringState = 'complete'
    localDescription = { sdp: 'v=0\r\n' }
    setLocalDescription = async () => undefined
    setRemoteDescription = async () => undefined
  }

  Object.defineProperty(globalThis, 'RTCPeerConnection', { configurable: true, value: PeerConnection })
  Object.defineProperty(window.navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: async () => ({
        getAudioTracks: () => [],
        getTracks: () => []
      })
    }
  })
  Object.defineProperty(window, 'AudioContext', { configurable: true, value: FakeAudioContext })
}

afterEach(() => {
  setApiRequestConnection(null)
  setApiRequestProfile(null)
  Reflect.deleteProperty(window, 'hermesDesktop')
  Reflect.deleteProperty(globalThis, 'RTCPeerConnection')
  Reflect.deleteProperty(window.navigator, 'mediaDevices')
  Reflect.deleteProperty(window, 'AudioContext')
})

describe('GPT-Live local mic meter', () => {
  it('reports live mic RMS on onInputLevel once the capture stream is open', async () => {
    installWebRTC()
    installApi()

    const onInputLevel = vi.fn()
    const handlers: VoiceLiveHandlers = {
      onClosed: () => undefined,
      onDelegation: () => undefined,
      onError: () => undefined,
      onInputLevel
    }

    const session = new VoiceLiveSession(handlers)
    await session.start([])

    await vi.waitFor(() => {
      expect(onInputLevel).toHaveBeenCalled()
    })

    expect(onInputLevel.mock.calls.some(([level]) => typeof level === 'number' && level > 0)).toBe(true)

    session.close()
  })
})
