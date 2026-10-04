import { atom } from 'nanostores'

import { fetchVoiceLiveStatus, type VoiceChatMode, type VoiceLiveStatus } from '@/lib/voice-live'
import { activeGatewayProfileKey, requestGatewayForProfile } from '@/store/gateway'

/**
 * `voice.voice_chat_mode` as the backend resolves it, plus whether GPT-Live can
 * actually start (an OpenAI key resolves on the gateway host). The composer
 * mounts the chained or the live conversation engine from this; refreshed with
 * the config snapshot so a Settings change applies to the next conversation.
 */
export const $voiceLiveStatus = atom<null | VoiceLiveStatus>(null)

let inflight: null | Promise<null | VoiceLiveStatus> = null

export async function refreshVoiceLiveStatus(): Promise<null | VoiceLiveStatus> {
  if (inflight) {
    return inflight
  }

  inflight = fetchVoiceLiveStatus()
    .then(status => {
      $voiceLiveStatus.set(status)

      return status
    })
    .finally(() => {
      inflight = null
    })

  return inflight
}

/** Selected mode. `chained` until the backend answers, or when the backend predates the mode. */
export function selectedVoiceChatMode(status: null | VoiceLiveStatus = $voiceLiveStatus.get()): VoiceChatMode {
  return status?.mode === 'gpt-live' || status?.mode === 'grok-voice' ? status.mode : 'chained'
}

/** True for the full-duplex engines (GPT-Live, Grok Voice) that own mic and speaker. */
export function isFullDuplexMode(mode: VoiceChatMode): boolean {
  return mode !== 'chained'
}

/**
 * Persist `voice.voice_chat_mode` on the live gateway (whichever profile/host
 * the app is talking to) and re-read the resolved status, so the menu shows
 * what the backend will actually mount next. Takes effect on the NEXT
 * conversation; an active one keeps its engine.
 *
 * Routed by profile, not by socket: `config.set` is `@_profile_scoped`, so on
 * the shared-primary route an unscoped write lands in the LAUNCH profile's
 * config.yaml, not the viewed one (#125969 class).
 */
export async function setVoiceChatMode(mode: VoiceChatMode): Promise<null | VoiceLiveStatus> {
  await requestGatewayForProfile(activeGatewayProfileKey(), 'config.set', { key: 'voice.voice_chat_mode', value: mode })

  return refreshVoiceLiveStatus()
}
