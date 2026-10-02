#!/usr/bin/env python3
"""Dragon AI Agent first-run chat + image LLM defaults.

Merges Hermes gateway config.yaml so chat uses the selected model and
profile Generate can see an image_gen backend. Stdlib only. No secrets.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CHAT_PROVIDER = "xai"
DEFAULT_CHAT_MODEL = "grok-4.6"
DEFAULT_IMAGE_PROVIDER = "xai"
DEFAULT_IMAGE_MODEL = "grok-imagine-image"
CONFIG_NAME = "config.yaml"
EMBEDDED_HOME_NAME = ".hermes-airmaze-embedded"

DEFAULT_CUSTOM_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_CUSTOM_MODEL = "local-model"

CHAT_CATALOG: list[dict[str, str]] = [
    {
        "id": "grok-4.6",
        "provider": "xai",
        "model": "grok-4.6",
        "label": "Grok (xAI) — grok-4.6",
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
    pattern = re.compile(rf"(?ms)^{re.escape(key)}:\n(?:[ \t].*\n)*")
    block = block if block.endswith("\n") else block + "\n"
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    body = text.rstrip()
    if body:
        return body + "\n\n" + block
    return (
        "# Dragon AI Agent first-run model defaults. Merged into Hermes gateway config.\n"
        "# Auth stays env keys already on this machine (or DPAPI for a self-hosted key). Nothing secret is stored here.\n\n"
        + block
    )


def apply_models(
    home: Path | str,
    chat_model: str | None = None,
    image_model: str | None = None,
    custom_model: str | None = None,
    base_url: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    chat = resolve_chat_choice(chat_model, custom_model=custom_model, base_url=base_url)
    image = _lookup(IMAGE_CATALOG, image_model or DEFAULT_IMAGE_MODEL)
    path = config_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    parsed = _simple_load(existing) if existing.strip() else {}
    has_chat = bool(_nested_get(parsed, "principal", "model"))
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
    return {
        "wrote": wrote,
        "path": str(path),
        "chatProvider": str(_nested_get(final, "principal", "provider") or chat["provider"]),
        "chatModel": str(_nested_get(final, "principal", "model") or chat["model"]),
        "chatBaseUrl": str(_nested_get(final, "principal", "base_url") or chat.get("base_url") or ""),
        "imageProvider": str(_nested_get(final, "image_gen", "provider") or image["provider"]),
        "imageModel": str(_nested_get(final, "image_gen", "xai", "model") or _nested_get(final, "image_gen", "model") or image["model"]),
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
    return 0


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
    sub.add_parser("catalog")
    args = parser.parse_args(argv)
    if args.self_test or args.cmd is None and not argv:
        return self_test()
    if args.cmd == "catalog":
        print(json.dumps({"chat": chat_catalog(), "image": image_catalog()}, indent=2))
        return 0
    if args.cmd == "apply":
        home = Path(args.home) if str(args.home or "").strip() else default_embedded_home()
        result = apply_models(
            home,
            chat_model=args.chat,
            image_model=args.image,
            custom_model=args.custom_model or None,
            base_url=args.base_url or None,
            overwrite=not args.if_missing,
        )
        print(json.dumps(result, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
