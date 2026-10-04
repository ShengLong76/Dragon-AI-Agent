#!/usr/bin/env python3
"""Dragon AI Agent first-run chat + image LLM defaults.

Merges Hermes gateway config.yaml so chat uses the selected model and
profile Generate can see an image_gen backend. The same chat pick is
inherited by every bot profile unless that bot has an override.
Stdlib only. No secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_CHAT_PROVIDER = "xai"
DEFAULT_CHAT_MODEL = "grok-4.7"
DEFAULT_IMAGE_PROVIDER = "xai"
DEFAULT_IMAGE_MODEL = "grok-imagine-image"
CONFIG_NAME = "config.yaml"
EMBEDDED_HOME_NAME = ".hermes-airmaze-embedded"
INHERITED_MARK = "# dragon-ai-inherited-model"
PROFILE_IDENTITY = ("config.yaml", "profile.yaml", "bot.yaml", "SOUL.md", "bot.meta.json")
INHERIT_HOST = "127.0.0.1"
INHERIT_PORT = 8655

DEFAULT_CUSTOM_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_CUSTOM_MODEL = "local-model"

CHAT_CATALOG: list[dict[str, str]] = [
    {
        "id": "grok-4.7",
        "provider": "xai",
        "model": "grok-4.7",
        "label": "Grok (xAI) - grok-4.7",
        "kind": "cloud",
        "auth_env": "XAI_API_KEY",
    },
    {
        "id": "grok-4.6",
        "provider": "xai",
        "model": "grok-4.6",
        "label": "Grok (xAI) - grok-4.6",
        "kind": "cloud",
        "auth_env": "XAI_API_KEY",
    },
    {
        "id": "grok-4.5",
        "provider": "xai",
        "model": "grok-4.5",
        "label": "Grok (xAI) — grok-4.5",
        "kind": "cloud",
        "auth_env": "XAI_API_KEY",
    },
    {
        "id": "grok-4.3",
        "provider": "xai",
        "model": "grok-4.3",
        "label": "Grok (xAI) — grok-4.3",
        "kind": "cloud",
        "auth_env": "XAI_API_KEY",
    },
    {
        "id": "gpt-4o",
        "provider": "openai-api",
        "model": "gpt-4o",
        "label": "OpenAI — gpt-4o",
        "kind": "cloud",
        "auth_env": "OPENAI_API_KEY",
    },
    {
        "id": "claude-sonnet-4-6",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "label": "Anthropic — claude-sonnet-4-6",
        "kind": "cloud",
        "auth_env": "ANTHROPIC_API_KEY",
    },
    {
        "id": "gemini-2.5-pro",
        "provider": "gemini",
        "model": "gemini-2.5-pro",
        "label": "Google Gemini — gemini-2.5-pro",
        "kind": "cloud",
        "auth_env": "GOOGLE_API_KEY",
    },
    {
        "id": "openrouter-gpt-4o",
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "label": "OpenRouter — openai/gpt-4o",
        "kind": "cloud",
        "auth_env": "OPENROUTER_API_KEY",
    },
    {
        "id": "self-hosted",
        "provider": "custom",
        "model": DEFAULT_CUSTOM_MODEL,
        "label": "Self-hosted / custom endpoint",
        "kind": "custom",
        "auth_env": "",
        "base_url": DEFAULT_CUSTOM_BASE_URL,
    },
]

IMAGE_CATALOG: list[dict[str, str]] = [
    {
        "id": "grok-imagine-image",
        "provider": "xai",
        "model": "grok-imagine-image",
        "label": "Grok Imagine — grok-imagine-image",
    },
    {
        "id": "grok-imagine-image-quality",
        "provider": "xai",
        "model": "grok-imagine-image-quality",
        "label": "Grok Imagine (Quality) — grok-imagine-image-quality",
    },
    {
        "id": "grok-imagine-image-2.0",
        "provider": "xai",
        "model": "grok-imagine-image-2.0",
        "label": "Grok Imagine 2.0 — grok-imagine-image-2.0",
    },
]


def chat_catalog() -> list[dict[str, str]]:
    return [dict(row) for row in CHAT_CATALOG]


def image_catalog() -> list[dict[str, str]]:
    return [dict(row) for row in IMAGE_CATALOG]


def _lookup(catalog: list[dict[str, str]], model_id: str) -> dict[str, str]:
    want = str(model_id or "").strip()
    for row in catalog:
        if row["id"] == want or row["model"] == want:
            return dict(row)
    raise ValueError(f"unknown model {model_id!r}")


def is_custom_choice(row: dict[str, str]) -> bool:
    return str(row.get("kind") or "") == "custom" or str(row.get("provider") or "") == "custom"


def resolve_chat_choice(
    model_id: str | None = None,
    custom_model: str | None = None,
    base_url: str | None = None,
) -> dict[str, str]:
    row = _lookup(CHAT_CATALOG, model_id or DEFAULT_CHAT_MODEL)
    if is_custom_choice(row):
        mid = str(custom_model or row.get("model") or DEFAULT_CUSTOM_MODEL).strip() or DEFAULT_CUSTOM_MODEL
        url = str(base_url or row.get("base_url") or DEFAULT_CUSTOM_BASE_URL).strip() or DEFAULT_CUSTOM_BASE_URL
        row["model"] = mid
        row["base_url"] = url
    return row


def popular_cloud_providers() -> list[str]:
    return sorted(
        {
            str(row["provider"])
            for row in CHAT_CATALOG
            if str(row.get("kind") or "") == "cloud"
        }
    )


def default_embedded_home() -> Path:
    return Path.home() / EMBEDDED_HOME_NAME


def config_path(home: Path | str) -> Path:
    root = Path(home)
    if root.name == CONFIG_NAME:
        return root
    return root / CONFIG_NAME


def _simple_load(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        stripped = raw.split("#", 1)[0]
        if not stripped.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if ":" not in stripped:
            continue
        key, _, rest = stripped.lstrip(" ").partition(":")
        key = key.strip()
        value = rest.strip().strip("'\"")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = value
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    node: Any = data
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _yaml_scalar(value: str) -> str:
    s = str(value or "")
    if not s or any(ch in s for ch in (":", "#", " ", '"', "'", "{", "}", "[", "]", ",", "&", "*", "?", "|", "%", "@")):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _principal_block(provider: str, model: str, base_url: str = "") -> str:
    lines = [
        "principal:",
        f"  provider: {provider}",
        f"  model: {_yaml_scalar(model)}",
    ]
    if str(base_url or "").strip():
        lines.append(f"  base_url: {_yaml_scalar(base_url)}")
    return "\n".join(lines) + "\n"


def _hermes_model_block(provider: str, model: str, base_url: str = "") -> str:
    lines = [
        "model:",
        f"  provider: {provider}",
        f"  default: {_yaml_scalar(model)}",
    ]
    if str(base_url or "").strip():
        lines.append(f"  base_url: {_yaml_scalar(base_url)}")
    return "\n".join(lines) + "\n"


def _image_gen_block(provider: str, model: str) -> str:
    return (
        f"image_gen:\n"
        f"  provider: {provider}\n"
        f"  model: {model}\n"
        f"  xai:\n"
        f"    model: {model}\n"
    )


def _upsert_block(text: str, key: str, block: str) -> str:
    mapping = re.compile(rf"(?ms)^{re.escape(key)}:\n(?:[ \t].*\n)*")
    scalar = re.compile(rf"(?m)^{re.escape(key)}:\s*.*$")
    block = block if block.endswith("\n") else block + "\n"
    if mapping.search(text):
        return mapping.sub(block, text, count=1)
    if scalar.search(text):
        return scalar.sub(block.rstrip("\n"), text, count=1)
    body = text.rstrip()
    if body:
        return body + "\n\n" + block
    return (
        "# Dragon AI Agent first-run model defaults. Merged into Hermes gateway config.\n"
        "# Auth stays env keys already on this machine (or DPAPI for a self-hosted key). Nothing secret is stored here.\n\n"
        + block
    )


def _ensure_inherited_mark(text: str) -> str:
    if INHERITED_MARK in text:
        return text
    replaced, count = re.subn(
        r"(?m)^(model:|principal:)",
        INHERITED_MARK + r"\n\1",
        text,
        count=1,
    )
    if count:
        return replaced
    body = text.rstrip()
    return (body + "\n\n" + INHERITED_MARK + "\n") if body else INHERITED_MARK + "\n"


def _chat_from_parsed(parsed: dict[str, Any]) -> tuple[str, str, str]:
    raw_model = parsed.get("model")
    if isinstance(raw_model, str) and raw_model.strip():
        model = raw_model.strip()
    else:
        model = str(
            _nested_get(parsed, "principal", "model")
            or _nested_get(parsed, "model", "default")
            or _nested_get(parsed, "model", "model")
            or ""
        ).strip()
    provider = str(
        _nested_get(parsed, "principal", "provider")
        or _nested_get(parsed, "model", "provider")
        or ""
    ).strip()
    base_url = str(
        _nested_get(parsed, "principal", "base_url")
        or _nested_get(parsed, "model", "base_url")
        or ""
    ).strip()
    return provider, model, base_url


def read_applied_models(home: Path | str) -> dict[str, Any]:
    path = config_path(home)
    if not path.is_file():
        return {
            "chatProvider": DEFAULT_CHAT_PROVIDER,
            "chatModel": DEFAULT_CHAT_MODEL,
            "chatBaseUrl": "",
            "imageProvider": DEFAULT_IMAGE_PROVIDER,
            "imageModel": DEFAULT_IMAGE_MODEL,
            "path": str(path),
            "present": False,
        }
    parsed = _simple_load(path.read_text(encoding="utf-8"))
    provider, model, base_url = _chat_from_parsed(parsed)
    return {
        "chatProvider": provider or DEFAULT_CHAT_PROVIDER,
        "chatModel": model or DEFAULT_CHAT_MODEL,
        "chatBaseUrl": base_url,
        "imageProvider": str(_nested_get(parsed, "image_gen", "provider") or DEFAULT_IMAGE_PROVIDER),
        "imageModel": str(
            _nested_get(parsed, "image_gen", "xai", "model")
            or _nested_get(parsed, "image_gen", "model")
            or DEFAULT_IMAGE_MODEL
        ),
        "path": str(path),
        "present": bool(model),
        "mtime": path.stat().st_mtime,
    }


def candidate_config_homes(primary: Path | str) -> list[Path]:
    homes: list[Path] = []
    seen: set[Path] = set()
    extras = [
        Path(primary),
        Path.home() / EMBEDDED_HOME_NAME,
        Path.home() / ".hermes",
    ]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        extras.append(Path(local) / "hermes")
    for raw in extras:
        try:
            key = raw.resolve()
        except OSError:
            key = raw
        if key in seen:
            continue
        seen.add(key)
        homes.append(raw)
    return homes


def read_best_applied_models(primary: Path | str) -> dict[str, Any]:
    """Prefer the newest Hermes config that already has a chat model (in-app pick)."""
    best: dict[str, Any] | None = None
    best_mtime = -1.0
    for home in candidate_config_homes(primary):
        applied = read_applied_models(home)
        if not applied.get("present"):
            continue
        mtime = float(applied.get("mtime") or 0)
        if best is None or mtime >= best_mtime:
            best = applied
            best_mtime = mtime
    return best or read_applied_models(primary)


def default_profile_roots(home: Path | str, *, include_desktop: bool = False) -> list[Path]:
    home_p = Path(home)
    roots = [home_p / "profiles"]
    if include_desktop:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            extra = Path(local) / "hermes" / "profiles"
            try:
                same = extra.resolve() == roots[0].resolve()
            except OSError:
                same = False
            if not same:
                roots.append(extra)
    return roots


def _is_excluded_profile_dir(path: Path) -> bool:
    meta: dict[str, Any] = {}
    meta_path = path / "bot.meta.json"
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta = loaded
        except (OSError, json.JSONDecodeError):
            meta = {}
    try:
        from exclude_hermes_bot import is_excluded_profile  # noqa: WPS433
    except ImportError:
        return path.name.lower() in ("default", "hermes")
    return bool(is_excluded_profile(path.name, title=str(meta.get("title") or ""), meta=meta))


def iter_bot_profiles(roots: list[Path | str] | None) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for raw in roots or []:
        root = Path(raw)
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            try:
                key = child.resolve()
            except OSError:
                key = child
            if key in seen:
                continue
            if not any((child / name).is_file() for name in PROFILE_IDENTITY):
                continue
            if _is_excluded_profile_dir(child):
                continue
            seen.add(key)
            found.append(child)
    return found


def read_profile_model(profile_dir: Path | str) -> dict[str, Any]:
    root = Path(profile_dir)
    inherited = False
    provider = ""
    model = ""
    source = ""
    for name in ("config.yaml", "profile.yaml", "bot.yaml"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if INHERITED_MARK in text:
            inherited = True
        parsed = _simple_load(text) if text.strip() else {}
        got_provider, got_model, _got_base = _chat_from_parsed(parsed)
        if got_model and not model:
            provider, model, source = got_provider, got_model, str(path)
    return {
        "provider": provider,
        "model": model,
        "inherited": inherited,
        "path": source,
    }


def _ensure_bot_config_yaml(profile_dir: Path) -> Path:
    cfg = profile_dir / CONFIG_NAME
    if cfg.is_file():
        return cfg
    for name in ("bot.yaml", "profile.yaml"):
        src = profile_dir / name
        if src.is_file():
            shutil.copy2(src, cfg)
            return cfg
    cfg.write_text("", encoding="utf-8")
    return cfg


def _stamp_profile_files(profile_dir: Path, provider: str, model: str, base_url: str = "") -> None:
    _ensure_bot_config_yaml(profile_dir)
    for name in ("config.yaml", "profile.yaml", "bot.yaml"):
        path = profile_dir / name
        if name != "config.yaml" and not path.is_file():
            continue
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        text = _upsert_block(text, "principal", _principal_block(provider, model, base_url))
        text = _upsert_block(text, "model", _hermes_model_block(provider, model, base_url))
        text = _ensure_inherited_mark(text)
        if not text.endswith("\n"):
            text += "\n"
        path.write_text(text, encoding="utf-8")


def inherit_default_model(
    profile_dir: Path | str,
    provider: str | None = None,
    model: str | None = None,
    base_url: str = "",
    overwrite: bool = True,
) -> dict[str, Any]:
    dest = Path(profile_dir)
    dest.mkdir(parents=True, exist_ok=True)
    chat_provider = (provider or DEFAULT_CHAT_PROVIDER).strip() or DEFAULT_CHAT_PROVIDER
    chat_model = (model or DEFAULT_CHAT_MODEL).strip() or DEFAULT_CHAT_MODEL
    current = read_profile_model(dest)
    current_model = str(current.get("model") or "").strip()
    inherited = bool(current.get("inherited"))
    is_override = bool(current_model) and not inherited and current_model != chat_model
    if is_override:
        return {
            "wrote": False,
            "reason": "override",
            "path": str(dest),
            "chatProvider": current.get("provider") or chat_provider,
            "chatModel": current_model,
        }
    if current_model and not overwrite:
        return {
            "wrote": False,
            "reason": "present",
            "path": str(dest),
            "chatProvider": current.get("provider") or chat_provider,
            "chatModel": current_model,
        }
    _stamp_profile_files(dest, chat_provider, chat_model, base_url)
    return {
        "wrote": True,
        "reason": "inherited",
        "path": str(dest),
        "chatProvider": chat_provider,
        "chatModel": chat_model,
    }


def apply_inherited_models(
    roots: list[Path | str] | None,
    provider: str,
    model: str,
    overwrite: bool = True,
    base_url: str = "",
) -> dict[str, Any]:
    stamped = 0
    skipped = 0
    present = 0
    if isinstance(roots, (str, Path)):
        roots = [roots]
    for profile in iter_bot_profiles(roots):
        result = inherit_default_model(
            profile,
            provider=provider,
            model=model,
            base_url=base_url,
            overwrite=overwrite,
        )
        if result.get("wrote"):
            stamped += 1
        elif result.get("reason") == "override":
            skipped += 1
        else:
            present += 1
    return {
        "botsStamped": stamped,
        "botsSkippedOverride": skipped,
        "botsAlreadySet": present,
    }


def apply_discovered_chat(home: Path | str, provider: str, model: str, base_url: str = "") -> dict[str, Any]:
    """Write an in-app / Hermes chat pick onto the embedded gateway without a catalog id."""
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    text = _upsert_block(existing, "principal", _principal_block(provider, model, base_url))
    text = _upsert_block(text, "model", _hermes_model_block(provider, model, base_url))
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return {"wrote": True, "path": str(path), "chatProvider": provider, "chatModel": model, "chatBaseUrl": base_url}


def inherit_from_home(
    home: Path | str,
    profile_roots: list[Path | str] | None = None,
    overwrite: bool = True,
    sync_gateway: bool = True,
) -> dict[str, Any]:
    """Stamp every bot from the in-app / gateway chat pick. Overrides without the marker stay."""
    discovered = read_best_applied_models(home)
    provider = str(discovered.get("chatProvider") or DEFAULT_CHAT_PROVIDER)
    model = str(discovered.get("chatModel") or DEFAULT_CHAT_MODEL)
    base_url = str(discovered.get("chatBaseUrl") or "")
    gateway = {"wrote": False, "path": str(config_path(home))}
    if sync_gateway and discovered.get("present"):
        current = read_applied_models(home)
        if (
            current.get("chatModel") != model
            or current.get("chatProvider") != provider
            or current.get("chatBaseUrl") != base_url
        ):
            gateway = apply_discovered_chat(home, provider, model, base_url)
    roots = (
        [Path(p) for p in profile_roots]
        if profile_roots is not None
        else default_profile_roots(home, include_desktop=True)
    )
    bots = apply_inherited_models(roots, provider, model, overwrite=overwrite, base_url=base_url)
    return {
        "ok": True,
        "source": discovered.get("path"),
        "chatProvider": provider,
        "chatModel": model,
        "chatBaseUrl": base_url,
        "gateway": gateway,
        **bots,
    }


def apply_models(
    home: Path | str,
    chat_model: str | None = None,
    image_model: str | None = None,
    custom_model: str | None = None,
    base_url: str | None = None,
    overwrite: bool = True,
    profile_roots: list[Path | str] | None = None,
    stamp_bots: bool = True,
) -> dict[str, Any]:
    chat = resolve_chat_choice(chat_model, custom_model=custom_model, base_url=base_url)
    image = _lookup(IMAGE_CATALOG, image_model or DEFAULT_IMAGE_MODEL)
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    parsed = _simple_load(existing) if existing.strip() else {}
    _has_provider, has_chat_model, _has_base = _chat_from_parsed(parsed)
    has_chat = bool(has_chat_model)
    has_image = bool(_nested_get(parsed, "image_gen", "provider"))
    write_chat = overwrite or not has_chat
    write_image = overwrite or not has_image
    text = existing
    chat_base = str(chat.get("base_url") or "")
    if write_chat:
        text = _upsert_block(text, "principal", _principal_block(chat["provider"], chat["model"], chat_base))
        text = _upsert_block(text, "model", _hermes_model_block(chat["provider"], chat["model"], chat_base))
    if write_image:
        text = _upsert_block(text, "image_gen", _image_gen_block(image["provider"], image["model"]))
    wrote = write_chat or write_image
    if wrote:
        if not text.endswith("\n"):
            text += "\n"
        path.write_text(text, encoding="utf-8")
    final = _simple_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    final_provider, final_model, final_base = _chat_from_parsed(final)
    bots = {"botsStamped": 0, "botsSkippedOverride": 0, "botsAlreadySet": 0}
    if stamp_bots:
        roots = (
            [Path(p) for p in profile_roots]
            if profile_roots is not None
            else default_profile_roots(path.parent, include_desktop=False)
        )
        bots = apply_inherited_models(
            roots,
            final_provider or chat["provider"],
            final_model or chat["model"],
            overwrite=overwrite,
            base_url=final_base or chat_base,
        )
    return {
        "wrote": wrote,
        "path": str(path),
        "chatProvider": final_provider or chat["provider"],
        "chatModel": final_model or chat["model"],
        "chatBaseUrl": final_base or chat.get("base_url") or "",
        "imageProvider": str(_nested_get(final, "image_gen", "provider") or image["provider"]),
        "imageModel": str(
            _nested_get(final, "image_gen", "xai", "model")
            or _nested_get(final, "image_gen", "model")
            or image["model"]
        ),
        **bots,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="dragon-gm-self-") as tmp:
        home = Path(tmp)
        result = apply_models(home)
        text = (home / CONFIG_NAME).read_text(encoding="utf-8")
        if re.search(r"(?im)^\s*(api_key|xai_api_key)\s*:", text):
            print("self-test: wrote a key", file=sys.stderr)
            return 1
        if result.get("chatModel") != DEFAULT_CHAT_MODEL:
            print(f"self-test: chat {result}", file=sys.stderr)
            return 1
        if "image_gen:" not in text or "grok-imagine-image" not in text:
            print("self-test: missing image_gen", file=sys.stderr)
            return 1
        custom = apply_models(
            home,
            chat_model="self-hosted",
            custom_model="llama3.1",
            base_url="http://127.0.0.1:11434/v1",
            overwrite=True,
        )
        custom_text = (home / CONFIG_NAME).read_text(encoding="utf-8")
        if custom.get("chatProvider") != "custom" or "11434" not in custom_text:
            print(f"self-test: custom {custom}", file=sys.stderr)
            return 1
        if re.search(r"(?im)^\s*(api_key|xai_api_key|openai_api_key)\s*:", custom_text):
            print("self-test: custom wrote a key", file=sys.stderr)
            return 1
        bot = home / "profiles" / "personal-assistant"
        bot.mkdir(parents=True)
        (bot / "bot.yaml").write_text("slug: personal-assistant\n", encoding="utf-8")
        inherit_default_model(bot, provider=DEFAULT_CHAT_PROVIDER, model=DEFAULT_CHAT_MODEL)
        bot_text = (bot / "config.yaml").read_text(encoding="utf-8")
        if INHERITED_MARK not in bot_text or DEFAULT_CHAT_MODEL not in bot_text:
            print("self-test: bot inherit missing", file=sys.stderr)
            return 1
    return 0


def _json_bytes(data: Any, status: int = 200) -> tuple[int, bytes]:
    return status, (json.dumps(data) + "\n").encode("utf-8")


def make_inherit_handler(home: Path, profile_roots: list[Path]) -> type[BaseHTTPRequestHandler]:
    class InheritHandler(BaseHTTPRequestHandler):
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
            if path in ("/api/health", "/health"):
                self._send(200, b'{"ok":true,"service":"dragon-inherit-models"}\n')
                return
            if path in ("/api/inherit-models", "/inherit-models"):
                status, body = _json_bytes(inherit_from_home(home, profile_roots=profile_roots, overwrite=True))
                self._send(status, body)
                return
            self._send(404, b'{"error":"not found"}\n')

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/api/inherit-models", "/inherit-models"):
                status, body = _json_bytes(inherit_from_home(home, profile_roots=profile_roots, overwrite=True))
                self._send(status, body)
                return
            self._send(404, b'{"error":"not found"}\n')

    return InheritHandler


def serve_inherit(
    home: Path | str,
    host: str = INHERIT_HOST,
    port: int = INHERIT_PORT,
    profile_roots: list[Path | str] | None = None,
) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("inherit helper binds loopback only")
    roots = [Path(p) for p in profile_roots] if profile_roots else default_profile_roots(home, include_desktop=True)
    httpd = ThreadingHTTPServer((host, port), make_inherit_handler(Path(home), roots))
    print(f"Dragon AI inherit helper on http://{host}:{port}/api/inherit-models", flush=True)
    httpd.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Dragon AI Agent default chat/image models into Hermes config.yaml")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("--home", default="", help="Hermes home directory (config.yaml parent)")
    apply_p.add_argument("--chat", default=DEFAULT_CHAT_MODEL)
    apply_p.add_argument("--image", default=DEFAULT_IMAGE_MODEL)
    apply_p.add_argument("--custom-model", default="", help="Model id when --chat is self-hosted")
    apply_p.add_argument("--base-url", default="", help="OpenAI-compatible base URL when --chat is self-hosted")
    apply_p.add_argument("--if-missing", action="store_true")
    apply_p.add_argument(
        "--profiles",
        action="append",
        default=[],
        help="Extra bot profile roots to stamp (repeatable). Desktop picker path, etc.",
    )
    inherit_p = sub.add_parser("inherit")
    inherit_p.add_argument("--home", default="")
    inherit_p.add_argument("--profiles", action="append", default=[])
    inherit_p.add_argument("--if-missing", action="store_true")
    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--home", default="")
    serve_p.add_argument("--host", default=INHERIT_HOST)
    serve_p.add_argument("--port", type=int, default=INHERIT_PORT)
    serve_p.add_argument("--profiles", action="append", default=[])
    sub.add_parser("catalog")
    args = parser.parse_args(argv)
    if args.self_test or args.cmd is None and not argv:
        return self_test()
    if args.cmd == "catalog":
        print(json.dumps({"chat": chat_catalog(), "image": image_catalog()}, indent=2))
        return 0
    if args.cmd == "apply":
        home = Path(args.home) if str(args.home or "").strip() else default_embedded_home()
        extra = [Path(p) for p in (args.profiles or []) if str(p or "").strip()]
        roots = default_profile_roots(home, include_desktop=not extra)
        for item in extra:
            if item not in roots:
                roots.append(item)
        result = apply_models(
            home,
            chat_model=args.chat,
            image_model=args.image,
            custom_model=args.custom_model or None,
            base_url=args.base_url or None,
            overwrite=not args.if_missing,
            profile_roots=roots,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "inherit":
        home = Path(args.home) if str(args.home or "").strip() else default_embedded_home()
        extra = [Path(p) for p in (args.profiles or []) if str(p or "").strip()]
        roots = extra or default_profile_roots(home, include_desktop=True)
        result = inherit_from_home(home, profile_roots=roots, overwrite=not args.if_missing)
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "serve":
        home = Path(args.home) if str(args.home or "").strip() else default_embedded_home()
        extra = [Path(p) for p in (args.profiles or []) if str(p or "").strip()]
        serve_inherit(home, host=args.host, port=args.port, profile_roots=extra or None)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
