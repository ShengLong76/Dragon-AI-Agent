# GPT + Grok voice chat

Dragon AI Agent keeps the existing **GPT voice** path and adds **Grok Voice** as a third Settings conversation mode. Grok does **not** replace GPT.

James’s bar after the call: ChatGPT voice is **duplex**. Grok must feel the same — full-duplex speech-to-speech like Grok voice on an xAI call — not turn-based chained STT→LLM→TTS.

**Selection is Settings → Voice → Voice conversation mode** (and backend `voice.voice_chat_mode`). That dropdown already has **Chained** and **Gpt-live**. This package adds **Grok Voice**. Chat-screen GPT / Grok pills are **removed**. The composer right-side **waveform** opens a Grok-Bot floating capsule that hosts overlay duplex.

This packaging repo does not contain Hermes `apps/desktop` source and does not rebuild `Hermes.exe`. The Settings option, selector, and Grok duplex client are a launch-time overlay (same pattern as Teams). Gateway config is written into the embedded Hermes home.

## What is duplex-ready in this repo

| Surface | Status |
|---------|--------|
| **Settings Voice conversation mode** | Ready. Overlay + renderer enum add **Grok Voice** beside **Chained** and **Gpt-live**. Writes `voice.voice_chat_mode: grok-live`. |
| **GPT \| Grok** composer pills | **Removed.** Not the selection surface. |
| **Composer waveform** | Ready. Right-side waveform icon opens the floating capsule. Accessible name **Talk with Grok**. |
| **Floating capsule** | Ready. Near the top of the chat pane: bot avatar \| purple vertical bars \| **gear** \| chat \| mic \| red X. |
| **Gear Voice settings** | Ready. Official xAI voices (`eve`, `ara`, `rex`, `sal`, `leo`), speed `0.75×–2×`, language, interrupt. Persists via `POST /api/voice/prefs`. |
| **GPT duplex** | Ready via upstream Hermes `voice.voice_chat_mode: gpt-live` → OpenAI `gpt-live-1`. Unchanged. |
| **Grok duplex client** | Ready. Electron overlay `branding/voice/dragon-voice-selector.js` (waveform → capsule) opens official `wss://api.x.ai/v1/realtime?model=grok-voice-latest`. |
| **Ephemeral token** | Ready. Helper `POST http://127.0.0.1:8654/api/voice/ephemeral` calls official `POST https://api.x.ai/v1/realtime/client_secrets`. Renderer never sees `XAI_API_KEY`. Browser WS uses `xai-client-secret.<value>`. |
| **session.update** | Ready. Official `voice=eve`, `turn_detection.type=server_vad`, `audio.input/output.format` = `audio/pcm` @ 24000. |
| **Mic + playback** | Ready in overlay. `input_audio_buffer.append` (base64 PCM16); play `response.output_audio.delta` / `response.audio.delta`. |
| **Unary STT/TTS fallback** | Ready. Documented `POST /v1/stt` + `POST /v1/tts` if the helper or key is missing. |
| **Hermes `grok-live` engine** | **Not in this repo.** Upstream `voice_live.py` still maps non-`gpt-live` to chained. Overlay hosts Grok duplex. |

Selecting **Grok Voice** writes `voice_chat_mode: grok-live` — the same config key `gpt-live` uses. Native Hermes `voice_chat_mode()` still treats anything that is not `gpt-live` as chained, so OpenAI WebRTC does not also start. Opening the composer waveform also POSTs `grok-live` and starts overlay duplex until Hermes ships a grok-live engine.

## Provider differences (Grok realtime vs OpenAI realtime)

Do not point Grok at OpenAI realtime, and do not point GPT-Live at xAI.

