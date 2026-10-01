# GPT + Grok voice chat

Dragon AI Agent keeps the existing **GPT voice** path and adds **Grok voice** as a second, selectable option. Grok does **not** replace GPT.

This packaging repo does not contain Hermes `apps/desktop` source and does not rebuild `Hermes.exe`. The selector is a launch-time overlay (same pattern as Teams). Gateway config is written into the embedded Hermes home.

## What James sees

In the desktop voice chat chrome, a **GPT | Grok** control sits with the composer. Both options are always listed. The active one is the crimson selected state.

| Option | What it uses | Auth |
|--------|----------------|------|
| **GPT** (default) | Upstream Hermes `voice.voice_chat_mode: gpt-live` → OpenAI `gpt-live-1` | `OPENAI_API_KEY` or `voice.gpt_live.api_key` (already required for GPT voice) |
| **Grok** | xAI Voice APIs: STT + TTS now; speech-to-speech (`grok-voice-latest`) when an ephemeral token is available | Existing xAI Grok login — `XAI_API_KEY` or xAI OAuth. This step does **not** ask for a new key |

## Official xAI endpoints (do not invent others)

Documented at [xAI Voice](https://docs.x.ai/developers/model-capabilities/audio/voice):

| Role | Endpoint |
|------|----------|
| Text to speech | `POST https://api.x.ai/v1/tts` (`voice_id` default `eve`, `language` e.g. `en`) |
| Speech to text | `POST https://api.x.ai/v1/stt` (multipart; `model=grok-voice-transcribe-2.0`; `file` last) |
| Streaming STT | `wss://api.x.ai/v1/stt` |
| Speech to speech (Grok voice on xAI calls) | `wss://api.x.ai/v1/realtime?model=grok-voice-latest` |
| Browser/Electron token | `POST https://api.x.ai/v1/realtime/client_secrets` (`expires_after.seconds`) |

GPT-Live stays on OpenAI `POST https://api.openai.com/v1/live/sessions` via Hermes `tools/voice_live.py`. Do not replace that path.

## Config written (no secrets)

File: `%USERPROFILE%\.hermes-airmaze-embedded\config.yaml`

Selecting **GPT**:

```yaml
voice:
  selected_provider: gpt
  voice_chat_mode: gpt-live
  gpt_live:
    model: gpt-live-1
    voice: marin
  grok_live:
    model: grok-voice-latest
    voice: eve
```

Selecting **Grok** (GPT block is kept):

```yaml
voice:
  selected_provider: grok
  voice_chat_mode: chained
  gpt_live:
    model: gpt-live-1
    voice: marin
  grok_live:
    model: grok-voice-latest
    voice: eve
stt:
  enabled: true
  provider: xai
  xai:
    model: grok-voice-transcribe-2.0
tts:
  provider: xai
  xai:
    voice_id: eve
    language: en
```

`voice_chat_mode: chained` for Grok is an **upstream limitation**: Hermes only accepts `chained` | `gpt-live`. Hermes already lists `stt.provider: xai` and `tts.provider: xai` (Grok TTS). Full-duplex Grok (same style as an xAI call) is `grok-voice-latest` over the realtime WebSocket. The overlay helper can mint an ephemeral token so the renderer never sees `XAI_API_KEY`.

Do not write API keys into `config.yaml`. Auth stays env / Hermes Settings → Keys (`XAI_` card, `OPENAI_`).

## Helper

Loopback only: `http://127.0.0.1:8654/api/voice` (not Bot Screen `:8650`, not Teams `:8653`).

```powershell
python3 scripts/airmaze/voice_chat.py apply --provider grok
python3 scripts/airmaze/voice_chat.py apply --provider gpt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\airmaze\Apply-VoiceChat.ps1 -Provider grok
python3 scripts/airmaze/Test-VoiceChat.py
```

Launch starts the helper (`Start-DragonAIVoiceChat`). The overlay POSTs `{ "id": "gpt" | "grok" }` to `/api/voice/selection`.

## How to test GPT vs Grok

1. Put `OPENAI_API_KEY` (GPT voice) and `XAI_API_KEY` or xAI OAuth (Grok voice) in Settings → Keys. No keys in this repo.
2. Start Dragon AI Agent. Confirm the composer shows **GPT** and **Grok**.
3. Click **GPT**. Start a voice conversation. You should get the existing GPT-Live session (OpenAI). Grok stays visible, not selected.
4. Click **Grok**. Start voice / dictation. STT/TTS should use xAI (`eve`). GPT remains in the control.
5. Click **GPT** again. GPT-Live returns; `voice.grok_live` is still in `config.yaml`.
6. Offline: `python3 scripts/airmaze/Test-VoiceChat.py`.

## Blocker / TODO (full-duplex Grok)

xAI **does** publish Speech to Speech (`wss://api.x.ai/v1/realtime?model=grok-voice-latest`). The remaining gap is Hermes, not a missing API:

1. Upstream `voice.voice_chat_mode` rejects anything except `chained` | `gpt-live` (`methods_config_set.py`).
2. The Electron renderer cannot put `Authorization` on a browser WebSocket; it needs `POST /v1/realtime/client_secrets` (this helper’s `/api/voice/ephemeral`) and `xai-client-secret.<token>`.
3. A later change should add a `grok-live` engine next to `voice-live.ts` **without** deleting GPT-Live.

Until that lands, Grok voice in this package is selectable STT + TTS on the documented xAI endpoints, with realtime session/token builders ready.

## Out of scope

- Replacing GPT voice
- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Inventing unofficial Grok URLs
- Merging this PR
