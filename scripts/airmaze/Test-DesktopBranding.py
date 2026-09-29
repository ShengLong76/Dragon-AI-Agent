#!/usr/bin/env python3
"""Offline tests for the Dragon AI Agent Electron UI string overlay.

Proves the overlay actually rewrites empty-state / composer / settings copy
on a fake win-unpacked tree, and that Bot Screen / token / image wiring is
untouched. No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
TABLE = SCRIPTS / "desktop_branding.json"
ENGINE = SCRIPTS / "desktop_branding.py"
APPLY = SCRIPTS / "Apply-DesktopBranding.ps1"
FINDER = SCRIPTS / "Find-HermesDesktop.ps1"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
INSTALLERS = (
    ROOT / "scripts" / "airmaze" / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
COMPOSE = ROOT / "docker-compose.embedded.yml"
BRANDING = ROOT / "docs" / "airmaze" / "BRANDING.md"

PROTECTED = (
    "X-Hermes-Session-Token",
    "127.0.0.1:8650",
    "dragon-local",
    "hermes-airmaze-gw",
    "hermes-airmaze-desktop",
    "nousresearch/hermes-agent",
    "hermes://",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def test_table() -> dict:
    table = json.loads(read(TABLE))
    rows = table.get("replacements") or []
    by_from = {r["from"]: r["to"] for r in rows}
    expected = {
        "HERMES AGENT": "DRAGON AI AGENT",
        "Give Hermes a task": "Give Dragon AI a task",
        "Hermes Agent": "Dragon AI Agent",
        "About Hermes Desktop": "About Dragon AI Agent",
    }
    for src, dst in expected.items():
        if by_from.get(src) != dst:
            fail(f"table missing {src!r} -> {dst!r}")
    for token in PROTECTED:
        if token not in table.get("protected", []):
            fail(f"table must list protected token {token}")
    font = table.get("font") or {}
    if font.get("family") != "Syne" or "OFL" not in str(font.get("license")):
        fail("table must name Syne (OFL) as the UI face")
    if font.get("weight") != 700:
        fail("table must use Syne weight 700 on the wordmark")
    if "font-family: 'Collapse', var(--font-sans)" not in by_from:
        fail("table must rewrite the upstream Collapse wordmark family")
    print("OK  desktop_branding.json surfaces")
    return table


def test_engine_self() -> None:
    import desktop_branding as db  # noqa: WPS433

    if db.self_test() != 0:
        fail("desktop_branding --self-test failed")


def test_fake_unpacked_tree() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import desktop_branding as db  # noqa: WPS433

    renderer = """
