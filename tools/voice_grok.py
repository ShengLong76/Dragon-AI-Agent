"""Grok Voice chat mode: xAI's full-duplex speech-to-speech model as the voice of Dragon AI.

``voice.voice_chat_mode: grok-voice`` is the xAI counterpart of GPT-Live. One Grok voice model
owns the microphone and the speaker over a WebSocket (``wss://api.x.ai/v1/realtime``) and hands
every real request to the agent through a single client-side function, ``ask_dragon``; the
renderer turns each call into an ordinary turn on the open session and returns the reply as the
function output, which Grok speaks.

This module resolves the credential (``voice.grok_voice.api_key`` → ``XAI_API_KEY`` → the
SuperGrok OAuth grant) and mints the short-lived client secret the browser authenticates with,
so the long-lived key never reaches the renderer. Vendor contract:
https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

GROK_VOICE_MODE = "grok-voice"
DEFAULT_GROK_VOICE_MODEL = "grok-voice-latest"
DEFAULT_GROK_VOICE = "eve"
DEFAULT_GROK_VOICE_BASE_URL = "https://api.x.ai/v1"
GROK_VOICES = ("eve", "ara", "rex", "sal", "leo")
CLIENT_SECRET_TTL_SECONDS = 600
DELEGATION_TOOL = "ask_dragon"

GROK_VOICE_PERSONA = (
    "You are the voice of Dragon AI, a calm and capable assistant. Speak naturally and keep "
    "answers short unless the user asks for detail. Stop talking when the user interrupts.\n\n"
    f"You cannot do work yourself. Call the {DELEGATION_TOOL} function whenever the user asks a "
    "question that needs facts, current information, or careful reasoning, or asks you to do, "
    "check, find, make, fix, run, schedule, or remember anything. Pass their request in their own "
    "words. Do not call it for greetings, small talk, or a quick clarifying question. While you "
    "wait, say briefly that you are checking; never guess the result. When the result arrives, "
    "say it conversationally without reading out markdown, code, or URLs."
)


def _grok_section(voice: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if voice is None:
        try:
            from hermes_cli.config import load_config
            voice = load_config().get("voice")
        except Exception:
            voice = {}
    section = (voice if isinstance(voice, dict) else {}).get("grok_voice")
    return section if isinstance(section, dict) else {}


def _resolve_credentials(section: Dict[str, Any]) -> tuple[str, str, str]:
    """``(api_key, base_url, source)``; an empty key means Grok Voice cannot start."""
    base_url = str(section.get("base_url") or DEFAULT_GROK_VOICE_BASE_URL).strip().rstrip("/")
    explicit = str(section.get("api_key") or "").strip()
    if explicit:
        return explicit, base_url, "config"
    env_key = os.getenv("XAI_API_KEY", "").strip()
    if env_key:
        return env_key, base_url, "env"
    try:
        from hermes_cli.auth_xai import resolve_xai_oauth_runtime_credentials
        creds = resolve_xai_oauth_runtime_credentials()
        token = str(creds.get("api_key") or "").strip()
        if token:
            return token, base_url, "supergrok"
    except Exception as exc:
        logger.debug("Grok Voice: SuperGrok credential unavailable: %s", exc)
    return "", base_url, ""


def grok_voice_instructions(section: Optional[Dict[str, Any]] = None) -> str:
    extra = str((section if section is not None else _grok_section()).get("instructions") or "").strip()
    return f"{GROK_VOICE_PERSONA}\n\n{extra}" if extra else GROK_VOICE_PERSONA


def resolve_grok_voice_status(voice: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Non-secret readiness for the client. Never returns the key."""
    section = _grok_section(voice)
    api_key, _base, source = _resolve_credentials(section)
    return {
        "mode": GROK_VOICE_MODE,
        "available": bool(api_key),
        "reason": None if api_key else "connect SuperGrok or set XAI_API_KEY to use Grok Voice",
        "model": str(section.get("model") or DEFAULT_GROK_VOICE_MODEL),
        "voice": str(section.get("voice") or DEFAULT_GROK_VOICE),
        "credential": source or None,
    }


def create_grok_voice_session() -> Dict[str, Any]:
    """Mint a client secret and return everything the renderer needs to open the socket."""
    section = _grok_section()
    api_key, base_url, _source = _resolve_credentials(section)
    if not api_key:
        raise ValueError("Grok Voice needs SuperGrok sign-in or an xAI API key (XAI_API_KEY)")
    req = urllib.request.Request(
        f"{base_url}/realtime/client_secrets",
        data=json.dumps({"expires_after": {"seconds": CLIENT_SECRET_TTL_SECONDS}}).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            secret = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:600]
        logger.warning("Grok Voice client secret failed: %s %s", exc.code, detail)
        raise RuntimeError(f"Grok Voice session creation failed ({exc.code}): {detail}") from exc
    value = str(secret.get("value") or "").strip()
    if not value:
        raise RuntimeError("Grok Voice session creation failed: no client secret returned")
    model = str(section.get("model") or DEFAULT_GROK_VOICE_MODEL)
    ws_base = base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    return {
        "client_secret": value,
        "expires_at": secret.get("expires_at"),
        "url": f"{ws_base}/realtime?model={model}",
        "model": model,
        "voice": str(section.get("voice") or DEFAULT_GROK_VOICE),
        "instructions": grok_voice_instructions(section),
        "tool": DELEGATION_TOOL,
    }
