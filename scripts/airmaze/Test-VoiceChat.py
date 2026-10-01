#!/usr/bin/env python3
"""Tests first: GPT voice stays; Grok is overlay full-duplex beside it.

James: ChatGPT voice is duplex. Grok must feel the same via official
wss://api.x.ai/v1/realtime?model=grok-voice-latest — not only chained
STT→LLM→TTS. Endpoints must match public xAI docs. No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
ENGINE = SCRIPTS / "voice_chat.py"
APPLY = SCRIPTS / "Apply-VoiceChat.ps1"
BRANDING = SCRIPTS / "desktop_branding.py"
TABLE = SCRIPTS / "desktop_branding.json"
CSS = ROOT / "branding" / "fonts" / "syne" / "dragon-ui.css"
VOICE_JS = ROOT / "branding" / "voice" / "dragon-voice-selector.js"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
FINDER = SCRIPTS / "Find-HermesDesktop.ps1"
INSTALL = SCRIPTS / "install.ps1"
SETUP = ROOT / "installer" / "DragonAIAgentSetup.ps1"
DOCS = ROOT / "docs" / "airmaze" / "VOICE.md"
SETUP_GUIDE = ROOT / "docs" / "airmaze" / "SETUP_GUIDE.md"
BRANDING_DOC = ROOT / "docs" / "airmaze" / "BRANDING.md"
CHANGELOG = ROOT / "CHANGELOG.md"

OFFICIAL = {
    "tts": "https://api.x.ai/v1/tts",
    "stt": "https://api.x.ai/v1/stt",
    "realtime": "wss://api.x.ai/v1/realtime",
    "secrets": "https://api.x.ai/v1/realtime/client_secrets",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_engine():
    if not ENGINE.is_file():
        fail("voice_chat.py must exist")
    sys.path.insert(0, str(SCRIPTS))
    import voice_chat as vc  # noqa: WPS433

    return vc


def _mapping(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if ":" not in raw:
            continue
        key, _, rest = raw.lstrip(" ").partition(":")
        key = key.strip()
        value = rest.strip().strip("'\"")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = value
        else:
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def test_catalog_keeps_both(vc) -> None:
    ids = [row["id"] for row in vc.provider_catalog()]
    if ids != ["gpt", "grok"]:
        fail(f"catalog must list gpt then grok (GPT stays first-class), got {ids}")
    labels = [row["label"] for row in vc.provider_catalog()]
    if "GPT" not in labels or "Grok" not in labels:
        fail("both GPT and Grok labels must be present")
    gpt = next(row for row in vc.provider_catalog() if row["id"] == "gpt")
    grok = next(row for row in vc.provider_catalog() if row["id"] == "grok")
    if gpt["voiceChatMode"] != "gpt-live" or gpt["model"] != "gpt-live-1":
        fail(f"GPT option must stay Hermes gpt-live / gpt-live-1, got {gpt}")
    if grok["endpoints"]["tts"] != OFFICIAL["tts"]:
        fail(f"Grok TTS must be the documented xAI URL, got {grok['endpoints']}")
    if grok["endpoints"]["stt"] != OFFICIAL["stt"]:
        fail("Grok STT must be https://api.x.ai/v1/stt")
    if OFFICIAL["realtime"] not in grok["endpoints"]["realtime"]:
        fail("Grok realtime must use wss://api.x.ai/v1/realtime")
    if "grok-voice-latest" not in grok["endpoints"]["realtime"]:
        fail("Grok realtime must select grok-voice-latest")
    if grok["endpoints"]["clientSecrets"] != OFFICIAL["secrets"]:
        fail("ephemeral tokens must use /v1/realtime/client_secrets")
    if grok["sttModel"] != "grok-voice-transcribe-2.0":
        fail("STT model must be grok-voice-transcribe-2.0")
    if grok["voice"] != "eve":
        fail("default Grok voice_id must be eve")
    if grok.get("kind") != "full-duplex":
        fail("Grok catalog kind must be full-duplex, not chained-only")
    if grok.get("duplexHost") != "overlay":
        fail("this repo hosts Grok duplex in the Electron overlay")
    if grok.get("targetVoiceChatMode") != "grok-live":
        fail("catalog must name the Hermes leftover target grok-live")
    duplex = grok.get("duplex") or {}
    if duplex.get("wsProtocolPrefix") != "xai-client-secret.":
        fail("browser WS must use official xai-client-secret. prefix")
    if (duplex.get("audio") or {}).get("input") != {"format": {"type": "audio/pcm", "rate": 24000}}:
        fail(f"duplex audio must match official PCM 24000, got {duplex}")
    print("OK  catalog keeps GPT and adds documented Grok duplex endpoints")


def test_request_builders_match_docs(vc) -> None:
    tts = vc.tts_request("Welcome to Dragon AI.")
    if tts["url"] != OFFICIAL["tts"] or tts["json"]["language"] != "en":
        fail(f"TTS request drifted from xAI docs: {tts}")
    if "model" in tts["json"]:
        fail("unary TTS docs use text/voice_id/language — do not invent a model field")
    stt = vc.stt_request("clip.webm")
    names = [name for name, _ in stt["fields"]]
    if names[-1] != "file":
        fail("xAI STT requires file as the last multipart field")
    if ("model", "grok-voice-transcribe-2.0") not in stt["fields"]:
        fail("STT must send grok-voice-transcribe-2.0")
    secrets = vc.client_secrets_request(300)
    if secrets["url"] != OFFICIAL["secrets"]:
        fail("client_secrets URL drifted")
    if secrets["json"] != {"expires_after": {"seconds": 300}}:
        fail(f"client_secrets body must match docs, got {secrets['json']}")
    update = vc.realtime_session_update("eve", "You are Dragon AI.")
    if update["type"] != "session.update" or update["session"]["voice"] != "eve":
        fail(f"realtime session.update drifted: {update}")
    if update["session"]["turn_detection"] != {"type": "server_vad"}:
        fail(f"session.update must use official server_vad: {update}")
    if update["session"]["audio"]["input"]["format"] != {"type": "audio/pcm", "rate": 24000}:
        fail(f"session.update input must be official audio/pcm 24000: {update}")
    if update["session"]["audio"]["output"]["format"] != {"type": "audio/pcm", "rate": 24000}:
        fail(f"session.update output must be official audio/pcm 24000: {update}")
    append = vc.input_audio_buffer_append("Zg==")
    if append != {"type": "input_audio_buffer.append", "audio": "Zg=="}:
        fail(f"input_audio_buffer.append drifted: {append}")
    print("OK  request builders match public xAI Voice docs")


def test_apply_does_not_replace_gpt(vc) -> None:
    with tempfile.TemporaryDirectory(prefix="dragon-voice-") as tmp:
        home = pathlib.Path(tmp)
        gpt = vc.apply_voice_provider(home, "gpt")
        cfg = home / "config.yaml"
        data = _mapping(cfg.read_text(encoding="utf-8"))
        voice = data.get("voice") or {}
        if voice.get("voice_chat_mode") != "gpt-live":
            fail(f"GPT select must write gpt-live, got {voice}")
        if voice.get("selected_provider") != "gpt":
            fail("GPT select must record selected_provider gpt")
        if not isinstance(voice.get("gpt_live"), dict):
            fail("GPT select must keep a gpt_live block")
        if not isinstance(voice.get("grok_live"), dict):
            fail("GPT select must still store grok_live so Grok remains selectable")
        grok = vc.apply_voice_provider(home, "grok")
        text = cfg.read_text(encoding="utf-8")
        data = _mapping(text)
        voice = data.get("voice") or {}
        if "gpt_live" not in voice:
            fail("selecting Grok must not delete voice.gpt_live")
        if voice.get("selected_provider") != "grok":
            fail("Grok select must record selected_provider grok")
        if voice.get("voice_chat_mode") != "chained":
            fail("Grok select writes chained until Hermes accepts grok-live")
        grok_live = voice.get("grok_live") or {}
        if str(grok_live.get("duplex")).lower() not in {"true", "1"}:
            fail("Grok select must record grok_live.duplex so overlay hosts STS")
        if "grok-voice-latest" not in str(grok_live.get("realtime") or ""):
            fail("grok_live.realtime must name grok-voice-latest")
        if grok.get("duplexHost") != "overlay":
            fail("apply must report overlay as the Grok duplex host")
        if (data.get("stt") or {}).get("provider") != "xai":
            fail("Grok select must set stt.provider xai")
        if (data.get("tts") or {}).get("provider") != "xai":
            fail("Grok select must set tts.provider xai")
        xai_tts = (data.get("tts") or {}).get("xai") or {}
        if xai_tts.get("voice_id") != "eve":
            fail(f"Grok TTS voice_id must be eve, got {xai_tts}")
        lowered = text.lower()
        if "api_key:" in lowered or "xai_api_key:" in lowered or "openai_api_key:" in lowered:
            fail("apply must not write API keys into config.yaml")
        again = vc.apply_voice_provider(home, "gpt")
        data = _mapping(cfg.read_text(encoding="utf-8"))
        voice = data.get("voice") or {}
        if voice.get("voice_chat_mode") != "gpt-live":
            fail("switching back to GPT must restore gpt-live")
        if "grok_live" not in voice:
            fail("switching back to GPT must keep grok_live")
        if again.get("keptGrokLive") is not True or grok.get("keptGptLive") is not True:
            fail(f"both provider blocks must survive switches: {gpt} {grok} {again}")
    print("OK  apply switches GPT/Grok without deleting the other")


def test_no_invented_endpoints(vc) -> None:
    banned = (
        "api.grok.x.ai",
        "voice.grok.com",
        "/v1/audio/speech",
        "/v1/audio/transcriptions",
        "grok-tts-unofficial",
    )
    blob = json.dumps(vc.provider_catalog()) + json.dumps(vc.tts_request("x")) + json.dumps(vc.stt_request())
    for needle in banned:
        if needle in blob:
            fail(f"invented/wrong endpoint leaked: {needle}")
    src = read(ENGINE)
    for official in OFFICIAL.values():
        if official not in src:
            fail(f"voice_chat.py must cite {official}")
    print("OK  no invented Grok endpoints")


def test_ephemeral_token_shape(vc) -> None:
    missing = vc.mint_ephemeral_token(api_key="")
    if missing.get("ok") is not False or missing.get("error") != "missing_xai_key":
        fail(f"missing key must fail closed: {missing}")
    if missing.get("realtimeUrl") != "wss://api.x.ai/v1/realtime?model=grok-voice-latest":
        fail("missing-key payload must still name the official realtime URL")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"value": "tok_test", "expires_at": 99}).encode("utf-8")

    def opener(req, timeout=20):
        if getattr(req, "full_url", "") != OFFICIAL["secrets"] and req.get_full_url() != OFFICIAL["secrets"]:
            fail(f"ephemeral must POST official client_secrets, got {req.full_url}")
        return _Resp()

    minted = vc.mint_ephemeral_token(api_key="sk-test-not-real", opener=opener)
    if minted.get("ok") is not True or minted.get("value") != "tok_test":
        fail(f"mint must surface vendor value: {minted}")
    if minted.get("realtimeUrl") != "wss://api.x.ai/v1/realtime?model=grok-voice-latest":
        fail(f"mint must return official realtime URL: {minted}")
    if minted.get("session", {}).get("type") != "session.update":
        fail("mint must include official session.update for the overlay")
    if "sk-test-not-real" in json.dumps(minted):
        fail("mint must never echo the API key")
    print("OK  ephemeral token returns value + realtimeUrl, never the API key")


def test_overlay_selector_coexists(vc) -> None:
    sys.path.insert(0, str(SCRIPTS))
    import desktop_branding as db  # noqa: WPS433

    script = db.voice_provider_script()
    if 'data-dragon-ai-branding="voice-provider"' not in script:
        fail("overlay must mark the voice-provider script")
    if "GPT" not in script or "Grok" not in script:
        fail("overlay script must render both GPT and Grok options")
    if script.lower().count("gpt") < 1:
        fail("overlay must keep a GPT control")
    if "127.0.0.1:8654" not in script:
        fail("overlay must call the voice helper on :8654")
    if "8650" in script:
        fail("voice helper must not collide with Bot Screen :8650")
    if "Talk with Grok" not in script:
        fail("overlay must expose Talk with Grok for duplex")
    if "xai-client-secret." not in script:
        fail("overlay must authenticate the browser WS with xai-client-secret.")
    if "input_audio_buffer.append" not in script:
        fail("overlay must stream mic via official input_audio_buffer.append")
    if "wss://api.x.ai/v1/realtime?model=grok-voice-latest" not in script:
        fail("overlay must target official grok-voice-latest realtime")
    if "/api/voice/ephemeral" not in script:
        fail("overlay must mint the token through the helper, not with XAI_API_KEY")
    js = read(VOICE_JS)
    if "Talk with Grok" not in js or "xai-client-secret." not in js:
        fail("branding/voice/dragon-voice-selector.js must host duplex")
    if "Start conversation" not in js or "findComposerAction" not in js:
        fail("Talk with Grok must integrate Start conversation into the composer action")
    if "data-dragon-ai-composer-action" not in js:
        fail("Start conversation must mount in data-dragon-ai-composer-action")
    html = "<html><head></head><body></body></html>"
    once, changed = db.inject_html_branding(html)
    twice, changed2 = db.inject_html_branding(once)
    if not changed or changed2:
        fail("voice script inject must be part of html branding and idempotent")
    if once.count('data-dragon-ai-branding="voice-provider"') != 1:
        fail("voice script must inject exactly once")
    if "GPT" not in once or "Grok" not in once:
        fail("injected HTML must contain both GPT and Grok")
    css = read(CSS)
    if "[data-dragon-voice-provider]" not in css:
        fail("dragon-ui.css must style the voice provider control")
    if "aria-checked" not in css and "[aria-checked=" not in css:
        fail("voice selector CSS must style the selected option")
    if "[data-dragon-grok-talk]" not in css:
        fail("dragon-ui.css must style Talk with Grok")
    if "dragon-ai-composer-chrome:1" not in css or "[data-dragon-ai-composer-action]" not in css:
        fail("dragon-ui.css must stamp composer chrome and the action cluster")
    talk_rule = css.split("[data-dragon-grok-talk] {", 1)
    if len(talk_rule) < 2 or "var(--color-primary)" in talk_rule[1].split("}", 1)[0]:
        fail("Talk / Start conversation must not keep a crimson bordered island")
    table = json.loads(read(TABLE))
    voice = table.get("voice") or {}
    if voice.get("options") != ["gpt", "grok"]:
        fail("desktop_branding.json voice.options must be gpt + grok")
    if voice.get("default") != "gpt":
        fail("default voice option must stay GPT so Grok is additive")
    print("OK  overlay selector shows GPT and Grok")


def test_docs_and_packaging(vc) -> None:
    docs = read(DOCS)
    for needle in (
        "GPT",
        "Grok",
        "XAI_API_KEY",
        "https://api.x.ai/v1/tts",
        "https://api.x.ai/v1/stt",
        "grok-voice-latest",
        "gpt-live",
        "grok-live",
        "do not replace",
        "OPENAI_API_KEY",
        "full-duplex",
        "Talk with Grok",
        "xai-client-secret",
        "voice-live.ts",
        "voice_live.py",
    ):
        if needle.lower() not in docs.lower() and needle not in docs:
            fail(f"VOICE.md must document {needle!r}")
    if "ready-to-paste" not in docs.lower() and "follow-up prompt" not in docs.lower():
        fail("VOICE.md must include the ready-to-paste Hermes follow-up prompt")
    if "invent" in docs.lower() and "do not invent" not in docs.lower():
        pass
    guide = read(SETUP_GUIDE)
    if "Grok voice" not in guide or "XAI_API_KEY" not in guide:
        fail("SETUP_GUIDE.md must mention Grok voice + XAI_API_KEY")
    branding = read(BRANDING_DOC)
    if "Grok" not in branding or "GPT" not in branding:
        fail("BRANDING.md must mention the GPT | Grok voice selector")
    log = read(CHANGELOG)
    if "Grok voice" not in log or "GPT voice" not in log:
        fail("CHANGELOG.md must record Grok added beside GPT voice")
    launcher = read(LAUNCHER)
    if "Start-DragonAIVoiceChat" not in launcher:
        fail("launcher must define Start-DragonAIVoiceChat")
    if "voice_chat" not in launcher or "8654" not in launcher:
        fail("start-embedded.ps1 must start the voice helper on :8654")
    finder = read(FINDER)
    if "voice_chat.py" not in finder or "8654" not in finder:
        fail("Find-HermesDesktop.ps1 must start the voice helper")
    apply_ps = read(APPLY)
    if "voice_chat.py" not in apply_ps:
        fail("Apply-VoiceChat.ps1 must call voice_chat.py")
    for path in (INSTALL, SETUP):
        text = read(path)
        if "voice_chat.py" not in text or "VOICE.md" not in text:
            fail(f"{path.name} must install voice_chat.py and VOICE.md")
        if "Apply-VoiceChat.ps1" not in text:
            fail(f"{path.name} must install Apply-VoiceChat.ps1")
        if "branding\\voice" not in text and "branding/voice" not in text:
            fail(f"{path.name} must copy branding/voice for the duplex overlay")
    if vc.self_test() != 0:
        fail("voice_chat --self-test failed")
    print("OK  docs, launcher, and installer wiring")


def main() -> int:
    vc = load_engine()
    test_catalog_keeps_both(vc)
    test_request_builders_match_docs(vc)
    test_apply_does_not_replace_gpt(vc)
    test_no_invented_endpoints(vc)
    test_ephemeral_token_shape(vc)
    test_overlay_selector_coexists(vc)
    test_docs_and_packaging(vc)
    print("SMOKE OK: GPT voice stays gpt-live; Grok overlay hosts official duplex.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
