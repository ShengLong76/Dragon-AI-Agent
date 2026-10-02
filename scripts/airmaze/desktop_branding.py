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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from private_desktop import assert_private_dragon_path, is_private_dragon_path

# Refuse branding outside DragonAIAgent (standalone Hermes tree is not mutated).

HERE = Path(__file__).resolve().parent
TABLE_PATH = HERE / "desktop_branding.json"
BRAND_DIR_NAME = "dragon-ai-branding"
HTML_MARK = 'data-dragon-ai-branding="ui-face"'
SIDEBAR_SCRIPT_MARK = 'data-dragon-ai-branding="sidebar-header"'
TEAMS_SCRIPT_MARK = 'data-dragon-ai-branding="teams-picker"'
VOICE_SCRIPT_MARK = 'data-dragon-ai-branding="voice-provider"'
OLD_HTML_MARKS = ('data-dragon-ai-branding="outfit"',)
STYLESHEET_NAME = "dragon-ui.css"
CSS_APPEND_MARK = "/* dragon-ai-ui-face */"
LOCKUP_WRAP_MARK = "dragon-ai-lockup-wrap:1"
SIDEBAR_SCRIPT_NAME = "sidebar-header.js"
TEAMS_SCRIPT_NAME = "teams-picker.js"
PACK_FILE_SUFFIXES = {".woff2", ".css", ".txt", ".md", ".js"}
LOGO_NAMES = ("dragon-ai-agent-logo.svg", "dragon-ai-agent-logo.png")
PNG_ICON_NAMES = ("icon.png", "apple-touch-icon.png")
APP_USER_MODEL_ID = "com.nousresearch.hermes"
CRIMSON_LOCKUP_BORDER_RE = re.compile(
    r"border\s*:\s*1px\s+solid\s+rgba\(\s*196\s*,\s*30\s*,\s*58\s*,\s*[^)]+\)",
    re.IGNORECASE,
)

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


def extra_install_unpacked_roots() -> list[Path]:
    """Also land assets under %LOCALAPPDATA%\\DragonAIAgent\\...\\app.asar.unpacked."""
    roots: list[Path] = []
    local = os.environ.get("LOCALAPPDATA") or ""
    if not local:
        return roots
    seed = Path(local) / "DragonAIAgent"
    if not seed.is_dir():
        return roots
    for unpacked in seed.rglob("app.asar.unpacked"):
        if not unpacked.is_dir():
            continue
        if "node_modules" in unpacked.parts:
            continue
        roots.append(unpacked)
    return roots


def discover_roots(exe_path: Path) -> list[Path]:
    assert_private_dragon_path(exe_path)
    exe_dir = exe_path.parent
    roots: list[Path] = []
    seen: set[Path] = set()
    for rel in (
        Path("resources") / "app.asar.unpacked",
        Path("resources") / "app",
    ):
        candidate = exe_dir / rel
        if candidate.exists():
            roots.append(candidate)
            seen.add(candidate.resolve())
    desktop_root = exe_dir.parent.parent
    if is_private_dragon_path(desktop_root):
        intro = desktop_root / "src" / "components" / "chat" / "intro.tsx"
        if intro.is_file():
            src = desktop_root / "src"
            roots.append(src)
            seen.add(src.resolve())
        dist = desktop_root / "dist"
        if dist.is_dir() and dist.resolve() not in seen:
            roots.append(dist)
            seen.add(dist.resolve())
    for extra in extra_install_unpacked_roots():
        resolved = extra.resolve()
        if resolved not in seen:
            roots.append(extra)
            seen.add(resolved)
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


def strip_crimson_lockup_border(text: str) -> tuple[str, int]:
    out, n = CRIMSON_LOCKUP_BORDER_RE.subn("border:0", text)
    return out, n


def overlay_file(path: Path, table: dict[str, Any], replacements: list[dict[str, str]]) -> int:
    text = read_text_file(path)
    if text is None:
        return 0
    out, hits = apply_text(text, replacements)
    out, extra = apply_source_only(path, table, out)
    hits += extra
    out, stripped = strip_crimson_lockup_border(out)
    hits += stripped
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
    found = [brand / name for name in LOGO_NAMES if (brand / name).is_file()]
    missing = [name for name in LOGO_NAMES if not (brand / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Apply-DesktopBranding: missing required logo "
            + ", ".join(missing)
            + f" under {brand}"
        )
    return found


def png_icon_source() -> Path:
    png = branding_dir() / "dragon-ai-agent-logo.png"
    if not png.is_file():
        raise FileNotFoundError(
            f"Apply-DesktopBranding: missing required logo {png.name} under {png.parent}"
        )
    return png


def team_icon_files() -> list[Path]:
    folder = branding_dir() / "teams"
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".svg"
    )


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


