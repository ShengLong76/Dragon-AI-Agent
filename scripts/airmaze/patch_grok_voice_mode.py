#!/usr/bin/env python3
"""Accept voice.voice_chat_mode: grok-live beside chained|gpt-live.

Hermes methods_config_set.py only allows chained|gpt-live. Settings → Voice
→ Voice conversation mode cannot persist Grok Voice until that set is
widened. This patch is additive: it does not remove gpt-live or implement a
second duplex engine. The desktop gpt-live path still owns OpenAI WebRTC.

Grok realtime (xAI WebSocket + ephemeral client secret) is not OpenAI
realtime / GPT-Live WebRTC. See docs/airmaze/VOICE.md.

Stdlib only. Safe to run when the file is missing (no-op).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

NEEDLE_SETS = (
    '{"chained", "gpt-live"}',
    "{'chained', 'gpt-live'}",
    '{"gpt-live", "chained"}',
    "{'gpt-live', 'chained'}",
)
REPLACEMENT = '{"chained", "gpt-live", "grok-live"}'
ERROR_FROM = "pick chained|gpt-live"
ERROR_TO = "pick chained|gpt-live|grok-live"
ENUM_FROM = "['chained', 'gpt-live']"
ENUM_TO = "['chained', 'gpt-live', 'grok-live']"


def _compact_sets(text: str) -> str:
    return text.replace("'", '"').replace(" ", "")


def patch_text(text: str) -> tuple[str, int]:
    """Widen voice_chat_mode allow-lists. Idempotent."""
    hits = 0
    out = text
    compact = _compact_sets(out)
    already_set = '{"chained","gpt-live","grok-live"}' in compact
    if not already_set:
        for needle in NEEDLE_SETS:
            if needle in out:
                repl = REPLACEMENT if '"' in needle else "{'chained', 'gpt-live', 'grok-live'}"
                out = out.replace(needle, repl)
                hits += 1
    if ERROR_TO not in out and ERROR_FROM in out:
        out = out.replace(ERROR_FROM, ERROR_TO)
        hits += 1
    if ENUM_TO not in out and ENUM_FROM in out:
        out = out.replace(ENUM_FROM, ENUM_TO)
        hits += 1
    return out, hits


def patch_file(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"ok": False, "path": str(path), "error": "missing"}
    original = path.read_text(encoding="utf-8")
    updated, hits = patch_text(original)
    if updated == original:
        return {"ok": True, "path": str(path), "changed": False, "hits": hits}
    path.write_text(updated, encoding="utf-8")
    return {"ok": True, "path": str(path), "changed": True, "hits": hits}


def candidate_paths() -> list[Path]:
    roots = [
        Path("/opt/hermes"),
        Path("/opt/hermes-agent"),
        Path("/app"),
        Path("/usr/local/lib"),
        Path("/usr/lib"),
    ]
    found: list[Path] = []
    seen: set[Path] = set()
    names = ("methods_config_set.py",)
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            for path in root.rglob(name):
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                found.append(path)
    return found


def apply_image_patches() -> list[dict[str, object]]:
    results = []
    for path in candidate_paths():
        results.append(patch_file(path))
    return results


def self_test() -> int:
    sample = (
        '        "voice.voice_chat_mode": (_word, {"chained", "gpt-live"}, '
        '"unknown voice chat mode: {value}; pick chained|gpt-live",\n'
        "                                  lambda w: _write_config_key(\"voice.voice_chat_mode\", w))}\n"
    )
    out, hits = patch_text(sample)
    if "grok-live" not in out or "gpt-live" not in out or "chained" not in out:
        print("FAIL: patch must add grok-live without dropping chained|gpt-live", file=sys.stderr)
        return 1
    if "pick chained|gpt-live|grok-live" not in out:
        print("FAIL: error copy must name grok-live", file=sys.stderr)
        return 1
    if hits < 1:
        print("FAIL: expected at least one replacement", file=sys.stderr)
        return 1
    again, hits2 = patch_text(out)
    if again != out:
        print("FAIL: patch must be idempotent", file=sys.stderr)
        return 1
    enum = "ENUM_OPTIONS = {'voice.voice_chat_mode': ['chained', 'gpt-live']}"
    enum_out, _ = patch_text(enum)
    if "['chained', 'gpt-live', 'grok-live']" not in enum_out:
        print("FAIL: desktop enum list must gain grok-live", file=sys.stderr)
        return 1
    print("OK  patch_grok_voice_mode self-test")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Accept grok-live beside gpt-live in Hermes voice_chat_mode")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Patch methods_config_set.py in the image if present")
    parser.add_argument("--file", default="", help="Patch one file")
    args = parser.parse_args(argv)
    if args.self_test or (not args.apply and not args.file):
        return self_test()
    if args.file:
        result = patch_file(Path(args.file))
        print(result)
        return 0 if result.get("ok") else 1
    results = apply_image_patches()
    print(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
