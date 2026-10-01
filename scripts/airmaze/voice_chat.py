#!/usr/bin/env python3
"""Dragon AI Agent voice chat: GPT and Grok as coexisting selectable options.

Upstream Hermes voice chat is ``voice.voice_chat_mode: chained | gpt-live``.
``gpt-live`` is the existing OpenAI GPT voice path (``gpt-live-1``). This
module ADDS Grok voice beside it. It never removes or replaces GPT.

Grok full duplex uses documented xAI Voice APIs (not invented):

    * STS  wss://api.x.ai/v1/realtime?model=grok-voice-latest
    * Token POST https://api.x.ai/v1/realtime/client_secrets
    * TTS  POST https://api.x.ai/v1/tts  (unary fallback)
    * STT  POST https://api.x.ai/v1/stt  (model grok-voice-transcribe-2.0)

The Electron overlay hosts Grok duplex (Talk with Grok). This helper mints
the ephemeral token so the renderer never sees ``XAI_API_KEY``. Selecting
Grok still writes ``voice_chat_mode: chained`` because Hermes rejects
``grok-live`` today — that keeps native gpt-live from starting at the same
time. Unary xAI STT/TTS stay as fallback if the helper/key is missing.

Selecting GPT writes ``gpt-live`` and leaves the Grok/xAI blocks in place.

Stdlib only. Loopback helper binds 127.0.0.1:8654 (not Bot Screen :8650,
not Teams :8653).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gateway_models as gm  # noqa: E402

VOICE_HOST = "127.0.0.1"
VOICE_PORT = 8654
CONFIG_NAME = gm.CONFIG_NAME
PROVIDER_GPT = "gpt"
PROVIDER_GROK = "grok"
DEFAULT_PROVIDER = PROVIDER_GPT

# Official xAI Voice endpoints — https://docs.x.ai/developers/model-capabilities/audio/voice
XAI_API_BASE = "https://api.x.ai/v1"
XAI_TTS_URL = f"{XAI_API_BASE}/tts"
XAI_STT_URL = f"{XAI_API_BASE}/stt"
XAI_STT_STREAM_URL = "wss://api.x.ai/v1/stt"
XAI_REALTIME_URL = "wss://api.x.ai/v1/realtime"
XAI_CLIENT_SECRETS_URL = f"{XAI_API_BASE}/realtime/client_secrets"
XAI_STT_MODEL = "grok-voice-transcribe-2.0"
XAI_VOICE_MODEL = "grok-voice-latest"
XAI_DEFAULT_VOICE = "eve"
XAI_DEFAULT_LANGUAGE = "en"
XAI_PCM_RATE = 24000
XAI_AUDIO_FORMAT = {"type": "audio/pcm", "rate": XAI_PCM_RATE}
XAI_WS_PROTOCOL_PREFIX = "xai-client-secret."
GROK_LIVE_MODE = "grok-live"

# Official OpenAI GPT-Live — Hermes tools/voice_live.py
OPENAI_LIVE_BASE = "https://api.openai.com/v1"
OPENAI_LIVE_MODEL = "gpt-live-1"
OPENAI_LIVE_VOICE = "marin"
OPENAI_LIVE_MODE = "gpt-live"
CHAINED_MODE = "chained"

DOCS = {
    "voice": "https://docs.x.ai/developers/model-capabilities/audio/voice",
    "tts": "https://docs.x.ai/developers/model-capabilities/audio/text-to-speech",
    "stt": "https://docs.x.ai/developers/model-capabilities/audio/speech-to-text",
    "sts": "https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech",
    "ephemeral": "https://docs.x.ai/developers/model-capabilities/audio/ephemeral-tokens",
    "gpt_live": "https://developers.openai.com/api/docs/guides/live-delegation",
}

PROVIDERS: list[dict[str, Any]] = [
    {
        "id": PROVIDER_GPT,
        "label": "GPT",
        "title": "GPT voice",
        "vendor": "openai",
        "kind": "full-duplex",
        "voiceChatMode": OPENAI_LIVE_MODE,
        "model": OPENAI_LIVE_MODEL,
        "voice": OPENAI_LIVE_VOICE,
        "auth": ["OPENAI_API_KEY", "voice.gpt_live.api_key"],
        "endpoints": {
            "sessions": f"{OPENAI_LIVE_BASE}/live/sessions",
        },
        "docs": DOCS["gpt_live"],
        "notes": "Existing Hermes GPT-Live path. Do not remove.",
    },
    {
        "id": PROVIDER_GROK,
        "label": "Grok",
        "title": "Grok voice",
        "vendor": "xai",
        "kind": "full-duplex",
        "voiceChatMode": CHAINED_MODE,
        "targetVoiceChatMode": GROK_LIVE_MODE,
        "duplexHost": "overlay",
        "model": XAI_VOICE_MODEL,
        "sttModel": XAI_STT_MODEL,
        "voice": XAI_DEFAULT_VOICE,
        "language": XAI_DEFAULT_LANGUAGE,
        "auth": ["XAI_API_KEY", "xAI OAuth already on this PC"],
        "endpoints": {
            "tts": XAI_TTS_URL,
            "stt": XAI_STT_URL,
            "sttStream": XAI_STT_STREAM_URL,
            "realtime": f"{XAI_REALTIME_URL}?model={XAI_VOICE_MODEL}",
            "clientSecrets": XAI_CLIENT_SECRETS_URL,
        },
        "duplex": {
            "realtime": f"{XAI_REALTIME_URL}?model={XAI_VOICE_MODEL}",
            "clientSecrets": XAI_CLIENT_SECRETS_URL,
            "wsProtocolPrefix": XAI_WS_PROTOCOL_PREFIX,
            "turnDetection": {"type": "server_vad"},
            "audio": {
                "input": {"format": dict(XAI_AUDIO_FORMAT)},
                "output": {"format": dict(XAI_AUDIO_FORMAT)},
            },
        },
        "docs": DOCS["sts"],
        "notes": (
            "xAI Grok Voice full duplex (grok-voice-latest). Overlay Talk with "
            "Grok mints POST /v1/realtime/client_secrets and opens the documented "
            "WebSocket. Hermes voice_chat_mode stays chained so native gpt-live "
            "does not also start. Unary STT/TTS remain fallback if the helper "
            "or key is missing."
        ),
        "upstreamLimitation": (
            "Hermes voice.voice_chat_mode only accepts chained|gpt-live "
            "(methods_config_set.py). voice-live.ts / tools/voice_live.py must "
            "accept grok-live beside gpt-live before this package can write "
            "voice_chat_mode: grok-live. Until then the Electron overlay hosts duplex."
        ),
    },
]


def provider_catalog() -> list[dict[str, Any]]:
    return [dict(row) for row in PROVIDERS]


def _lookup(provider_id: str) -> dict[str, Any]:
    want = str(provider_id or "").strip().lower().replace("_", "-")
    aliases = {
        "gpt": PROVIDER_GPT,
        "gpt-live": PROVIDER_GPT,
        "gptlive": PROVIDER_GPT,
        "openai": PROVIDER_GPT,
        "grok": PROVIDER_GROK,
        "grok-live": PROVIDER_GROK,
        "groklive": PROVIDER_GROK,
        "xai": PROVIDER_GROK,
        "x-ai": PROVIDER_GROK,
    }
    want = aliases.get(want, want)
    for row in PROVIDERS:
        if row["id"] == want:
            return dict(row)
    raise ValueError(f"unknown voice provider {provider_id!r}; pick gpt or grok")


def default_embedded_home() -> Path:
    return gm.default_embedded_home()


def config_path(home: Path | str) -> Path:
    return gm.config_path(home)


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if text == "" or any(ch in text for ch in (":", "#", "'", '"')):
        return json.dumps(text)
    return text


def _yaml_map(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    pad = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            nested = _yaml_map(value, indent + 1).rstrip()
            if nested:
                lines.append(nested)
        else:
            lines.append(f"{pad}{key}: {_yaml_scalar(value)}")
    return ("\n".join(lines) + "\n") if lines else ""


def _as_map(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def current_selection(parsed: dict[str, Any]) -> str:
    voice = _as_map(parsed.get("voice"))
    raw = str(voice.get("selected_provider") or "").strip().lower()
    if raw in {PROVIDER_GPT, PROVIDER_GROK}:
        return raw
    mode = str(voice.get("voice_chat_mode") or "").strip().lower().replace("_", "-")
    if mode in {OPENAI_LIVE_MODE, "gptlive", "live"}:
        return PROVIDER_GPT
    stt = str(_as_map(parsed.get("stt")).get("provider") or "").strip().lower()
    tts = str(_as_map(parsed.get("tts")).get("provider") or "").strip().lower()
    if stt == "xai" or tts == "xai":
        return PROVIDER_GROK
    return DEFAULT_PROVIDER


def _merge_keep(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    out = dict(existing)
    for key, value in updates.items():
        if isinstance(value, dict):
            out[key] = _merge_keep(_as_map(out.get(key)), value)
        else:
            out[key] = value
    return out


def voice_blocks_for(provider_id: str, parsed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build voice/stt/tts maps. GPT settings survive a Grok select and vice versa."""
    choice = _lookup(provider_id)
    existing_voice = _as_map(parsed.get("voice"))
    existing_stt = _as_map(parsed.get("stt"))
    existing_tts = _as_map(parsed.get("tts"))
    gpt_live = _merge_keep(
        {"model": OPENAI_LIVE_MODEL, "voice": OPENAI_LIVE_VOICE},
        _as_map(existing_voice.get("gpt_live")),
    )
    grok_live = _merge_keep(
        {
            "model": XAI_VOICE_MODEL,
            "voice": XAI_DEFAULT_VOICE,
            "duplex": True,
            "realtime": realtime_session_url(),
        },
        _as_map(existing_voice.get("grok_live")),
    )
    voice = _merge_keep(
        existing_voice,
        {
            "selected_provider": choice["id"],
            "voice_chat_mode": choice["voiceChatMode"],
            "gpt_live": gpt_live,
            "grok_live": grok_live,
        },
    )
    stt = dict(existing_stt)
    tts = dict(existing_tts)
    if choice["id"] == PROVIDER_GROK:
        stt = _merge_keep(
            stt,
            {
                "enabled": True,
                "provider": "xai",
                "xai": _merge_keep(_as_map(stt.get("xai")), {"model": XAI_STT_MODEL}),
            },
        )
        tts = _merge_keep(
            tts,
            {
                "provider": "xai",
                "xai": _merge_keep(
                    _as_map(tts.get("xai")),
                    {"voice_id": XAI_DEFAULT_VOICE, "language": XAI_DEFAULT_LANGUAGE},
                ),
            },
        )
    return {"voice": voice, "stt": stt, "tts": tts}


