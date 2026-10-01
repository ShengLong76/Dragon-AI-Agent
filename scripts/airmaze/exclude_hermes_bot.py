#!/usr/bin/env python3
"""Exclude the Hermes bot from Dragon AI Agent.

James (2026-10-01): do not ship a Hermes bot. Purge leftover
default/hermes profile folders so they do not come back under UNASSIGNED.
Do not seed those ids on deploy/import/sync. Personal Assistant stays.

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

EXCLUDED_IDS = ("default", "hermes")
EXCLUDED_TITLE_PREFIXES = ("hermes",)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def is_excluded_profile(
    profile_id: str,
    title: str | None = None,
    meta: dict[str, Any] | None = None,
) -> bool:
    """True when this roster id or display title is the stock Hermes bot."""
    if _norm(profile_id) in EXCLUDED_IDS:
        return True
    titles: list[str] = []
    if title:
        titles.append(str(title))
    if isinstance(meta, dict):
        for key in ("title", "display_name", "displayName", "name"):
            if meta.get(key):
                titles.append(str(meta[key]))
    for raw in titles:
        text = _norm(raw)
        if not text:
            continue
        if text in EXCLUDED_IDS:
            return True
        if any(text == prefix or text.startswith(prefix + " ") for prefix in EXCLUDED_TITLE_PREFIXES):
            return True
    return False


def _read_meta(folder: Path) -> dict[str, Any]:
    path = folder / "bot.meta.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def purge_hermes_profiles(roots: Iterable[Path | str]) -> dict[str, Any]:
    """Delete leftover default/hermes folders. Keep catalog bots."""
    removed: list[str] = []
    for raw in roots:
        root = Path(raw)
        if not root.is_dir():
            continue
        for child in list(root.iterdir()):
            if not child.is_dir():
                continue
            meta = _read_meta(child)
            if not is_excluded_profile(child.name, meta=meta):
                continue
            shutil.rmtree(child)
            removed.append(str(child))
    return {"removed": removed, "kept": [id_ for id_ in ("personal-assistant",) if True]}


def default_profile_roots() -> list[Path]:
    roots: list[Path] = []
    local = Path.home() / "AppData" / "Local"
    if (Path.home() / "AppData").is_dir():
        roots.append(local / "hermes" / "profiles")
        roots.append(Path.home() / ".hermes-airmaze-embedded" / "profiles")
    else:
        roots.append(Path.home() / "hermes" / "profiles")
        roots.append(Path.home() / ".hermes-airmaze-embedded" / "profiles")
    return roots


def self_test() -> int:
    if not is_excluded_profile("default"):
        print("FAIL: default must be excluded", file=sys.stderr)
        return 1
    if not is_excluded_profile("Hermes"):
        print("FAIL: hermes must be excluded", file=sys.stderr)
        return 1
    if is_excluded_profile("personal-assistant"):
        print("FAIL: Personal Assistant must stay", file=sys.stderr)
        return 1
    if is_excluded_profile("email-warmer", title="Email Warmer"):
        print("FAIL: catalog bot must stay", file=sys.stderr)
        return 1
    if not is_excluded_profile("custom", title="Hermes Agent"):
        print("FAIL: Hermes Agent title must be excluded", file=sys.stderr)
        return 1
    print("OK  exclude_hermes_bot self-test")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exclude the Hermes bot from Dragon AI Agent")
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="cmd")
    p_purge = sub.add_parser("purge", help="Delete leftover default/hermes profile folders")
    p_purge.add_argument("--desktop", default="")
    p_purge.add_argument("--embedded", default="")
    args = parser.parse_args(argv)

    if args.self_test or args.cmd is None:
        return self_test()

    if args.cmd == "purge":
        roots: list[Path] = []
        if args.desktop:
            roots.append(Path(args.desktop))
        if args.embedded:
            roots.append(Path(args.embedded))
        if not roots:
            roots = default_profile_roots()
        summary = purge_hermes_profiles(roots)
        print(json.dumps(summary, indent=2))
        return 0

    return self_test()


if __name__ == "__main__":
    raise SystemExit(main())