| | **Gpt-live** (OpenAI) | **Grok Voice** (xAI) |
|--|----------------------|----------------------|
| Config key | `voice.voice_chat_mode: gpt-live` | `voice.voice_chat_mode: grok-live` |
| Block | `voice.gpt_live` | `voice.grok_live` (same shape: model, voice, instructions, endpoint, turn detection) |
| Session start | `POST https://api.openai.com/v1/live/sessions` (SDP / WebRTC) | `POST https://api.x.ai/v1/realtime/client_secrets` then `wss://api.x.ai/v1/realtime?model=grok-voice-latest` |
| Transport | WebRTC; key stays on the gateway | WebSocket; browser uses `xai-client-secret.<value>` |
| Turn / barge-in | OpenAI Live interruption policy on the WebRTC session | xAI `session.update` `turn_detection.type: server_vad` |
| Auth | `OPENAI_API_KEY` or `voice.gpt_live.api_key` | `XAI_API_KEY` or xAI OAuth (never written to YAML) |
| Missing required Grok fields | n/a | Helper **fails closed** with a config error |

## What still needs a Hermes engine change

These files live in NousResearch/hermes-agent, not here. This package cannot rebuild `Hermes.exe`.

1. `methods_config_set.py` — this package patches the image at gateway start so `grok-live` is accepted beside `gpt-live` / `chained`. Upstream still ships the two-value set.
2. Desktop `voice-live.ts` (or the module that starts gpt-live) — add a `grok-live` path that mints `POST /v1/realtime/client_secrets` and opens `wss://api.x.ai/v1/realtime?model=grok-voice-latest` with `xai-client-secret.<value>`.
3. `tools/voice_live.py` — accept `grok-live` beside `gpt-live` instead of folding it into chained. Do not delete GPT-Live.

When that lands, overlay Talk can stay as fallback. Ready-to-paste prompt is at the bottom of this file.

## What James sees

**Settings → Voice → Voice conversation:** the mode dropdown lists **Chained**, **Gpt-live**, and **Grok Voice**. That is the operator picker (and the backend `voice.voice_chat_mode` switch).

Composer **GPT | Grok** pills are removed. The chat-screen control is the Grok-Bot waveform → floating capsule. Gear opens Voice settings (voice, speed, language, interrupt). Chat returns to text. Mic mutes. Red X ends the session.

| Option | What it uses | Auth |
|--------|----------------|------|
| **Chained** | Native Hermes STT → turn → TTS | Existing STT/TTS providers |
| **Gpt-live** | Upstream Hermes `voice.voice_chat_mode: gpt-live` → OpenAI `gpt-live-1` WebRTC | `OPENAI_API_KEY` or `voice.gpt_live.api_key` |
| **Grok Voice** | Overlay full duplex: `wss://api.x.ai/v1/realtime?model=grok-voice-latest` after `POST /v1/realtime/client_secrets`. Unary xAI STT/TTS is fallback only. | Existing xAI Grok login — `XAI_API_KEY` or xAI OAuth. This step does **not** ask for a new key |

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

GPT-Live stays on OpenAI `POST https://api.openai.com/v1/live/sessions` via Hermes `tools/voice_live.py`. That is OpenAI Live / WebRTC, not OpenAI realtime and not xAI. Do not replace that path.

## Config written (no secrets)

File: `%USERPROFILE%\.hermes-airmaze-embedded\config.yaml`

Selecting **Gpt-live**:

```yaml
voice:
  selected_provider: gpt
  voice_chat_mode: gpt-live
  gpt_live:
    model: gpt-live-1
    voice: marin
    instructions: ""
    endpoint: https://api.openai.com/v1/live/sessions
    transport: webrtc
  grok_live:
    model: grok-voice-latest
    voice: eve
    instructions: ""
    duplex: true
    endpoint: wss://api.x.ai/v1/realtime
    realtime: "wss://api.x.ai/v1/realtime?model=grok-voice-latest"
    client_secrets: https://api.x.ai/v1/realtime/client_secrets
    transport: websocket
    turn_detection:
      type: server_vad
```

Selecting **Grok Voice** (GPT block is kept):

