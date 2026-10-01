# GPT + Grok voice chat

Dragon AI Agent keeps the existing **GPT voice** path and adds **Grok voice** as a second, selectable option. Grok does **not** replace GPT.

James’s bar after the call: ChatGPT voice is **duplex**. Grok must feel the same — full-duplex speech-to-speech like Grok voice on an xAI call — not turn-based chained STT→LLM→TTS.

This packaging repo does not contain Hermes `apps/desktop` source and does not rebuild `Hermes.exe`. The selector and Grok duplex client are a launch-time overlay (same pattern as Teams). Gateway config is written into the embedded Hermes home.

## What is duplex-ready in this repo

| Surface | Status |
|---------|--------|
| **GPT \| Grok** selector | Ready. Overlay control; default GPT. Never remove. |
| **GPT duplex** | Ready via upstream Hermes `voice.voice_chat_mode: gpt-live` → OpenAI `gpt-live-1`. Unchanged. |
| **Grok duplex client** | Ready in this repo. Electron overlay `branding/voice/dragon-voice-selector.js` (**Talk with Grok**) opens official `wss://api.x.ai/v1/realtime?model=grok-voice-latest`. |
| **Ephemeral token** | Ready. Helper `POST http://127.0.0.1:8654/api/voice/ephemeral` calls official `POST https://api.x.ai/v1/realtime/client_secrets`. Renderer never sees `XAI_API_KEY`. Browser WS uses `xai-client-secret.<value>`. |
| **session.update** | Ready. Official `voice=eve`, `turn_detection.type=server_vad`, `audio.input/output.format` = `audio/pcm` @ 24000. |
| **Mic + playback** | Ready in overlay. `input_audio_buffer.append` (base64 PCM16); play `response.output_audio.delta` / `response.audio.delta`. |
| **Unary STT/TTS fallback** | Ready. Documented `POST /v1/stt` + `POST /v1/tts` if the helper or key is missing. |
| **Hermes `grok-live` engine** | **Not in this repo.** Upstream only accepts `chained` \| `gpt-live`. |

Selecting **Grok** writes `voice_chat_mode: chained` on purpose so Hermes does not also start native gpt-live. The overlay Talk button is the duplex host until Hermes accepts `grok-live`.

## What still needs a Hermes engine change

These files live in NousResearch/hermes-agent, not here. This package cannot rebuild `Hermes.exe`.

1. `methods_config_set.py` — accept `voice.voice_chat_mode: grok-live` beside `gpt-live` / `chained`.
2. Desktop `voice-live.ts` (or the module that starts gpt-live) — add a `grok-live` path that mints `POST /v1/realtime/client_secrets` and opens `wss://api.x.ai/v1/realtime?model=grok-voice-latest` with `xai-client-secret.<value>`.
3. `tools/voice_live.py` — accept `grok-live` beside `gpt-live`. Do not delete GPT-Live.

When that lands, this package can write `voice_chat_mode: grok-live` instead of `chained` and optionally retire the overlay Talk button (or keep it as fallback). Ready-to-paste prompt is at the bottom of this file.

## What James sees

In the desktop voice chat chrome, a **GPT | Grok** control sits with the composer. Both options are always listed. The active one is the crimson selected state. With **Grok** selected, **Talk with Grok** starts overlay full duplex.

| Option | What it uses | Auth |
|--------|----------------|------|
| **GPT** (default) | Upstream Hermes `voice.voice_chat_mode: gpt-live` → OpenAI `gpt-live-1` | `OPENAI_API_KEY` or `voice.gpt_live.api_key` (already required for GPT voice) |
| **Grok** | Overlay full duplex: `wss://api.x.ai/v1/realtime?model=grok-voice-latest` after `POST /v1/realtime/client_secrets`. Unary xAI STT/TTS is fallback only. | Existing xAI Grok login — `XAI_API_KEY` or xAI OAuth. This step does **not** ask for a new key |

## Official xAI endpoints (do not invent others)