def pack_script_path(name: str) -> Path:
    pack = font_pack_dir()
    if pack is not None and (pack / name).is_file():
        return pack / name
    return branding_dir() / "fonts" / "syne" / name


def load_pack_script(name: str) -> str:
    path = pack_script_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"branding inject script missing: {path}")
    return path.read_text(encoding="utf-8").strip()


def wrap_marked_script(mark: str, body: str) -> str:
    return f"<script {mark}>\n{body.rstrip()}\n</script>"


def sidebar_header_script() -> str:
    return wrap_marked_script(SIDEBAR_SCRIPT_MARK, load_pack_script(SIDEBAR_SCRIPT_NAME))


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


def _insert_before_close(html: str, snippet: str) -> tuple[str, bool]:
    lower = html.lower()
    idx = lower.find("</head>")
    if idx != -1:
        return html[:idx] + snippet + "\n" + html[idx:], True
    idx = lower.find("</body>")
    if idx != -1:
        return html[:idx] + snippet + "\n" + html[idx:], True
    return html + "\n" + snippet + "\n", True


def upsert_marked_script(html: str, mark: str, script: str) -> tuple[str, bool]:
    """Replace a previously injected marked script so launch overlays refresh."""
    start = html.find(f"<script {mark}>")
    if start == -1:
        mark_at = html.lower().find(mark.lower())
        if mark_at == -1:
            return _insert_before_close(html, script)
        start = html.rfind("<script", 0, mark_at)
        if start == -1:
            return _insert_before_close(html, script)
    end = html.find("</script>", start)
    if end == -1:
        return _insert_before_close(html, script)
    end += len("</script>")
    current = html[start:end]
    if current == script:
        return html, False
    return html[:start] + script + html[end:], True


def inject_sidebar_header_script(html: str) -> tuple[str, bool]:
    return upsert_marked_script(html, SIDEBAR_SCRIPT_MARK, sidebar_header_script())


def teams_picker_script() -> str:
    return wrap_marked_script(TEAMS_SCRIPT_MARK, load_pack_script(TEAMS_SCRIPT_NAME))


def inject_teams_picker_script(html: str) -> tuple[str, bool]:
    return upsert_marked_script(html, TEAMS_SCRIPT_MARK, teams_picker_script())


def voice_selector_js_path() -> Path:
    return branding_dir() / "voice" / "dragon-voice-selector.js"


def voice_provider_script() -> str:
    """GPT | Grok selector plus overlay Grok duplex client. GPT stays."""
    path = voice_selector_js_path()
    body = path.read_text(encoding="utf-8").strip()
    if VOICE_SCRIPT_MARK in body:
        raise ValueError("voice selector JS must not include its own script mark")
    return f"<script {VOICE_SCRIPT_MARK}>\n{body}\n</script>"


def inject_voice_provider_script(html: str) -> tuple[str, bool]:
    return upsert_marked_script(html, VOICE_SCRIPT_MARK, voice_provider_script())


def inject_html_branding(html: str) -> tuple[str, bool]:
    out, changed = inject_font_link(html)
    out2, changed2 = inject_sidebar_header_script(out)
    out3, changed3 = inject_teams_picker_script(out2)
    out4, changed4 = inject_voice_provider_script(out3)
    out5, stripped = strip_crimson_lockup_border(out4)
    return out5, changed or changed2 or changed3 or changed4 or bool(stripped)


def append_font_css(css_text: str, sheet: str) -> tuple[str, bool]:
    block = CSS_APPEND_MARK + "\n" + sheet.rstrip() + "\n"
    if CSS_APPEND_MARK in css_text:
        start = css_text.find(CSS_APPEND_MARK)
        out = css_text[:start] + block
        return out, out != css_text
    return css_text.rstrip() + "\n" + block, True