```yaml
voice:
  selected_provider: grok
  voice_chat_mode: grok-live
  gpt_live:
    model: gpt-live-1
    voice: marin
    instructions: ""
    endpoint: https://api.openai.com/v1/live/sessions
    transport: webrtc
  grok_live:
    model: grok-voice-latest
    voice: eve
    instructions: ""
    duplex: true
    endpoint: wss://api.x.ai/v1/realtime
    realtime: "wss://api.x.ai/v1/realtime?model=grok-voice-latest"
    client_secrets: https://api.x.ai/v1/realtime/client_secrets
    transport: websocket
    turn_detection:
      type: server_vad
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

`voice.grok_live` mirrors `voice.gpt_live` (model, voice, instructions, endpoint, turn detection). Transport differs: Grok is xAI WebSocket + ephemeral secret; GPT-Live is OpenAI WebRTC. Native `tools/voice_live.py` still folds non-`gpt-live` into chained, so overlay owns Grok duplex. Unary xAI STT/TTS stay as fallback.

Do not write API keys into `config.yaml`. Auth stays env / Hermes Settings → Keys (`XAI_` card, `OPENAI_`).

## Helper

Loopback only: `http://127.0.0.1:8654/api/voice` (not Bot Screen `:8650`, not Teams `:8653`).

```powershell
python3 scripts/airmaze/voice_chat.py apply --provider grok-live
python3 scripts/airmaze/voice_chat.py apply --provider gpt-live
python3 scripts/airmaze/voice_chat.py apply --provider chained
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\airmaze\Apply-VoiceChat.ps1 -Provider grok-live
python3 scripts/airmaze/Test-VoiceChat.py
```

Launch starts the helper (`Start-DragonAIVoiceChat`). Settings overlay POSTs `{ "id": "chained" | "gpt-live" | "grok-live" }` to `/api/voice/selection`. The composer waveform POSTs `grok-live`, then `/api/voice/ephemeral`, then opens the official realtime WebSocket. Gear POSTs `/api/voice/prefs` (`voice`, `speed`, `language`, `interrupt`).

Gateway start runs `patch_grok_voice_mode.py` so `methods_config_set.py` accepts `grok-live` (fail-open if the image file is missing).

## How to test GPT vs Grok

1. Put `OPENAI_API_KEY` (GPT voice) and `XAI_API_KEY` or xAI OAuth (Grok voice) in Settings → Keys. No keys in this repo.
2. Start Dragon AI Agent. Open **Settings → Voice → Voice conversation**.
3. Confirm the mode dropdown lists **Chained**, **Gpt-live**, and **Grok Voice**.
4. Pick **Gpt-live**. Use the Hermes mic. Existing GPT-Live duplex (OpenAI). `voice.grok_live` stays in config.
5. Pick **Grok Voice**. Click the composer **waveform**. The floating capsule opens (avatar | purple bars | gear | chat | mic | red X). Gear must show Voice / Speed / Language. Allow the microphone. Speak — server VAD should barge in / answer without a chained STT→LLM→TTS pause.
6. Pick **Chained**. Native STT→TTS returns; both live blocks remain.
7. Offline: `python3 scripts/airmaze/Test-VoiceChat.py`.

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
- Settings → Voice → Voice conversation mode lists Grok Voice beside Chained and Gpt-live
- Writes voice.voice_chat_mode: grok-live (same key as gpt-live)
- Writes voice.grok_live (model, voice, instructions, endpoint, server_vad) and keeps voice.gpt_live
- Overlay Grok-Bot waveform capsule in branding/voice/dragon-voice-selector.js (gear Voice settings required)
- Helper 127.0.0.1:8654 POST /api/voice/ephemeral mints the token
- Chat-screen GPT | Grok pills are removed; Settings remains the mode picker

When a native grok-live engine exists, overlay Talk can stay as fallback. Draft only; do not merge packaging until James says so.
```

## Out of scope

- Replacing GPT voice
- Bringing back the chat-screen GPT | Grok pills
- Shipping a gear with no Voice / Speed controls
- Adding Grok as a new chat-screen provider picker
- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Inventing unofficial Grok URLs
- Pointing Grok at OpenAI realtime
- Merging this PR
