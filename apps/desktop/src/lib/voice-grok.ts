import { type OwnerScope, ownerScoped } from '@/api/client'
import { hermesApi } from '@/hermes'

import { rmsLevelFromFloatSamples } from './mic-level'
import type { LiveHistoryMessage, LiveTranscriptFragment, VoiceLiveHandlers } from './voice-live'

/**
 * Grok Voice chat: xAI's full-duplex speech-to-speech model as the voice of
 * Dragon AI, over `wss://api.x.ai/v1/realtime`.
 *
 * Same command surface as `VoiceLiveSession`, so the live conversation hook
 * drives either engine. Grok has no delegation primitive; it calls the one
 * client function the session declares (`ask_dragon`). Each call becomes a
 * delegation; the reply Dragon AI streams back is buffered and returned as
 * that call's `function_call_output` when the hook marks it complete, and
 * Grok speaks it. The backend mints a short-lived client secret, so the xAI
 * key or SuperGrok grant never reaches the renderer.
 */

const SAMPLE_RATE = 24_000
const CAPTURE_FRAME = 4096
const CONTEXT_MAX_FRAGMENTS = 80
const HISTORY_CHAR_BUDGET = 3_000

interface GrokSessionGrant {
  ok: boolean
  client_secret: string
  url: string
  voice: string
  instructions: string
  tool: string
}

interface GrokServerEvent {
  type: string
  delta?: string
  transcript?: string
  name?: string
  call_id?: string
  arguments?: string
  error?: { message?: string; code?: string }
}

function toBase64(bytes: Uint8Array): string {
  let binary = ''

  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
  }

  return btoa(binary)
}

function floatToPcm16(samples: Float32Array): Uint8Array {
  const out = new DataView(new ArrayBuffer(samples.length * 2))

  for (let index = 0; index < samples.length; index += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[index]!))
    out.setInt16(index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  }

  return new Uint8Array(out.buffer)
}

function pcm16ToFloat(base64: string): Float32Array<ArrayBuffer> {
  const binary = atob(base64)
  const view = new DataView(new ArrayBuffer(binary.length))

  for (let index = 0; index < binary.length; index += 1) {
    view.setUint8(index, binary.charCodeAt(index))
  }

  const out = new Float32Array(binary.length >> 1)

  for (let index = 0; index < out.length; index += 1) {
    out[index] = view.getInt16(index * 2, true) / 0x8000
  }

  return out
}

function historyNote(history: LiveHistoryMessage[]): string {
  const lines: string[] = []
  let budget = HISTORY_CHAR_BUDGET

  for (const message of [...history].reverse()) {
    const text = message.content.map(part => part.text).join(' ')

    if (budget - text.length < 0) {
      break
    }

    budget -= text.length
    lines.unshift(`${message.role === 'assistant' ? 'Assistant' : 'User'}: ${text}`)
  }

  return lines.length ? `\n\nThe conversation so far, newest last:\n${lines.join('\n')}` : ''
}

export class GrokVoiceSession {
  readonly audio: HTMLAudioElement
  private readonly owner: null | OwnerScope
  private readonly handlers: VoiceLiveHandlers
  private socket: null | WebSocket = null
  private microphone: null | MediaStream = null
  private captureContext: null | AudioContext = null
  private processor: null | ScriptProcessorNode = null
  private playbackContext: null | AudioContext = null
  private playing = new Set<AudioBufferSourceNode>()
  private playhead = 0
  private muted = false
  private finalized = false
  private started = false
  private tool = 'ask_dragon'
  private transcript: LiveTranscriptFragment[] = []
  private assistantLine = ''
  private replies = new Map<string, string>()
  private awaitingResponse = new Set<string>()
  private lastSpeaking = false
  sessionId: null | string = null
  activeDelegationId: null | string = null

  constructor(handlers: VoiceLiveHandlers, owner: null | OwnerScope = null) {
    this.handlers = handlers
    this.owner = owner
    this.audio = new Audio()
  }

  get connected(): boolean {
    return this.started && this.socket?.readyState === WebSocket.OPEN
  }

  contextWindow(): LiveTranscriptFragment[] {
    return this.transcript.slice(-CONTEXT_MAX_FRAGMENTS)
  }

