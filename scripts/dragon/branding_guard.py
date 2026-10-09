#!/usr/bin/env python3
"""Fail if user-visible Hermes naming slips back into Dragon AI.

Allows MIT attribution, LICENSE text, and internal references to the Hermes
upstream remote used by the sync workflow.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEED_PATH = ROOT / "branding" / "product-feed.json"

ALLOWED_PATH_PREFIXES = (
    "LICENSE",
    "branding/product-feed.json",
    "scripts/dragon/",
    ".github/workflows/dragon-",
    "hermes_cli/product_feed.py",
    "tests/hermes_cli/test_product_feed.py",
    "tests/scripts/test_sync_upstream.py",
    "tests/scripts/test_branding_guard.py",
)

# User-visible surfaces the rebrand script already owns, plus README.
VISIBLE_SCAN = [
    ROOT / "README.md",
]

BANNED = re.compile(r"\bHermes Agent\b|\bHermes Desktop\b|\bHermes Cloud\b")
ATTRIBUTION = re.compile(
    r"fork of the open-source \[Hermes Agent\]|Hermes Agent © Nous Research|MIT",
    re.IGNORECASE,
)


def _allowed(path: Path) -> bool:
    rel = path.resolve().relative_to(ROOT).as_posix()
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def scan_visible() -> list[str]:
    hits: list[str] = []
    for path in VISIBLE_SCAN:
        if not path.is_file() or _allowed(path):
            continue
        text = path.read_text(encoding="utf-8-sig")
        for index, line in enumerate(text.splitlines(), 1):
            if BANNED.search(line) and not ATTRIBUTION.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{index}:{line.strip()}")
    return hits


def check_product_feed() -> list[str]:
    feed = json.loads(FEED_PATH.read_text(encoding="utf-8-sig"))
    errors = []
    if feed.get("productRepository") != "ShengLong76/Dragon-AI-Agent":
        errors.append("branding/product-feed.json productRepository must be ShengLong76/Dragon-AI-Agent")
    if feed.get("upstreamRepository") != "NousResearch/hermes-agent":
        errors.append("branding/product-feed.json upstreamRepository must remain NousResearch/hermes-agent")
    if feed.get("publicAssetsBase") not in (None, ""):
        errors.append("branding/product-feed.json publicAssetsBase must stay empty until Dragon owns a CDN")
    version = feed.get("productVersion")
    if not isinstance(version, str) or not version.strip():
        errors.append("branding/product-feed.json productVersion must be the Dragon product version")
    else:
        desktop = json.loads((ROOT / "apps" / "desktop" / "package.json").read_text(encoding="utf-8-sig"))
        if desktop.get("version") != version:
            errors.append("branding/product-feed.json productVersion must match apps/desktop/package.json version")
    return errors


def run_rebrand_check() -> int:
    return subprocess.call(
        [sys.executable, str(ROOT / "scripts" / "dragon" / "rebrand_strings.py"), "--check"],
        cwd=ROOT,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    errors = check_product_feed() + scan_visible()
    rebrand = run_rebrand_check()
    if errors:
        print("branding guard failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
    if rebrand != 0:
        print("rebrand_strings.py --check failed", file=sys.stderr)
    return 1 if errors or rebrand != 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