const WORDMARK = 'HERMES AGENT';
export const copy = {
  placeholder: 'Give Hermes a task',
  about: 'About Hermes Desktop',
  product: 'Hermes Agent',
  appName: 'Hermes',
  settings: 'Loading Hermes settings',
  ready: 'Hermes Desktop is ready'
};
// Bot Screen / Remote wiring must survive the overlay:
const token = 'X-Hermes-Session-Token';
const serve = 'http://127.0.0.1:8650';
const image = 'nousresearch/hermes-agent:latest-desktop';
const container = 'hermes-airmaze-gw';
const sidecar = 'hermes-airmaze-desktop';
const session = 'dragon-local';
const protocol = 'hermes://copilot-key/start';
"""
    with tempfile.TemporaryDirectory(prefix="dragon-ui-brand-") as tmp:
        base = pathlib.Path(tmp)
        unpacked = base / "win-unpacked"
        dist = unpacked / "resources" / "app.asar.unpacked" / "dist"
        dist.mkdir(parents=True)
        exe = unpacked / "Hermes.exe"
        exe.write_bytes(b"MZ")
        js = dist / "renderer.js"
        js.write_text(renderer, encoding="utf-8")
        (dist / "index.html").write_text(
            "<!doctype html><html><head><title>Hermes</title></head><body><div id='root'></div></body></html>\n",
            encoding="utf-8",
        )
        (dist / "assets").mkdir(parents=True, exist_ok=True)
        (dist / "assets" / "index.css").write_text(
            ".wordmark{font-family:'Collapse',var(--font-sans);font-weight:700;text-transform:uppercase}\n",
            encoding="utf-8",
        )
        # Attribution / license must stay Hermes.
        (unpacked / "resources" / "app.asar.unpacked" / "LICENSE").write_text(
            "MIT Copyright (c) 2025 Nous Research. Hermes Agent.\n",
            encoding="utf-8",
        )

        summary = db.apply_to_exe(exe)
        if summary["replacementsApplied"] < 4:
            fail(f"overlay too weak: {summary}")
        branded = js.read_text(encoding="utf-8")
        for needle in ("HERMES AGENT", "Give Hermes a task", "Hermes Agent", "About Hermes Desktop"):
            if needle in branded:
                fail(f"renderer still has product chrome {needle!r}")
        if "DRAGON AI AGENT" not in branded or "Give Dragon AI a task" not in branded:
            fail("renderer missing Dragon empty-state / composer copy")
        if "Dragon AI Agent" not in branded:
            fail("renderer missing Dragon product name")
        if "About Dragon AI Agent" not in branded:
            fail("settings about still unbranded")
        for token in PROTECTED:
            if token not in branded:
                fail(f"overlay ate protected token {token}")
        license_txt = (unpacked / "resources" / "app.asar.unpacked" / "LICENSE").read_text(encoding="utf-8")
        if "Hermes Agent" not in license_txt:
            fail("overlay rewrote license attribution")
        stamp = unpacked / "resources" / ".dragon-ai-ui-branding.json"
        if not stamp.is_file():
            fail("missing branding stamp")
        pack_dir = dist / "dragon-ai-branding"
        vf = pack_dir / "syne-latin-wght-normal.woff2"
        bold = pack_dir / "syne-latin-700-normal.woff2"
        css = pack_dir / "dragon-ui.css"
        if not vf.is_file() or vf.read_bytes()[:4] != b"wOF2":
            fail("Syne variable woff2 was not copied into the unpacked renderer")
        if not bold.is_file() or bold.read_bytes()[:4] != b"wOF2":
            fail("Syne 700 woff2 was not copied into the unpacked renderer")
        css_txt = css.read_text(encoding="utf-8")
        if "@font-face" not in css_txt or "Syne" not in css_txt or ".wordmark" not in css_txt:
            fail("injected CSS missing Syne wordmark rules")
        if "font-weight: 700" not in css_txt:
            fail("wordmark CSS must set Syne at weight 700")
        bundled = (dist / "assets" / "index.css").read_text(encoding="utf-8")
        live_rule = bundled.split("/*", 1)[0]
        if "font-family:'Collapse'" in live_rule or "font-family: 'Collapse'" in live_rule:
            fail("unpacked .wordmark still names Collapse")
        if ".wordmark{font-family:'Syne'" not in live_rule:
            fail("unpacked .wordmark was not rewritten to Syne")
        if "dragon-ai-ui-face" not in bundled:
            fail("Syne rules were not appended to the renderer CSS")
        if 'url("../dragon-ai-branding/syne-latin-wght-normal.woff2")' not in bundled:
            fail("appended @font-face urls must resolve from assets/ to the Syne pack")
        html = (dist / "index.html").read_text(encoding="utf-8")
        if 'data-dragon-ai-branding="ui-face"' not in html:
            fail("index.html was not linked to the bundled wordmark stylesheet")
        if html.count("dragon-ui.css") != 1:
            fail("font stylesheet linked more than once")
        font_info = summary.get("font") or {}
        if font_info.get("fontFamily") != "Syne":
            fail(f"overlay did not report Syne: {font_info}")
        # Idempotent second pass.
        summary2 = db.apply_to_exe(exe)
        if summary2["replacementsApplied"] != 0:
            fail(f"second pass not idempotent: {summary2}")
        html2 = (dist / "index.html").read_text(encoding="utf-8")
        if html2.count('data-dragon-ai-branding="ui-face"') != 1:
            fail("second pass duplicated the wordmark stylesheet link")
        print("OK  fake win-unpacked overlay")


def test_packaging_not_regressed() -> None:
    compose = read(COMPOSE)
    for token in (
        "127.0.0.1:8650:8650",
        "hermes-airmaze-desktop",
        "nousresearch/hermes-agent",
        "HERMES_DASHBOARD_SESSION_TOKEN",
        "dragon-local",
    ):
        if token not in compose:
            fail(f"compose lost Bot Screen token {token}")
    launcher = read(LAUNCHER)
    if "Apply-DragonAIDesktopUiBranding" not in launcher and "Apply-DesktopBranding" not in launcher:
        fail("launcher/finder must apply the UI overlay before opening Hermes.exe")
    finder = read(FINDER)
    if "Apply-DragonAIDesktopUiBranding" not in finder:
        fail("Find-HermesDesktop.ps1 must call Apply-DragonAIDesktopUiBranding")
    if "Start-HermesDesktopClient" not in finder:
        fail("finder lost Start-HermesDesktopClient")
    apply_ps = read(APPLY)
    if "app.asar.unpacked" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must target unpacked renderer files")
    if "Install-DragonAIDesktopFontPack" not in apply_ps or "Syne" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must install the bundled Syne pack")
    for path in INSTALLERS:
        text = read(path)
        if "Apply-DesktopBranding.ps1" not in text or "desktop_branding.py" not in text:
            fail(f"{path.name} must install the UI overlay scripts")
        if "branding\\fonts" not in text and "branding/fonts" not in text:
            fail(f"{path.name} must copy branding/fonts for the wordmark overlay")
    branding = read(BRANDING)
    if "HERMES AGENT" not in branding and "empty state" not in branding.lower():
        fail("BRANDING.md must document the in-app overlay and leftovers")
    if "app.asar" not in branding:
        fail("BRANDING.md must say what still needs an Electron rebuild")
    if "Syne" not in branding or "OFL" not in branding:
        fail("BRANDING.md must name Syne and why (OFL, weight 700)")
    if "Collapse" not in branding:
        fail("BRANDING.md must name the upstream Collapse wordmark face")
    if "Universal Sans" not in branding:
        fail("BRANDING.md must say Universal Sans is proprietary and not shipped")
    pack = ROOT / "branding" / "fonts" / "syne"
    if not (pack / "OFL.txt").is_file() or not (pack / "syne-latin-wght-normal.woff2").is_file():
        fail("branding/fonts/syne must bundle OFL.txt and the Syne woff2 files")
    if not (pack / "syne-latin-700-normal.woff2").is_file():
        fail("branding/fonts/syne must include the 700 cut for the wordmark")
    print("OK  packaging Bot Screen / installer wiring")


def main() -> int:
    sys.path.insert(0, str(SCRIPTS))
    test_table()
    test_engine_self()
    test_fake_unpacked_tree()
    test_packaging_not_regressed()
    print("SMOKE OK: empty state, composer, and settings product copy overlay Dragon AI Agent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