def apply_voice_provider(home: Path | str, provider_id: str) -> dict[str, Any]:
    choice = _lookup(provider_id)
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    parsed = gm._simple_load(existing) if existing.strip() else {}
    blocks = voice_blocks_for(choice["id"], parsed)
    text = existing
    for key in ("voice", "stt", "tts"):
        text = gm._upsert_block(text, key, f"{key}:\n{_yaml_map(blocks[key], 1)}")
    if not text.endswith("\n"):
        text += "\n"
    for block in blocks.values():
        dumped = _yaml_map(block).lower()
        if "api_key:" in dumped or "xai_api_key:" in dumped or "openai_api_key:" in dumped:
            raise ValueError("refuse to write API keys into config.yaml")
    path.write_text(text, encoding="utf-8")
    final = gm._simple_load(path.read_text(encoding="utf-8"))
    return {
        "ok": True,
        "path": str(path),
        "provider": choice["id"],
        "label": choice["label"],
        "voiceChatMode": str(gm._nested_get(final, "voice", "voice_chat_mode") or choice["voiceChatMode"]),
        "keptGptLive": bool(gm._nested_get(final, "voice", "gpt_live")),
        "keptGrokLive": bool(gm._nested_get(final, "voice", "grok_live")),
        "sttProvider": str(gm._nested_get(final, "stt", "provider") or ""),
        "ttsProvider": str(gm._nested_get(final, "tts", "provider") or ""),
        "duplexHost": "overlay" if choice["id"] == PROVIDER_GROK else "hermes-gpt-live",
        "targetVoiceChatMode": choice.get("targetVoiceChatMode") or choice["voiceChatMode"],
    }


