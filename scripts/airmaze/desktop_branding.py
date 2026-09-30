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
BRAND_DIR_NAME = "dragon-ai-branding"
HTML_MARK = 'data-dragon-ai-branding="ui-face"'
OLD_HTML_MARKS = ('data-dragon-ai-branding="outfit"',)
STYLESHEET_NAME = "dragon-ui.css"
CSS_APPEND_MARK = "/* dragon-ai-ui-face */"
LOGO_NAMES = ("dragon-ai-agent-logo.svg", "dragon-ai-agent-logo.png")

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


def branding_dir() -> Path:
    return HERE.parents[1] / "branding"


def logo_files() -> list[Path]:
    brand = branding_dir()
    return [brand / name for name in LOGO_NAMES if (brand / name).is_file()]


def font_pack_dir() -> Path | None:
    candidates = (
        HERE.parents[1] / "branding" / "fonts" / "syne",
        HERE.parents[1] / "branding" / "fonts" / "league-spartan",
        HERE.parents[1] / "branding" / "fonts" / "outfit",
        HERE / "fonts" / "syne",
        HERE / "fonts" / "league-spartan",
        HERE / "fonts" / "outfit",
    )
    for path in candidates:
        if (path / STYLESHEET_NAME).is_file() and any(path.glob("*.woff2")):
            return path
    return None


def sheet_for_css_file(sheet: str, css_path: Path, dest_root: Path) -> str:
    """Rewrite url(\"./file.woff2\") so it still hits the pack from this CSS file."""
    try:
        rel_dir = css_path.parent.resolve().relative_to(dest_root.resolve())
    except ValueError:
        prefix = f"./{BRAND_DIR_NAME}"
    else:
        if rel_dir == Path("."):
            prefix = f"./{BRAND_DIR_NAME}"
        else:
            prefix = f"{'/'.join(['..'] * len(rel_dir.parts))}/{BRAND_DIR_NAME}"
    return sheet.replace('url("./', f'url("{prefix}/')


def font_install_targets(roots: list[Path]) -> list[Path]:
    targets: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        posix = root.as_posix().replace("\\", "/")
        if posix.endswith("/src") or "/src/" in posix + "/":
            continue
        for cand in (root / "dist", root):
            if not cand.is_dir():
                continue
            resolved = cand.resolve()
            if resolved in seen:
                continue
            if (
                list(cand.glob("*.html"))
                or list(cand.glob("*.js"))
                or (cand / "assets").is_dir()
            ):
                seen.add(resolved)
                targets.append(resolved)
    return targets


def _link_tag() -> str:
    return f'<link rel="stylesheet" href="./{BRAND_DIR_NAME}/{STYLESHEET_NAME}" {HTML_MARK} />'


def inject_font_link(html: str) -> tuple[str, bool]:
    if HTML_MARK in html:
        return html, False
    link = _link_tag()
    changed = False
    out = html
    for old in OLD_HTML_MARKS:
        if old in out:
            out = out.replace(old, HTML_MARK.split("=")[0] + '="ui-face"')
            changed = True
    if HTML_MARK in out:
        return out, changed
    lower = out.lower()
    idx = lower.find("</head>")
    if idx != -1:
        return out[:idx] + link + "\n" + out[idx:], True
    idx = lower.find("<body")
    if idx != -1:
        return out[:idx] + link + "\n" + out[idx:], True
    return link + "\n" + out, True


def append_font_css(css_text: str, sheet: str) -> tuple[str, bool]:
    if CSS_APPEND_MARK in css_text:
        return css_text, False
    block = "\n" + CSS_APPEND_MARK + "\n" + sheet.rstrip() + "\n"
    return css_text.rstrip() + block, True


def install_font_pack(roots: list[Path]) -> dict[str, Any]:
    pack = font_pack_dir()
    if pack is None:
        return {"fontFamily": None, "targets": 0, "htmlPatched": 0, "copied": False}
    files = [
        p
        for p in pack.iterdir()
        if p.is_file() and p.suffix.lower() in {".woff2", ".css", ".txt", ".md"}
    ]
    html_patched = 0
    targets = font_install_targets(roots)
    for dest_root in targets:
        dest = dest_root / BRAND_DIR_NAME
        dest.mkdir(parents=True, exist_ok=True)
        for src in files:
            (dest / src.name).write_bytes(src.read_bytes())
        for src in logo_files():
            (dest / src.name).write_bytes(src.read_bytes())
        sheet = (dest / STYLESHEET_NAME).read_text(encoding="utf-8")
        css_targets = list(dest_root.glob("*.css")) + list((dest_root / "assets").glob("*.css") if (dest_root / "assets").is_dir() else [])
        for css_path in css_targets:
            if BRAND_DIR_NAME in css_path.parts:
                continue
            text = read_text_file(css_path)
            if text is None:
                continue
            rewritten = sheet_for_css_file(sheet, css_path, dest_root)
            out, changed = append_font_css(text, rewritten)
            if changed:
                css_path.write_bytes(out.encode("utf-8"))
        for html_path in dest_root.glob("*.html"):
            text = read_text_file(html_path)
            if text is None:
                continue
            out, changed = inject_font_link(text)
            if changed:
                html_path.write_bytes(out.encode("utf-8"))
                html_patched += 1
    return {
        "fontFamily": "Syne",
        "targets": len(targets),
        "htmlPatched": html_patched,
        "copied": bool(targets),
    }