def install_font_pack(roots: list[Path], required: bool = True) -> dict[str, Any]:
    pack = font_pack_dir()
    if pack is None:
        if required:
            raise FileNotFoundError(
                "Apply-DesktopBranding: dragon-ui.css pack missing under branding/fonts/syne"
            )
        return {"fontFamily": None, "targets": 0, "htmlPatched": 0, "copied": False}
    files = [
        p
        for p in pack.iterdir()
        if p.is_file() and p.suffix.lower() in PACK_FILE_SUFFIXES
    ]
    html_patched = 0
    targets = font_install_targets(roots)
    for dest_root in targets:
        dest = dest_root / BRAND_DIR_NAME
        dest.mkdir(parents=True, exist_ok=True)
        for src in files:
            (dest / src.name).write_bytes(src.read_bytes())
        logos = logo_files()
        for src in logos:
            (dest / src.name).write_bytes(src.read_bytes())
        for src in logos:
            landed_logo = dest / src.name
            if not landed_logo.is_file() or landed_logo.stat().st_size < 1:
                raise FileNotFoundError(
                    f"Apply-DesktopBranding: missing required logo {src.name} did not land in {dest}"
                )
        icons_dest = dest / "teams"
        icons_dest.mkdir(parents=True, exist_ok=True)
        for src in team_icon_files():
            (icons_dest / src.name).write_bytes(src.read_bytes())
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
            out, changed = inject_html_branding(text)
            if changed:
                html_path.write_bytes(out.encode("utf-8"))
                html_patched += 1
        landed = dest / STYLESHEET_NAME
        if required and (not landed.is_file() or LOCKUP_WRAP_MARK not in landed.read_text(encoding="utf-8")):
            raise FileNotFoundError(
                f"Apply-DesktopBranding: {STYLESHEET_NAME} with wrap rules did not land in {dest}"
            )
    if required and not targets:
        raise FileNotFoundError(
            "Apply-DesktopBranding: no unpacked dist target for dragon-ai-branding "
            "(resources/app.asar.unpacked/dist)"
        )
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


