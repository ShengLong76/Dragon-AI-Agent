"""Grok Voice chat mode: xAI's full-duplex voice model delegating to the agent.

The contract pinned here: the long-lived xAI credential never leaves the gateway host. The
renderer receives only a short-lived client secret, the socket URL, and the session persona.
"""

import json

import pytest

from tools import voice_grok, voice_live


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _no_supergrok(monkeypatch):
    import hermes_cli.auth_xai as auth_xai

    def _missing(**_kwargs):
        raise RuntimeError("not signed in")

    monkeypatch.setattr(auth_xai, "resolve_xai_oauth_runtime_credentials", _missing)


def test_mode_parsing_accepts_grok_spellings():
    for raw in ("grok-voice", "grok_voice", "grok", "GROK-VOICE"):
        assert voice_live.voice_chat_mode({"voice_chat_mode": raw}) == voice_grok.GROK_VOICE_MODE
    assert voice_live.voice_chat_mode({"voice_chat_mode": "gpt-live"}) == voice_live.GPT_LIVE_MODE
    assert voice_live.voice_chat_mode({}) == voice_live.CHAINED_MODE


def test_status_without_credentials_is_unavailable(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    _no_supergrok(monkeypatch)
    status = voice_grok.resolve_grok_voice_status({"grok_voice": {}})
    assert status["available"] is False
    assert status["mode"] == "grok-voice"
    assert "SuperGrok" in status["reason"]


def test_session_returns_only_the_ephemeral_secret(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-long-lived-key")
    monkeypatch.setattr(voice_grok, "_grok_section", lambda voice=None: {"voice": "ara"})
    seen = {}

    def _urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _Response({"value": "ephemeral-secret", "expires_at": 123})

    monkeypatch.setattr(voice_grok.urllib.request, "urlopen", _urlopen)
    result = voice_grok.create_grok_voice_session()

    assert seen["url"] == "https://api.x.ai/v1/realtime/client_secrets"
    assert seen["auth"] == "Bearer xai-long-lived-key"
    assert seen["body"] == {"expires_after": {"seconds": voice_grok.CLIENT_SECRET_TTL_SECONDS}}
    assert result["client_secret"] == "ephemeral-secret"
    assert result["url"] == "wss://api.x.ai/v1/realtime?model=grok-voice-latest"
    assert result["voice"] == "ara"
    assert result["tool"] == voice_grok.DELEGATION_TOOL
    assert "xai-long-lived-key" not in json.dumps(result)


def test_session_without_credentials_raises_value_error(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    _no_supergrok(monkeypatch)
    monkeypatch.setattr(voice_grok, "_grok_section", lambda voice=None: {})
    with pytest.raises(ValueError):
        voice_grok.create_grok_voice_session()