def write_stamp(exe_path: Path, summary: dict[str, Any], table: dict[str, Any]) -> Path | None:
    resources = exe_path.parent / "resources"
    if not resources.is_dir():
        return None
    stamp = {
        "version": table.get("version"),
        "product": table.get("product"),
        "fontFamily": (table.get("font") or {}).get("family"),
        "filesChanged": summary["filesChanged"],
        "replacementsApplied": summary["replacementsApplied"],
        "font": summary.get("font"),
    }
    dest = resources / STAMP_NAME
    dest.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return dest


def apply_to_exe(exe_path: Path, table: dict[str, Any] | None = None) -> dict[str, Any]:
    table = table or load_table()
    exe = exe_path.resolve()
    roots = discover_roots(exe)
    summary = overlay_roots(roots, table)
    summary["font"] = install_font_pack(roots)
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
    required = {
        "empty-state-wordmark",
        "composer-placeholder",
        "product-name",
        "settings-about",
        "sidebar-default-bot",
    }
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
        "function defaultBotLabel(){return 'Hermes'}\n"
        "const sidebar=['Hermes','Personal Assistant'];\n"
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
    if "return 'Hermes'" in out or 'return "Hermes"' in out or 'return"Hermes"' in out:
        print("FAIL: default sidebar bot still labeled Hermes", file=sys.stderr)
        return 1
    if "Personal Assistant" not in out:
        print("FAIL: Personal Assistant must remain the user-facing sidebar bot", file=sys.stderr)
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
    pack = font_pack_dir()
    if pack is None or pack.name != "syne":
        print("FAIL: Syne font pack missing (branding/fonts/syne)", file=sys.stderr)
        return 1
    css = (pack / STYLESHEET_NAME).read_text(encoding="utf-8")
    if "@font-face" not in css or "Syne" not in css or ".wordmark" not in css:
        print("FAIL: dragon-ui.css must @font-face Syne onto the wordmark", file=sys.stderr)
        return 1
    if "font-weight: 700" not in css:
        print("FAIL: wordmark must use Syne at weight 700", file=sys.stderr)
        return 1
    if "font-family: \"Collapse\"" not in css and "font-family: 'Collapse'" not in css:
        print("FAIL: CSS must also register as Collapse so leftover wordmark rules switch face", file=sys.stderr)
        return 1
    if "Universal Sans" in css or "Tesla" in css or "Gotham" in css:
        print("FAIL: CSS must not claim Tesla / Universal Sans / Gotham", file=sys.stderr)
        return 1
    if "fonts.googleapis.com" in css or "family=Inter" in css or "Universal Sans" in css:
        print("FAIL: CSS must not load Inter or a second webfont", file=sys.stderr)
        return 1
    if "--color-primary: #c41e3a" not in css or "--color-ring: #c41e3a" not in css:
        print("FAIL: overlay CSS must ship applied crimson design tokens", file=sys.stderr)
        return 1
    if "dragon-ai-agent-logo.png" not in css and "dragon-ai-agent-logo.svg" not in css:
        print("FAIL: overlay CSS must pin the front-facing dragon mark", file=sys.stderr)
        return 1
    if "22rem" not in css or "z-index: 1" not in css or "z-index: 0" not in css:
        print("FAIL: empty-state mark must be large and sit behind the wordmark", file=sys.stderr)
        return 1
    if "overflow: visible" not in css or "72vw" in css:
        print("FAIL: mark must size to the intro pane and not clip into a box", file=sys.stderr)
        return 1
    if "calc(-50% + 5.9%)" not in css:
        print("FAIL: empty-state mark must shift right so the dragon artwork centers on the wordmark", file=sys.stderr)
        return 1
    if "background-color: transparent" not in css:
        print("FAIL: empty-state mark must not paint a boxed plate", file=sys.stderr)
        return 1
    if '[data-roster-key$="::default"]' not in css:
        print("FAIL: overlay CSS must hide the default Hermes sidebar bot", file=sys.stderr)
        return 1
    if "Personal Assistant" not in css and "sidebar" not in css.lower():
        print("FAIL: overlay CSS must keep Personal Assistant as the visible bot", file=sys.stderr)
        return 1
    logos = {p.name: p for p in logo_files()}
    if "dragon-ai-agent-logo.svg" not in logos or "dragon-ai-agent-logo.png" not in logos:
        print("FAIL: branding must ship SVG + PNG dragon mark", file=sys.stderr)
        return 1
    svg = logos["dragon-ai-agent-logo.svg"].read_text(encoding="utf-8")
    if "#314a73" not in svg.lower():
        print("FAIL: mark body must be navy #314A73", file=sys.stderr)
        return 1
    if "#c41e3a" not in svg.lower():
        print("FAIL: mark eyes must be red #C41E3A", file=sys.stderr)
        return 1
    for banned in ("#C4A574", "#E8C36A", "#F5C14A", "#B8863A"):
        if banned.lower() in svg.lower():
            print(f"FAIL: mark must not use gold/copper {banned}", file=sys.stderr)
            return 1
    npoly = svg.count("<polygon")
    if 'viewBox="0 0 256 256"' not in svg or npoly < 6 or npoly > 20:
        print(f"FAIL: mark must stay a few large facets (got {npoly} polygons)", file=sys.stderr)
        return 1
    if "<rect" in svg.lower() or "#0a0a0a" in svg.lower():
        print("FAIL: mark SVG must not include a boxed black plate", file=sys.stderr)
        return 1
    logo_meta = table.get("logo") or {}
    if logo_meta.get("facing") != "front":
        print("FAIL: table logo.facing must stay front (not a side profile)", file=sys.stderr)
        return 1
    if logo_meta.get("body") != "#314A73" or logo_meta.get("eyes") != "#C41E3A":
        print("FAIL: table must record navy body and red eyes", file=sys.stderr)
        return 1
    if logo_meta.get("boxed") is not False or logo_meta.get("stack") != "wordmark-in-front":
        print("FAIL: table must record an unboxed mark with the wordmark in front", file=sys.stderr)
        return 1
    sidebar = table.get("sidebar") or {}
    if sidebar.get("hideDefaultHermes") is not True:
        print("FAIL: table must hide the default Hermes sidebar bot", file=sys.stderr)
        return 1
    if sidebar.get("userFacingBots") != ["Personal Assistant"]:
        print("FAIL: table sidebar must list only Personal Assistant", file=sys.stderr)
        return 1
    if "prefers-reduced-motion" not in css or "focus-visible" not in css:
        print("FAIL: overlay CSS must keep visible focus and reduced-motion", file=sys.stderr)
        return 1
    design = table.get("designSystem") or {}
    if design.get("style") != "AI-Native UI":
        print("FAIL: table must record the UI UX Pro Max style", file=sys.stderr)
        return 1
    tokens = table.get("tokens") or {}
    if tokens.get("primary") != "#C41E3A":
        print("FAIL: table tokens.primary must stay dragon crimson", file=sys.stderr)
        return 1
    meta = table.get("font") or {}
    if meta.get("family") != "Syne":
        print("FAIL: table font.family must be Syne", file=sys.stderr)
        return 1
    collapse_sample = ".wordmark{font-family:'Collapse',var(--font-sans);font-weight:700}"
    collapse_out, _ = apply_text(collapse_sample, replacements)
    if "Collapse" in collapse_out or "Syne" not in collapse_out:
        print(f"FAIL: Collapse wordmark family not rewritten: {collapse_out}", file=sys.stderr)
        return 1
    fake_root = Path("/tmp/dragon-font-rel")
    fake_css = fake_root / "assets" / "index.css"
    rewritten = sheet_for_css_file('src: url("./syne-latin-700-normal.woff2")', fake_css, fake_root)
    if 'url("../dragon-ai-branding/syne-latin-700-normal.woff2")' not in rewritten:
        print(f"FAIL: appended CSS font urls must resolve from assets/: {rewritten}", file=sys.stderr)
        return 1
    html = "<html><head><title>t</title></head><body></body></html>"
    once, changed = inject_font_link(html)
    twice, changed2 = inject_font_link(once)
    if not changed or changed2 or twice != once or once.count(HTML_MARK) != 1:
        print("FAIL: font link inject is not idempotent", file=sys.stderr)
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
        root = Path(args.root)
        summary = overlay_roots([root], table)
        summary["font"] = install_font_pack([root])
    elif args.exe:
        summary = apply_to_exe(Path(args.exe), table)
    else:
        parser.error("pass --exe, --root, or --self-test")
        return 2

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        font = summary.get("font") or {}
        print(
            "Dragon AI Agent UI overlay: "
            f"{summary.get('replacementsApplied', 0)} replacements in "
            f"{summary.get('filesChanged', 0)} files "
            f"(font={font.get('fontFamily')})"
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