  private send(event: Record<string, unknown>): boolean {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      return false
    }

    this.socket.send(JSON.stringify(event))

    return true
  }

  private pushTranscript(speaker: 'assistant' | 'user', text: string) {
    const clean = text.trim()

    if (!clean) {
      return
    }

    const now = Date.now()
    const fragment: LiveTranscriptFragment = { endMs: now, speaker, startMs: now, text: `${clean} ` }
    this.transcript.push(fragment)

    if (this.transcript.length > 2_000) {
      this.transcript.splice(0, this.transcript.length - 1_500)
    }

    this.handlers.onTranscript?.(fragment)
  }

  async start(history: LiveHistoryMessage[]): Promise<void> {
    if (this.socket) {
      throw new Error('Grok Voice session already started')
    }

    const grant = await hermesApi<GrokSessionGrant>({
      ...ownerScoped(this.owner ?? undefined),
      method: 'POST',
      path: '/api/audio/voice-live/grok-session',
      timeoutMs: 45_000
    })

    if (!grant?.ok || !grant.client_secret || !grant.url) {
      throw new Error('Grok Voice session creation failed')
    }

    this.tool = grant.tool || this.tool

    this.microphone = await navigator.mediaDevices.getUserMedia({
      audio: { autoGainControl: true, echoCancellation: true, noiseSuppression: true }
    })

    const socket = new WebSocket(grant.url, [`xai-client-secret.${grant.client_secret}`])
    this.socket = socket

    await new Promise<void>((resolve, reject) => {
      socket.addEventListener('open', () => resolve(), { once: true })
      socket.addEventListener('error', () => reject(new Error('Could not reach Grok Voice')), { once: true })
    })

    socket.addEventListener('message', ({ data }) => this.handleEvent(String(data)))
    socket.addEventListener('close', event => {
      if (!this.finalized) {
        this.finish(event.reason || 'connection_lost')
      }
    })

    this.send({
      type: 'session.update',
      session: {
        voice: grant.voice,
        instructions: `${grant.instructions}${historyNote(history)}`,
        turn_detection: { type: 'server_vad' },
        audio: {
          input: { format: { type: 'audio/pcm', rate: SAMPLE_RATE } },
          output: { format: { type: 'audio/pcm', rate: SAMPLE_RATE } }
        },
        tools: [
          {
            type: 'function',
            name: this.tool,
            description:
              'Hand a request to Dragon AI, the agent with tools, files, the web, memory, and schedules. Use it for anything beyond small talk.',
            parameters: {
              type: 'object',
              properties: {
                request: { type: 'string', description: "The user's request, in their own words." }
              },
              required: ['request']
            }
          }
        ]
      }
    })

    this.startCapture(this.microphone)
    this.playbackContext = new AudioContext({ sampleRate: SAMPLE_RATE })
    this.started = true
  }

  private startCapture(stream: MediaStream) {
    const context = new AudioContext({ sampleRate: SAMPLE_RATE })
    const source = context.createMediaStreamSource(stream)
    const processor = context.createScriptProcessor(CAPTURE_FRAME, 1, 1)

    processor.onaudioprocess = event => {
      const samples = event.inputBuffer.getChannelData(0)
      this.handlers.onInputLevel?.(this.muted ? 0 : rmsLevelFromFloatSamples(samples))

      if (this.muted || !this.connected) {
        return
      }

      this.send({
        type: 'input_audio_buffer.append',
        audio: toBase64(floatToPcm16(samples))
      })
    }

    source.connect(processor)
    processor.connect(context.destination)
    this.captureContext = context
    this.processor = processor
  }

  private play(base64: string) {
    const context = this.playbackContext

    if (!context || !base64) {
      return
    }

    const samples = pcm16ToFloat(base64)
    const buffer = context.createBuffer(1, samples.length, SAMPLE_RATE)
    buffer.copyToChannel(samples, 0)
    const source = context.createBufferSource()
    source.buffer = buffer
    source.connect(context.destination)
    this.playhead = Math.max(this.playhead, context.currentTime)
    source.start(this.playhead)
    this.playhead += buffer.duration
    this.playing.add(source)
    this.setSpeaking(true)
    source.addEventListener('ended', () => {
      this.playing.delete(source)

      if (!this.playing.size) {
        this.setSpeaking(false)
        this.flushPendingResponses()
      }
    })
  }

  private stopPlayback() {
    for (const source of this.playing) {
      try {
        source.stop()
      } catch {
        // Already ended.
      }
    }

    this.playing.clear()
    this.playhead = 0
    this.setSpeaking(false)
  }

  private setSpeaking(speaking: boolean) {
    if (speaking !== this.lastSpeaking) {
      this.lastSpeaking = speaking
      this.handlers.onSpeakingChange?.(speaking)
    }
  }

  private handleEvent(raw: string) {
    let event: GrokServerEvent

    try {
      event = JSON.parse(raw) as GrokServerEvent
    } catch {
      return
    }

    switch (event.type) {
      case 'session.created':
      case 'session.updated':
        return

      case 'response.output_audio.delta':
      case 'response.audio.delta':
        this.play(event.delta ?? '')

        return

      case 'response.output_audio_transcript.delta':
      case 'response.audio_transcript.delta':
        this.assistantLine += event.delta ?? ''

        return

      case 'response.done':
        this.pushTranscript('assistant', this.assistantLine)
        this.assistantLine = ''

        return

      case 'input_audio_buffer.speech_started':
        this.stopPlayback()

        return

      case 'conversation.item.input_audio_transcription.completed':
        this.pushTranscript('user', event.transcript ?? '')

        return

      case 'response.function_call_arguments.done': {
        if (event.name !== this.tool || !event.call_id) {
          return
        }

        let request = ''

        try {
          request = String((JSON.parse(event.arguments || '{}') as { request?: unknown }).request ?? '')
        } catch {
          request = event.arguments ?? ''
        }

        this.pushTranscript('user', request)
        this.activeDelegationId = event.call_id
        this.replies.set(event.call_id, '')
        this.handlers.onDelegation(event.call_id, this.contextWindow())

        return
      }

      case 'error':
        this.handlers.onError(event.error?.message ?? 'Grok Voice error', false)

        return

      default:
        return
    }
  }

  /** Grok speaks nothing while a call is open; progress notes stay quiet. */
  think(_delegationId: null | string, _content: string): void {}

  /** Collect the reply; it is returned as one function output on `complete`. */
  speak(delegationId: null | string, content: string): void {
    if (!delegationId || !this.replies.has(delegationId)) {
      return
    }

    this.replies.set(delegationId, `${this.replies.get(delegationId)} ${content}`.trim())
  }

  /** The agent's turn settled: hand the reply back and let Grok answer once it stops talking. */
  complete(delegationId: null | string): void {
    if (!delegationId || !this.replies.has(delegationId)) {
      return
    }

    const output = this.replies.get(delegationId) || 'Dragon AI finished that request without a spoken result.'
    this.replies.delete(delegationId)
    this.send({
      type: 'conversation.item.create',
      item: { type: 'function_call_output', call_id: delegationId, output }
    })
    this.awaitingResponse.add(delegationId)
    this.flushPendingResponses()
  }

  private flushPendingResponses() {
    if (this.playing.size || !this.awaitingResponse.size) {
      return
    }

    this.awaitingResponse.clear()
    this.send({ type: 'response.create' })
  }

  instruct(_content: string): void {
    this.send({ type: 'input_audio_buffer.commit' })
    this.send({ type: 'response.create' })
  }

  setMuted(muted: boolean): void {
    this.muted = muted

    for (const track of this.microphone?.getAudioTracks() ?? []) {
      track.enabled = !muted
    }
  }

  close(): void {
    this.finish('close_requested')
  }

  private finish(reason: string) {
    if (this.finalized) {
      return
    }

    this.finalized = true
    this.stopPlayback()
    this.processor?.disconnect()
    void this.captureContext?.close().catch(() => undefined)
    void this.playbackContext?.close().catch(() => undefined)
    this.microphone?.getTracks().forEach(track => track.stop())

    if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
      this.socket.close(1000)
    }

    this.handlers.onClosed(reason, null)
  }
}