def icon_source() -> Path | None:
    """Prefer the sidebar-mark ICO the installer already ships."""
    candidates = (
        branding_dir() / "dragon-ai-agent-logo.ico",
        HERE.parents[1] / "installer" / "winres" / "icon.ico",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _add_unique(dests: list[Path], seen: set[Path], path: Path) -> None:
    key = path
    try:
        key = path.resolve()
    except OSError:
        key = path
    if key in seen:
        return
    seen.add(key)
    dests.append(path)


def icon_destinations(exe_path: Path, filename: str = "icon.ico") -> list[Path]:
    """Hermes / electron-builder icon locations next to the live exe."""
    exe_dir = exe_path.resolve().parent
    resources = exe_dir / "resources"
    dests: list[Path] = []
    seen: set[Path] = set()

    _add_unique(dests, seen, resources / filename)
    _add_unique(dests, seen, exe_dir / filename)
    for parent in (resources / "app", resources / "app.asar.unpacked"):
        if parent.is_dir():
            _add_unique(dests, seen, parent / filename)
    if filename == "apple-touch-icon.png":
        for parent in (
            resources / "app.asar.unpacked" / "dist",
            resources / "app.asar.unpacked" / "public",
            resources / "app" / "dist",
            resources / "app" / "public",
        ):
            if parent.is_dir():
                _add_unique(dests, seen, parent / filename)
    if resources.is_dir():
        for hit in resources.rglob(filename):
            if "node_modules" in hit.parts:
                continue
            _add_unique(dests, seen, hit)
    return dests


def png_destinations(exe_path: Path) -> list[Path]:
    """Electron PNG candidates Hermes app-icon.ts / tray actually read."""
    dests: list[Path] = []
    seen: set[Path] = set()
    for name in PNG_ICON_NAMES:
        for path in icon_destinations(exe_path, name):
            _add_unique(dests, seen, path)
    return dests


def try_stamp_pe_icon(exe_path: Path, ico: Path) -> dict[str, Any]:
    """Best-effort Hermes.exe PE icon via rcedit. Never blocks launch."""
    for name in ("rcedit", "rcedit-x64", "rcedit.exe"):
        tool = shutil.which(name)
        if not tool:
            continue
        try:
            proc = subprocess.run(
                [tool, str(exe_path), "--set-icon", str(ico)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0:
                return {"stamped": True, "tool": name}
            return {"stamped": False, "reason": proc.stderr.strip() or proc.stdout.strip() or "rcedit-failed"}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"stamped": False, "reason": str(exc)}
    return {"stamped": False, "reason": "no-rcedit"}


def stamp_app_icon(exe_path: Path) -> dict[str, Any]:
    """Copy Dragon ICO + PNG over Hermes icon paths. PE stamp is best-effort."""
    exe = exe_path.resolve()
    assert_private_dragon_path(exe)
    src = icon_source()
    if src is None:
        raise FileNotFoundError(
            "Apply-DesktopBranding: missing required logo dragon-ai-agent-logo.ico"
        )
    png = png_icon_source()
    payload = src.read_bytes()
    png_payload = png.read_bytes()
    written: list[str] = []
    for dest in icon_destinations(exe):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        written.append(str(dest))
    png_written: list[str] = []
    for dest in png_destinations(exe):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png_payload)
        png_written.append(str(dest))
    ico_landed = exe.parent / "resources" / "icon.ico"
    if not ico_landed.is_file() or ico_landed.read_bytes() != payload:
        raise FileNotFoundError(
            f"Apply-DesktopBranding: Dragon ICO did not land at {ico_landed}"
        )
    pe = try_stamp_pe_icon(exe, src)
    return {
        "copied": True,
        "path": written[0] if written else "",
        "paths": written,
        "pngPaths": png_written,
        "source": src.name,
        "pngSource": png.name,
        "appUserModelId": APP_USER_MODEL_ID,
        "pe": pe,
    }


def apply_to_exe(exe_path: Path, table: dict[str, Any] | None = None) -> dict[str, Any]:
    table = table or load_table()
    exe = exe_path.resolve()
    assert_private_dragon_path(exe)
    roots = discover_roots(exe)
    summary = overlay_roots(roots, table)
    summary["font"] = install_font_pack(roots)
    summary["icon"] = stamp_app_icon(exe)
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
    if logo_meta.get("trayPng") != "apple-touch-icon.png":
        print("FAIL: table must record apple-touch-icon.png as the Electron tray PNG", file=sys.stderr)
        return 1
    sidebar = table.get("sidebar") or {}
    if sidebar.get("hideDefaultHermes") is not True:
        print("FAIL: table must hide the default Hermes sidebar bot", file=sys.stderr)
        return 1
    if sidebar.get("excludeHermes") is not True:
        print("FAIL: table must exclude Hermes (not hide-only)", file=sys.stderr)
        return 1
    ids = {str(x).lower() for x in (sidebar.get("excludedProfileIds") or [])}
    if "default" not in ids or "hermes" not in ids:
        print("FAIL: table must list excluded profile ids default and hermes", file=sys.stderr)
        return 1
    if sidebar.get("headerTitle") != "Dragon AI":
        print("FAIL: sidebar header title must be Dragon AI", file=sys.stderr)
        return 1
    if sidebar.get("userFacingBots") != ["Personal Assistant"]:
        print("FAIL: table sidebar must list only Personal Assistant", file=sys.stderr)
        return 1
    if '[data-dragon-ai-sidebar-brand]' not in css or "Dragon AI" not in css:
        print("FAIL: overlay CSS must style the sidebar header lockup (Dragon AI)", file=sys.stderr)
        return 1
    if LOCKUP_WRAP_MARK not in css:
        print("FAIL: dragon-ui.css must stamp dragon-ai-lockup-wrap so unpacked copies can be verified", file=sys.stderr)
        return 1
    if "container-type: inline-size" not in css or "@container" not in css:
        print("FAIL: dragon-ui.css must ship container wrap rules for the Teams button", file=sys.stderr)
        return 1
    if "flex-direction: column" not in css or "min-width: max-content" in css:
        print("FAIL: sidebar Teams must stack under the logo with the full label visible", file=sys.stderr)
        return 1
    if "dragon-ai-marketplace-label:1" not in css or "dragon-ai-marketplace-blue:1" not in css:
        print("FAIL: dragon-ui.css must stamp Marketplace label + blue button", file=sys.stderr)
        return 1
    if "#2563eb" not in css.lower() or "dragon-ai-logo-clearance:1" not in css:
        print("FAIL: Marketplace must be blue and the logo must keep reserved clearance", file=sys.stderr)
        return 1
    if "dragon-ai-composer-chrome:1" not in css:
        print("FAIL: dragon-ui.css must stamp composer chrome", file=sys.stderr)
        return 1
    if "rgba(196,30,58" in css.replace(" ", "") or "rgba(196, 30, 58" in css:
        print("FAIL: overlay CSS must not paint a crimson lockup border", file=sys.stderr)
        return 1
    if "18cqi" in css or "clamp(20px, 18cqi, 32px)" in css:
        print("FAIL: sidebar logo must stay a fixed 32px (do not clamp/shrink with column width)", file=sys.stderr)
        return 1
    if "--dragon-sidebar-control-height: 32px" not in css:
        print("FAIL: sidebar logo height must match the 32px Teams button at full column width", file=sys.stderr)
        return 1
    if 'height: 32px' not in css or "flex: 0 0 32px" not in css:
        print("FAIL: sidebar logo must be a reserved 32px square matching Teams", file=sys.stderr)
        return 1
    if "[data-dragon-ai-sidebar-brand] img" in css and "height: 28px" in css.split("[data-dragon-ai-sidebar-brand] img", 1)[-1][:400]:
        print("FAIL: sidebar logo must not stay at 28px; match the Teams button", file=sys.stderr)
        return 1
    brand_img_css = css.split("[data-dragon-ai-sidebar-brand] img", 1)[-1][:700] if "[data-dragon-ai-sidebar-brand] img" in css else ""
    if "border: 0" not in brand_img_css and "border: none" not in brand_img_css:
        print("FAIL: sidebar logo must have no border", file=sys.stderr)
        return 1
    if "background: transparent" not in brand_img_css and "background-color: transparent" not in brand_img_css:
        print("FAIL: sidebar logo must have a transparent background", file=sys.stderr)
        return 1
    if "#c41e3a" in brand_img_css.lower() or "#C41E3A" in brand_img_css:
        print("FAIL: sidebar logo must not use a red border or plate", file=sys.stderr)
        return 1
    if '[role="alert"]' not in css or "text-overflow: ellipsis" not in css or "-webkit-line-clamp: 2" not in css:
        print("FAIL: overlay CSS must contain/ellipsis center-column RPC error banners", file=sys.stderr)
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
    if tokens.get("headerBand") != "#2563EB":
        print("FAIL: table tokens.headerBand must be Marketplace blue #2563EB", file=sys.stderr)
        return 1
    if tokens.get("mutedForeground") != "#C4C4CE":
        print("FAIL: table mutedForeground must be Grok-like #C4C4CE", file=sys.stderr)
        return 1
    if tokens.get("fontSizeBody") != "16px" or tokens.get("lineHeightBody") != "1.55":
        print("FAIL: table must record 16px / 1.55 body type", file=sys.stderr)
        return 1
    if "--dragon-ui-font-size-body: 16px" not in css or "--conversation-text-base-size: 16px" not in css:
        print("FAIL: overlay CSS must remap Hermes chat to 16px body", file=sys.stderr)
        return 1
    if "--ui-text-tertiary: #c4c4ce" not in css or "--color-muted-foreground: #c4c4ce" not in css:
        print("FAIL: overlay CSS must replace 54% tertiary with opaque #c4c4ce", file=sys.stderr)
        return 1
    if '[data-slot="aui_assistant-message-content"]' not in css:
        print("FAIL: overlay CSS must style chat message type size", file=sys.stderr)
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
    once, changed = inject_html_branding(html)
    twice, changed2 = inject_html_branding(once)
    if not changed or changed2 or twice != once or once.count(HTML_MARK) != 1:
        print("FAIL: font link inject is not idempotent", file=sys.stderr)
        return 1
    if once.count(SIDEBAR_SCRIPT_MARK) != 1 or "Dragon AI" not in once:
        print("FAIL: sidebar header script must inject Dragon AI once", file=sys.stderr)
        return 1
    if "findColumnHost" not in once or "data-dragon-ai-sidebar-fixed" not in once:
        print("FAIL: sidebar inject must try column hosts then body data-dragon-ai-sidebar-fixed", file=sys.stderr)
        return 1
    if "findInFlowColumn" not in once or "data-dragon-ai-sidebar-chrome" not in once:
        print("FAIL: sidebar inject must prefer in-flow chrome above Sessions/Bots", file=sys.stderr)
        return 1
    if "lockup → Teams Marketplace → Sessions/Bots" not in once:
        print("FAIL: sidebar inject must document DOM order lockup → Teams Marketplace → Sessions/Bots", file=sys.stderr)
        return 1
    if "findBotsTab" not in once or "data-dragon-ai-sidebar-clearance" not in once:
        print("FAIL: sidebar inject must reserve clearance so the overlay does not cover BOTS", file=sys.stderr)
        return 1
    if re.search(r'querySelector\(\s*[\'"]\[data-slot="sidebar-wrapper"\]', once):
        print("FAIL: sidebar inject must not treat sidebar-wrapper as a column host", file=sys.stderr)
        return 1
    if "pinWrap" not in once or "border:0" not in once.replace(" ", ""):
        print("FAIL: sidebar inject must pin the lockup with border:0 (no crimson frame)", file=sys.stderr)
        return 1
    if "rgba(196,30,58" in once.replace(" ", "") or "rgba(196, 30, 58" in once:
        print("FAIL: sidebar/teams inject must not set a crimson lockup border", file=sys.stderr)
        return 1
    if "dragon-ai-agent-logo.svg" not in once:
        print("FAIL: sidebar header script must use the transparent SVG mark", file=sys.stderr)
        return 1
    bordered = (
        '<html><head></head><body>'
        '<div data-dragon-ai-sidebar-brand style="border:1px solid rgba(196,30,58,.45)"></div>'
        '</body></html>'
    )
    cleaned, cleaned_changed = inject_html_branding(bordered)
    if not cleaned_changed or "rgba(196,30,58" in cleaned.replace(" ", ""):
        print("FAIL: overlay must strip a live crimson lockup border from index.html", file=sys.stderr)
        return 1
    stale = once.replace("dragon-ai-agent-logo.svg", "dragon-ai-agent-logo.png")
    refreshed, refreshed_changed = inject_html_branding(stale)
    if not refreshed_changed or "dragon-ai-agent-logo.svg" not in refreshed:
        print("FAIL: overlay must refresh a stale PNG sidebar script to the SVG mark", file=sys.stderr)
        return 1
    if once.count(TEAMS_SCRIPT_MARK) != 1 or "Teams Marketplace" not in once:
        print("FAIL: Teams Marketplace script must inject into the desktop client", file=sys.stderr)
        return 1
    if "data-dragon-ai-sidebar-fixed" not in once:
        print("FAIL: Teams Marketplace inject must share the body fixed-overlay fallback", file=sys.stderr)
        return 1
    if once.count(VOICE_SCRIPT_MARK) != 1 or "GPT" not in once or "Grok" not in once:
        print("FAIL: voice selector must inject GPT and Grok (GPT stays)", file=sys.stderr)
        return 1
    if "Talk with Grok" not in once or "xai-client-secret." not in once:
        print("FAIL: overlay must host Grok duplex (Talk + xai-client-secret)", file=sys.stderr)
        return 1
    if "Start conversation" not in once or "findComposerAction" not in once:
        print("FAIL: overlay must integrate Start conversation into the composer action", file=sys.stderr)
        return 1
    if "input_audio_buffer.append" not in once or "grok-voice-latest" not in once:
        print("FAIL: overlay must send official STS append events to grok-voice-latest", file=sys.stderr)
        return 1
    if not voice_selector_js_path().is_file():
        print("FAIL: branding/voice/dragon-voice-selector.js missing", file=sys.stderr)
        return 1
    if "data-dragon-ai-team-seats" not in once or "descriptionDetail" not in once:
        print("FAIL: Teams picker must list seats with brief + hover detail", file=sys.stderr)
        return 1
    if "data-dragon-ai-seat-icon" not in once or "dragon-ai-branding/teams/" not in once:
        print("FAIL: Teams picker must load per-seat icons from the branding pack", file=sys.stderr)
        return 1
    if not any(p.name == "seo-specialist.svg" for p in team_icon_files()):
        print("FAIL: branding/teams must ship SEO Specialist icon", file=sys.stderr)
        return 1
    if "[data-dragon-ai-teams-panel]" not in css:
        print("FAIL: overlay CSS must style the in-app Teams screen", file=sys.stderr)
        return 1
    if "[data-dragon-ai-teams-backdrop]" not in css or "left: 50%" not in css:
        print("FAIL: overlay CSS must style a centered Teams Marketplace popup", file=sys.stderr)
        return 1
    if "[data-dragon-ai-seat-tooltip]" not in css:
        print("FAIL: overlay CSS must style seat hover/focus detail", file=sys.stderr)
        return 1
    if "[data-dragon-voice-provider]" not in css or "[aria-checked=" not in css:
        print("FAIL: overlay CSS must style the GPT | Grok voice selector", file=sys.stderr)
        return 1
    if "[data-dragon-grok-talk]" not in css:
        print("FAIL: overlay CSS must style Talk with Grok", file=sys.stderr)
        return 1
    voice_meta = table.get("voice") or {}
    if voice_meta.get("options") != ["gpt", "grok"] or voice_meta.get("default") != "gpt":
        print("FAIL: table voice.options must be gpt + grok with GPT as default", file=sys.stderr)
        return 1
    if icon_source() is None:
        print("FAIL: Dragon ICO missing for taskbar/resources/icon.ico", file=sys.stderr)
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
        assert_private_dragon_path(root)
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
