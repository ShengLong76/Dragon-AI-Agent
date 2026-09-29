#!/usr/bin/env python3
"""Overlay Dragon AI Agent product chrome onto the on-disk Hermes Electron UI.

This packaging repo does not contain apps/desktop sources and does not rebuild
Hermes.exe. Upstream electron-builder unpacks dist/** next to the exe
(resources/app.asar.unpacked/dist). Those files are not inside the
integrity-checked app.asar, so a launch-time string overlay is the smallest
path that actually changes the empty state, composer placeholder, and
settings product copy.

Never rewrite process names, Docker tags, tokens, ports, protocols, or
license/attribution files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TABLE_PATH = HERE / "desktop_branding.json"

TEXT_EXTENSIONS = {
    ".js",
    ".mjs",
    ".cjs",
    ".html",
    ".htm",
    ".css",
    ".json",
    ".map",
    ".ts",
    ".tsx",
    ".jsx",
}
SKIP_DIR_NAMES = {"node_modules", ".git", "prebuilds", "__pycache__"}
SKIP_NAME_PREFIXES = ("LICENSE", "NOTICE", "THIRD_PARTY", "COPYING")
MAX_FILE_BYTES = 40 * 1024 * 1024
STAMP_NAME = ".dragon-ai-ui-branding.json"


def load_table(path: Path = TABLE_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("replacements"), list) or not data["replacements"]:
        raise ValueError(f"{path} has no replacements")
    return data


def sorted_replacements(table: dict[str, Any]) -> list[dict[str, str]]:
    rows = [r for r in table["replacements"] if r.get("from") and r.get("to")]
    return sorted(rows, key=lambda r: len(r["from"]), reverse=True)


def is_skippable_file(path: Path) -> bool:
    name = path.name
    if name.startswith(SKIP_NAME_PREFIXES):
        return True
    if name == STAMP_NAME:
        return True
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return True
    return False


def iter_overlay_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if root.is_file():
        return [root] if not is_skippable_file(root) else []
    if not root.is_dir():
        return []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if is_skippable_file(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def discover_roots(exe_path: Path) -> list[Path]:
    exe_dir = exe_path.parent
    roots: list[Path] = []
    for rel in (
        Path("resources") / "app.asar.unpacked",
        Path("resources") / "app",
    ):
        candidate = exe_dir / rel
        if candidate.exists():
            roots.append(candidate)
    desktop_root = exe_dir.parent.parent
    intro = desktop_root / "src" / "components" / "chat" / "intro.tsx"
    if intro.is_file():
        roots.append(desktop_root / "src")
    dist = desktop_root / "dist"
    if dist.is_dir() and dist.resolve() not in {p.resolve() for p in roots}:
        roots.append(dist)
    return roots


def apply_text(text: str, replacements: list[dict[str, str]]) -> tuple[str, int]:
    hits = 0
    out = text
    for row in replacements:
        src, dst = row["from"], row["to"]
        if src in out:
            n = out.count(src)
            out = out.replace(src, dst)
            hits += n
    return out, hits


def apply_source_only(path: Path, table: dict[str, Any], text: str) -> tuple[str, int]:
    hits = 0
    out = text
    posix = path.as_posix().replace("\\", "/")
    for row in table.get("source_only") or []:
        suffix = str(row.get("path_suffix") or "").replace("\\", "/")
        src, dst = row.get("from") or "", row.get("to") or ""
        if not suffix or not src or src not in out:
            continue
        if posix.endswith(suffix):
            n = out.count(src)
            out = out.replace(src, dst)
            hits += n
    return out, hits


def read_text_file(path: Path) -> str | None:
    raw = path.read_bytes()
    if b"\x00" in raw:
        return None
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def overlay_file(path: Path, table: dict[str, Any], replacements: list[dict[str, str]]) -> int:
    text = read_text_file(path)
    if text is None:
        return 0
    out, hits = apply_text(text, replacements)
    out, extra = apply_source_only(path, table, out)
    hits += extra
    if hits and out != text:
        path.write_bytes(out.encode("utf-8"))
    return hits


def overlay_roots(roots: list[Path], table: dict[str, Any]) -> dict[str, Any]:
    replacements = sorted_replacements(table)
    files_changed = 0
    replacements_applied = 0
    touched: list[str] = []
    for root in roots:
        for path in iter_overlay_files(root):
            n = overlay_file(path, table, replacements)
            if n:
                files_changed += 1
                replacements_applied += n
                touched.append(str(path))
    return {
        "filesChanged": files_changed,
        "replacementsApplied": replacements_applied,
        "files": touched,
    }


def write_stamp(exe_path: Path, summary: dict[str, Any], table: dict[str, Any]) -> Path | None:
    resources = exe_path.parent / "resources"
    if not resources.is_dir():
        return None
    stamp = {
        "version": table.get("version"),
        "product": table.get("product"),
        "filesChanged": summary["filesChanged"],
        "replacementsApplied": summary["replacementsApplied"],
    }
    dest = resources / STAMP_NAME
    dest.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return dest


def apply_to_exe(exe_path: Path, table: dict[str, Any] | None = None) -> dict[str, Any]:
    table = table or load_table()
    exe = exe_path.resolve()
    roots = discover_roots(exe)
    summary = overlay_roots(roots, table)
    summary["exe"] = str(exe)
    summary["roots"] = [str(r) for r in roots]
    stamp = write_stamp(exe, summary, table)
    if stamp:
        summary["stamp"] = str(stamp)
    return summary


def remaining_product_hermes(text: str) -> list[str]:
    """Product-name leftovers that this overlay is required to remove."""
    leftover = []
    for needle in ("HERMES AGENT", "Give Hermes a task", "Hermes Agent"):
        if needle in text:
            leftover.append(needle)
    return leftover


def self_test() -> int:
    table = load_table()
    replacements = sorted_replacements(table)
    surfaces = {r["surface"] for r in replacements}
    required = {"empty-state-wordmark", "composer-placeholder", "product-name", "settings-about"}
    missing = required - surfaces
    if missing:
        print(f"FAIL: table missing surfaces {sorted(missing)}", file=sys.stderr)
        return 1

    sample = (
        "const WORDMARK='HERMES AGENT';\n"
        "placeholder:'Give Hermes a task';\n"
        "title:'About Hermes Desktop';\n"
        "name:'Hermes Agent';\n"
        "appName:'Hermes';\n"
        + "".join(f"protected:{token};\n" for token in table.get("protected") or [])
    )
    out, hits = apply_text(sample, replacements)
    leftover = remaining_product_hermes(out)
    if leftover:
        print(f"FAIL: product leftovers after overlay: {leftover}", file=sys.stderr)
        return 1
    if "Give Dragon AI a task" not in out or "DRAGON AI AGENT" not in out:
        print("FAIL: expected Dragon copy missing", file=sys.stderr)
        return 1
    if "About Dragon AI Agent" not in out:
        print("FAIL: settings about still unbranded", file=sys.stderr)
        return 1
    for token in table["protected"]:
        if token not in out:
            print(f"FAIL: protected token lost: {token}", file=sys.stderr)
            return 1
    if hits < 3:
        print(f"FAIL: expected several replacements, got {hits}", file=sys.stderr)
        return 1
    # Second pass is idempotent.
    out2, hits2 = apply_text(out, replacements)
    if out2 != out or hits2 != 0:
        print(f"FAIL: overlay not idempotent hits2={hits2}", file=sys.stderr)
        return 1
    print("OK  desktop_branding self-test")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Overlay Dragon AI Agent chrome on Hermes.exe UI files")
    parser.add_argument("--exe", default="", help="Path to on-disk Hermes.exe")
    parser.add_argument("--root", default="", help="Overlay a single unpacked resources/src directory")
    parser.add_argument("--table", default=str(TABLE_PATH), help="Replacement table JSON")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print apply summary as JSON")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    table = load_table(Path(args.table))
    if args.root:
        summary = overlay_roots([Path(args.root)], table)
    elif args.exe:
        summary = apply_to_exe(Path(args.exe), table)
    else:
        parser.error("pass --exe, --root, or --self-test")
        return 2

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            "Dragon AI Agent UI overlay: "
            f"{summary.get('replacementsApplied', 0)} replacements in "
            f"{summary.get('filesChanged', 0)} files"
        )
        if not summary.get("replacementsApplied"):
            print(
                "No unpacked renderer strings matched. "
                "If Hermes.exe still shows HERMES AGENT, the build packed UI into "
                "app.asar (integrity-protected) and needs an upstream Electron rebuild."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