Documented at [xAI Voice](https://docs.x.ai/developers/model-capabilities/audio/voice), [Speech to Speech](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech), and [Ephemeral Tokens](https://docs.x.ai/developers/model-capabilities/audio/ephemeral-tokens):

| Role | Endpoint |
|------|----------|
| Speech to speech (Grok voice on xAI calls) | `wss://api.x.ai/v1/realtime?model=grok-voice-latest` |
| Browser/Electron token | `POST https://api.x.ai/v1/realtime/client_secrets` body `{expires_after:{seconds:300}}` only — docs say `session` is unsupported |
| Browser WS auth | `new WebSocket(url, ["xai-client-secret." + value])` |
| Text to speech (fallback) | `POST https://api.x.ai/v1/tts` (`voice_id` default `eve`, `language` e.g. `en`) |
| Speech to text (fallback) | `POST https://api.x.ai/v1/stt` (multipart; `model=grok-voice-transcribe-2.0`; `file` last) |
| Streaming STT (fallback) | `wss://api.x.ai/v1/stt` |

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
    duplex: true
    realtime: "wss://api.x.ai/v1/realtime?model=grok-voice-latest"
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
    duplex: true
    realtime: "wss://api.x.ai/v1/realtime?model=grok-voice-latest"
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

`voice_chat_mode: chained` for Grok is an **upstream limitation**: Hermes only accepts `chained` | `gpt-live`. Writing `grok-live` today is treated as chained or rejected. Overlay owns duplex so Hermes does not start gpt-live at the same time. Unary xAI STT/TTS stay as fallback.

Do not write API keys into `config.yaml`. Auth stays env / Hermes Settings → Keys (`XAI_` card, `OPENAI_`).

## Helper

Loopback only: `http://127.0.0.1:8654/api/voice` (not Bot Screen `:8650`, not Teams `:8653`).

```powershell
python3 scripts/airmaze/voice_chat.py apply --provider grok
python3 scripts/airmaze/voice_chat.py apply --provider gpt
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\airmaze\Apply-VoiceChat.ps1 -Provider grok
python3 scripts/airmaze/Test-VoiceChat.py
```

Launch starts the helper (`Start-DragonAIVoiceChat`). The overlay POSTs `{ "id": "gpt" | "grok" }` to `/api/voice/selection`. **Talk with Grok** POSTs `/api/voice/ephemeral` then opens the official realtime WebSocket.

## How to test GPT vs Grok

1. Put `OPENAI_API_KEY` (GPT voice) and `XAI_API_KEY` or xAI OAuth (Grok voice) in Settings → Keys. No keys in this repo.
2. Start Dragon AI Agent. Confirm the composer shows **GPT** and **Grok**.
3. Click **GPT**. Use the Hermes mic. Existing GPT-Live duplex (OpenAI). Grok stays visible, not selected.
4. Click **Grok**. Click **Talk with Grok**. Allow the microphone. Speak — server VAD should barge in / answer without a chained STT→LLM→TTS pause. GPT remains in the control.
5. Click **Stop Grok**, then **GPT**. GPT-Live returns; `voice.grok_live` is still in `config.yaml`.
6. Offline: `python3 scripts/airmaze/Test-VoiceChat.py`.

## Ready-to-paste follow-up prompt (Hermes engine)

Copy into a Cursor / Grok Build against **NousResearch/hermes-agent** (or the next packaging pass once that engine exists):

```
Add grok-live beside gpt-live in Hermes voice. Do not replace GPT.

Keep GPT voice intact as voice.voice_chat_mode: gpt-live (OpenAI gpt-live-1 WebRTC via the existing gpt-live path). Grok is a second option that must feel as responsive as ChatGPT voice — full duplex speech-to-speech, not chained STT→LLM→TTS.

Accept voice.voice_chat_mode: grok-live in methods_config_set.py (today only chained | gpt-live). Implement a grok-live engine next to voice-live.ts and tools/voice_live.py.

Official xAI contract only (docs.x.ai — do not invent endpoints):
- WSS wss://api.x.ai/v1/realtime?model=grok-voice-latest
- POST https://api.x.ai/v1/realtime/client_secrets  body {expires_after:{seconds:300}} only. Docs say the session field is unsupported.
- Response value (+ expires_at). Never put XAI_API_KEY in the renderer.
- Browser / Electron WS: new WebSocket(url, ["xai-client-secret." + value])
- session.update: voice eve, turn_detection.type=server_vad, audio.input/output.format {type:"audio/pcm", rate:24000}
- Stream mic with input_audio_buffer.append {audio: base64 PCM16}
- Play response.output_audio.delta and/or response.audio.delta
- VAD events: input_audio_buffer.speech_started / speech_stopped

Dragon-AI-Agent packaging already:
- GPT | Grok selector (do not remove)
- Overlay Talk with Grok in branding/voice/dragon-voice-selector.js
- Helper 127.0.0.1:8654 POST /api/voice/ephemeral mints the token
- Writes voice.grok_live (model grok-voice-latest, duplex true) and keeps voice.gpt_live
- Writes voice_chat_mode: chained when Grok is selected so native gpt-live does not also start

When grok-live is accepted, Dragon can write voice_chat_mode: grok-live instead of chained and optionally retire the overlay Talk button. Draft only; do not merge packaging until James says so.
```

## Out of scope

- Replacing GPT voice
- Removing the GPT | Grok selector
- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Inventing unofficial Grok URLs
- Merging this PR