def tts_request(text: str, voice_id: str = XAI_DEFAULT_VOICE, language: str = XAI_DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Unary Grok TTS body — docs.x.ai text-to-speech."""
    return {
        "url": XAI_TTS_URL,
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "json": {
            "text": text,
            "voice_id": voice_id or XAI_DEFAULT_VOICE,
            "language": language or XAI_DEFAULT_LANGUAGE,
        },
    }


def stt_request(filename: str = "recording.webm", model: str = XAI_STT_MODEL) -> dict[str, Any]:
    """Unary Grok STT — multipart; file must be last field."""
    return {
        "url": XAI_STT_URL,
        "method": "POST",
        "multipart": True,
        "fields": [
            ("model", model or XAI_STT_MODEL),
            ("format", "true"),
            ("language", XAI_DEFAULT_LANGUAGE),
            ("file", filename),
        ],
    }


def realtime_session_url(model: str = XAI_VOICE_MODEL) -> str:
    return f"{XAI_REALTIME_URL}?model={model or XAI_VOICE_MODEL}"


def realtime_session_update(voice: str = XAI_DEFAULT_VOICE, instructions: str = "") -> dict[str, Any]:
    """Official STS session.update — docs.x.ai speech-to-speech defaults."""
    session: dict[str, Any] = {
        "voice": voice or XAI_DEFAULT_VOICE,
        "turn_detection": {"type": "server_vad"},
        "audio": {
            "input": {"format": dict(XAI_AUDIO_FORMAT)},
            "output": {"format": dict(XAI_AUDIO_FORMAT)},
        },
    }
    if str(instructions or "").strip():
        session["instructions"] = str(instructions).strip()
    return {"type": "session.update", "session": session}


def input_audio_buffer_append(audio_b64: str) -> dict[str, Any]:
    """Official JSON transport: base64 PCM in input_audio_buffer.append."""
    return {"type": "input_audio_buffer.append", "audio": str(audio_b64 or "")}


def client_secrets_request(expires_seconds: int = 300) -> dict[str, Any]:
    return {
        "url": XAI_CLIENT_SECRETS_URL,
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "json": {"expires_after": {"seconds": int(expires_seconds)}},
    }


def read_dotenv_key(home: Path | str, name: str = "XAI_API_KEY") -> str:
    """Read NAME= from the embedded home .env. Never returns surrounding secrets."""
    env_path = Path(home) / ".env"
    if not env_path.is_file():
        return ""
    prefix = f"{name}="
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith(prefix):
                return line.split("=", 1)[1].strip().strip("'\"")
    except OSError:
        return ""
    return ""


def resolve_xai_api_key(home: Path | str | None = None) -> str:
    env = str(os.environ.get("XAI_API_KEY") or "").strip()
    if env:
        return env
    if home is not None:
        return read_dotenv_key(home, "XAI_API_KEY")
    return read_dotenv_key(default_embedded_home(), "XAI_API_KEY")


def _ephemeral_value(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    raw = payload.get("value")
    if raw:
        return str(raw)
    token = payload.get("token")
    if isinstance(token, dict) and token.get("value"):
        return str(token["value"])
    return ""


def mint_ephemeral_token(
    api_key: str | None = None,
    home: Path | str | None = None,
    opener: Any = None,
) -> dict[str, Any]:
    """POST /v1/realtime/client_secrets. Returns value + realtime URL, never the API key."""
    key = str(api_key or resolve_xai_api_key(home)).strip()
    if not key:
        return {
            "ok": False,
            "error": "missing_xai_key",
            "message": "Set XAI_API_KEY or keep the existing xAI Grok login. Do not paste a key into the desktop UI.",
            "docs": DOCS["ephemeral"],
            "realtimeUrl": realtime_session_url(),
            "session": realtime_session_update(),
        }
    spec = client_secrets_request()
    body = json.dumps(spec["json"]).encode("utf-8")
    req = urllib.request.Request(
        spec["url"],
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    fetch = opener or urllib.request.urlopen
    try:
        with fetch(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        return {"ok": False, "error": f"http_{exc.code}", "message": detail, "docs": DOCS["ephemeral"]}
    except (OSError, json.JSONDecodeError, TimeoutError) as exc:
        return {"ok": False, "error": type(exc).__name__, "message": str(exc), "docs": DOCS["ephemeral"]}
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "error": "invalid_token_body",
            "message": "xAI client_secrets response was not an object.",
            "docs": DOCS["ephemeral"],
        }
    dumped = json.dumps(payload)
    if key and key in dumped:
        payload = {k: v for k, v in payload.items() if v != key}
    value = _ephemeral_value(payload)
    if not value:
        return {
            "ok": False,
            "error": "missing_token_value",
            "message": "xAI client_secrets response had no value field.",
            "docs": DOCS["ephemeral"],
        }
    return {
        "ok": True,
        "value": value,
        "expires_at": payload.get("expires_at"),
        "token": payload,
        "realtimeUrl": realtime_session_url(),
        "session": realtime_session_update(),
        "wsProtocolPrefix": XAI_WS_PROTOCOL_PREFIX,
        "docs": DOCS["ephemeral"],
    }


def selection_payload(home: Path | str) -> dict[str, Any]:
    path = config_path(home)
    parsed = gm._simple_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current = current_selection(parsed)
    return {
        "ok": True,
        "provider": current,
        "providers": provider_catalog(),
        "path": str(path),
        "hasXaiKey": bool(resolve_xai_api_key(Path(home))),
        "docs": DOCS,
    }


def _json_bytes(data: Any, status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(data) + "\n").encode("utf-8")


def make_handler(home: Path) -> type[BaseHTTPRequestHandler]:
    class VoiceHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send(204, b"")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/api/voice/providers", "/voice/providers"):
                status, body = _json_bytes({"ok": True, "providers": provider_catalog()})
                self._send(status, body)
                return
            if path in ("/api/voice/selection", "/voice/selection", "/api/voice", "/voice"):
                status, body = _json_bytes(selection_payload(home))
                self._send(status, body)
                return
            if path in ("/api/health", "/health"):
                self._send(200, b'{"ok":true,"service":"dragon-voice"}\n')
                return
            self._send(404, b'{"error":"not found"}\n')

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send(400, b'{"error":"invalid json"}\n')
                return
            if not isinstance(data, dict):
                data = {}
            try:
                if path in ("/api/voice/selection", "/voice/selection", "/api/voice/select", "/voice/select"):
                    provider_id = str(data.get("id") or data.get("provider") or "").strip()
                    result = apply_voice_provider(home, provider_id)
                    status, body = _json_bytes(result)
                    self._send(status, body)
                    return
                if path in ("/api/voice/ephemeral", "/voice/ephemeral"):
                    result = mint_ephemeral_token(home=home)
                    status, body = _json_bytes(result, 200 if result.get("ok") else 400)
                    self._send(status, body)
                    return
            except Exception as exc:  # noqa: BLE001 — HTTP boundary
                status, body = _json_bytes({"error": type(exc).__name__, "message": str(exc)}, 400)
                self._send(status, body)
                return
            self._send(404, b'{"error":"not found"}\n')

    return VoiceHandler


def serve(home: Path | str, host: str = VOICE_HOST, port: int = VOICE_PORT) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("voice helper binds loopback only")
    if port in {8650, 8653}:
        raise ValueError("voice helper must not take Bot Screen :8650 or Teams :8653")
    httpd = ThreadingHTTPServer((host, port), make_handler(Path(home)))
    print(f"Dragon AI voice helper on http://{host}:{port}/api/voice", flush=True)
    httpd.serve_forever()


def self_test() -> int:
    ids = [row["id"] for row in provider_catalog()]
    if ids != [PROVIDER_GPT, PROVIDER_GROK]:
        print(f"self-test: catalog must be gpt then grok, got {ids}", file=sys.stderr)
        return 1
    if VOICE_PORT in {8650, 8653}:
        print("self-test: voice port collides with Bot Screen or Teams", file=sys.stderr)
        return 1
    tts = tts_request("Hello from Dragon AI.")
    if tts["url"] != XAI_TTS_URL or tts["json"]["voice_id"] != "eve":
        print(f"self-test: TTS spec drifted: {tts}", file=sys.stderr)
        return 1
    stt = stt_request()
    if stt["url"] != XAI_STT_URL or stt["fields"][0] != ("model", XAI_STT_MODEL):
        print(f"self-test: STT spec drifted: {stt}", file=sys.stderr)
        return 1
    if stt["fields"][-1][0] != "file":
        print("self-test: STT file field must be last", file=sys.stderr)
        return 1
    if "grok-voice-latest" not in realtime_session_url():
        print("self-test: realtime URL must name grok-voice-latest", file=sys.stderr)
        return 1
    update = realtime_session_update()
    audio = (update.get("session") or {}).get("audio") or {}
    if (audio.get("input") or {}).get("format") != XAI_AUDIO_FORMAT:
        print(f"self-test: session.update must use official PCM 24000: {update}", file=sys.stderr)
        return 1
    if (update.get("session") or {}).get("turn_detection") != {"type": "server_vad"}:
        print(f"self-test: session.update must use server_vad: {update}", file=sys.stderr)
        return 1
    append = input_audio_buffer_append("Zg==")
    if append != {"type": "input_audio_buffer.append", "audio": "Zg=="}:
        print(f"self-test: input_audio_buffer.append drifted: {append}", file=sys.stderr)
        return 1
    grok = next(row for row in provider_catalog() if row["id"] == PROVIDER_GROK)
    if grok.get("kind") != "full-duplex" or grok.get("duplexHost") != "overlay":
        print(f"self-test: Grok catalog must be overlay full-duplex, got {grok}", file=sys.stderr)
        return 1
    secrets = client_secrets_request()
    if secrets["url"] != XAI_CLIENT_SECRETS_URL or secrets["json"] != {"expires_after": {"seconds": 300}}:
        print(f"self-test: client_secrets spec drifted: {secrets}", file=sys.stderr)
        return 1
    if "session" in secrets["json"]:
        print("self-test: client_secrets must not send unsupported session field", file=sys.stderr)
        return 1
    try:
        _lookup("nope")
        print("self-test: unknown provider must raise", file=sys.stderr)
        return 1
    except ValueError:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dragon AI Agent GPT + Grok voice selector")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("catalog")
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("--home", default="")
    apply_p.add_argument("--provider", required=True, help="gpt or grok")
    sel_p = sub.add_parser("selection")
    sel_p.add_argument("--home", default="")
    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--home", default="")
    serve_p.add_argument("--host", default=VOICE_HOST)
    serve_p.add_argument("--port", type=int, default=VOICE_PORT)
    args = parser.parse_args(argv)
    if args.self_test or args.cmd is None and not argv:
        return self_test()
    if args.cmd == "catalog":
        print(json.dumps({"providers": provider_catalog()}, indent=2))
        return 0
    home = Path(args.home) if str(getattr(args, "home", "") or "").strip() else default_embedded_home()
    if args.cmd == "apply":
        print(json.dumps(apply_voice_provider(home, args.provider), indent=2))
        return 0
    if args.cmd == "selection":
        print(json.dumps(selection_payload(home), indent=2))
        return 0
    if args.cmd == "serve":
        serve(home, host=args.host, port=args.port)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
