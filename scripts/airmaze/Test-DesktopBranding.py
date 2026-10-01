#!/usr/bin/env python3
"""Offline tests for the Dragon AI Agent Electron UI string overlay.

Proves the overlay actually rewrites empty-state / composer / settings copy
on a fake win-unpacked tree, and that Bot Screen / token / image wiring is
untouched. No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import pathlib
import re
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


def _lin(channel: int) -> float:
    value = channel / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _rel_luminance(hex_color: str) -> float:
    raw = hex_color.removeprefix("#")
    red, green, blue = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(red) + 0.7152 * _lin(green) + 0.0722 * _lin(blue)


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_rel_luminance(foreground), _rel_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def _js_code_only(text: str) -> str:
    stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*?$", "", stripped, flags=re.M)


def assert_sidebar_host_fallback(sidebar_js: str, teams_js: str, css: str) -> None:
    for label, text in (("sidebar-header.js", sidebar_js), ("teams-picker.js", teams_js)):
        if "findColumnHost" not in text:
            fail(f"{label} must try column hosts first")
        if "findDragonSidebarHost" not in text:
            fail(f"{label} must share findDragonSidebarHost")
        if 'sidebar-header' not in text or 'sidebar-inner' not in text:
            fail(f"{label} must still prefer sidebar-header / sidebar-inner")
        if "data-dragon-ai-sidebar-fixed" not in text:
            fail(f"{label} must fall back to data-dragon-ai-sidebar-fixed on body")
        if "document.body" not in text:
            fail(f"{label} must mount the fixed overlay on document.body")
        if "findBotsTab" not in text or "data-dragon-ai-sidebar-clearance" not in text:
            fail(f"{label} must reserve clearance so the overlay does not cover the BOTS tab")
        compact = text.replace(" ", "")
        if "vartop=96" not in compact:
            fail(f"{label} fixed overlay default top must be 96px (48px sits on BOTS)")
        if "vartop=48" in compact:
            fail(f"{label} must not default overlay top to 48px (covers BOTS)")
        if "return96" not in compact:
            fail(f"{label} lockupHeight must reserve 96px so wrapped Teams Marketplace does not cover BOTS")
        if "return48" in compact:
            fail(f"{label} lockupHeight must not default to 48px (covers BOTS)")
        if "spacer||strip" in compact or "(spacer||strip)" in compact:
            fail(f"{label} must pin overlay to the clearance spacer, never the BOTS tab strip")
        if "sidebar-wrapper" in _js_code_only(text):
            fail(f"{label} must not treat sidebar-wrapper as a column host")
    if "Teams Marketplace" not in teams_js:
        fail("teams-picker.js control label must be Teams Marketplace")
    if re.search(r'textContent\s*=\s*"Teams"', teams_js):
        fail("user-visible control label must be Teams Marketplace, not Teams")
    if "[data-dragon-ai-sidebar-fixed]" not in css:
        fail("dragon-ui.css must style the body fixed overlay")
    if "min-width: 16rem" not in css:
        fail("fixed overlay row must keep a 16rem width (not collapse to ~24px)")
    css_code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if re.search(r"\[data-dragon-ai-sidebar-fixed\]\s*\{[^}]*container-type", css_code):
        fail("fixed overlay must not set container-type (collapses to ~24px)")
    if "@media (max-width: 1100px)" not in css:
        fail("overlay path must wrap Teams Marketplace with @media (max-width: 1100px)")
    if "container-type: inline-size" not in css or "@container" not in css:
        fail("real sidebar slots must keep @container wrap")
    fixed_rule = re.search(r"\[data-dragon-ai-sidebar-fixed\]\s*\{[^}]*\}", css_code)
    if not fixed_rule or "top: 96px" not in fixed_rule.group(0):
        fail("fixed overlay CSS default top must be 96px (clear of BOTS)")
    if "top: 48px" in fixed_rule.group(0):
        fail("fixed overlay CSS default must not sit on the BOTS tab (top: 48px)")
    if "[data-dragon-ai-sidebar-clearance]" not in css or "min-height: 96px" not in css:
        fail("clearance spacer must reserve 96px above the BOTS tab")
    name_block = css.split("[data-slot=\"bots-roster\"]", 1)[-1][:900]
    if "font-size: var(--dragon-ui-font-size-body)" not in name_block:
        fail("sidebar bot names must use the 16px body size (match middle session names)")
    if 'text-[0.8125rem]' not in css:
        fail("Hermes 0.8125rem name chips must remap to 16px body")
    if "[data-sidebar=\"menu-button\"]" not in name_block:
        fail("sidebar menu-button names must share the 16px body size")
    if "[role=\"dialog\"]" not in name_block or "[role=\"listbox\"]" not in name_block:
        fail("middle session/agent names must share the 16px body size")


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
    design = table.get("designSystem") or {}
    if "ui-ux-pro-max" not in str(design.get("skill")):
        fail("table must point at the in-repo UI UX Pro Max skill")
    if design.get("style") != "AI-Native UI":
        fail("table must record AI-Native UI as the applied style")
    tokens = table.get("tokens") or {}
    if tokens.get("primary") != "#C41E3A" or tokens.get("background") != "#1C1C20":
        fail("table tokens must keep dragon crimson on dark surfaces")
    if tokens.get("mutedForeground") != "#C4C4CE":
        fail("table mutedForeground must be Grok-like #C4C4CE (not washed #A0A0AA)")
    if tokens.get("fontSizeBody") != "16px" or tokens.get("lineHeightBody") != "1.55":
        fail("table must record 16px / 1.55 body type (Grok Bot parity)")
    if tokens.get("fontSizeUi") != "14px":
        fail("table must record 14px sidebar/Teams chrome")
    logo = table.get("logo") or {}
    if logo.get("facing") != "front" or "dragon-ai-agent-logo.svg" not in str(logo.get("svg")):
        fail("table must record a front-facing SVG dragon mark")
    if logo.get("body") != "#314A73" or logo.get("eyes") != "#C41E3A":
        fail("table must record a navy body and red eyes")
    if logo.get("boxed") is not False or logo.get("stack") != "wordmark-in-front":
        fail("table must record an unboxed mark with the wordmark in front")
    sidebar = table.get("sidebar") or {}
    if sidebar.get("hideDefaultHermes") is not True:
        fail("table must hide the default Hermes sidebar bot")
    if sidebar.get("excludeHermes") is not True:
        fail("table must exclude Hermes (not hide-only)")
    if sidebar.get("headerTitle") != "Dragon AI":
        fail("table sidebar header must be Dragon AI")
    if sidebar.get("userFacingBots") != ["Personal Assistant"]:
        fail("table sidebar must list only Personal Assistant")
    voice = table.get("voice") or {}
    if voice.get("options") != ["gpt", "grok"] or voice.get("default") != "gpt":
        fail("table voice.options must be gpt + grok with GPT as the default")
    if by_from.get("return 'Hermes'") != "return ''":
        fail("table must stop presenting Hermes as a sidebar bot label")
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
function defaultBotLabel(bot) {
  if ((bot.name || '').trim().toLowerCase() === 'default' && !bot.title) {
    return 'Hermes';
  }
  return 'Personal Assistant';
}
const roster = [{name:'default', label: defaultBotLabel({name:'default'})}, {name:'personal-assistant', label:'Personal Assistant'}];
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
        if "return 'Hermes'" in branded or 'return "Hermes"' in branded:
            fail("sidebar still presents Hermes as a user-facing bot")
        if "Personal Assistant" not in branded:
            fail("sidebar lost Personal Assistant")
        if branded.count("Personal Assistant") < 1:
            fail("Personal Assistant must remain the visible sidebar bot")
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
        if 'data-dragon-ai-branding="sidebar-header"' not in html or "Dragon AI" not in html:
            fail("index.html must inject the sidebar header lockup (Dragon AI)")
        if 'data-dragon-ai-branding="teams-picker"' not in html or "Teams" not in html:
            fail("index.html must inject the in-app Teams picker")
        if 'data-dragon-ai-branding="voice-provider"' not in html:
            fail("index.html must inject the GPT | Grok voice selector")
        if "GPT" not in html or "Grok" not in html:
            fail("voice selector must list both GPT and Grok")
        if "Talk with Grok" not in html or "xai-client-secret." not in html:
            fail("index.html must inject the overlay Grok duplex client")
        icon_dest = unpacked / "resources" / "icon.ico"
        if not icon_dest.is_file() or icon_dest.read_bytes()[:4] != b"\x00\x00\x01\x00":
            fail("apply must copy the Dragon ICO to resources/icon.ico")
        icon_info = summary.get("icon") or {}
        if icon_info.get("copied") is not True:
            fail(f"overlay did not report icon copy: {icon_info}")
        font_info = summary.get("font") or {}
        if font_info.get("fontFamily") != "Syne":
            fail(f"overlay did not report Syne: {font_info}")
        mark = pack_dir / "dragon-ai-agent-logo.svg"
        png_mark = pack_dir / "dragon-ai-agent-logo.png"
        mark_txt = mark.read_text(encoding="utf-8") if mark.is_file() else ""
        if not mark.is_file() or "#314A73" not in mark_txt or "#C41E3A" not in mark_txt:
            fail("front-facing navy dragon SVG was not copied into the unpacked renderer")
        seat_icon = pack_dir / "teams" / "seo-specialist.svg"
        if not seat_icon.is_file() or "#314A73" not in seat_icon.read_text(encoding="utf-8"):
            fail("overlay must copy Teams seat icons into dragon-ai-branding/teams/")
        if not png_mark.is_file() or png_mark.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            fail("James's dragon PNG was not copied into the unpacked renderer")
        if "dragon-ai-agent-logo.png" not in css_txt and "dragon-ai-agent-logo.svg" not in css_txt:
            fail("injected CSS must pin the dragon mark")
        if "22rem" not in css_txt or "z-index: 0" not in css_txt or "z-index: 1" not in css_txt:
            fail("empty-state mark must be larger and sit behind the Dragon AI Agent title")
        if "overflow: visible" not in css_txt or "72vw" in css_txt:
            fail("empty-state mark must size to the intro pane and stay unclipped")
        if "calc(-50% + 5.9%)" not in css_txt:
            fail("empty-state mark must shift right so the dragon artwork centers on the wordmark")
        if "background-color: transparent" not in css_txt:
            fail("empty-state mark must not keep a boxed background")
        if '[data-roster-key$="::default"]' not in css_txt:
            fail("injected CSS must hide the default Hermes sidebar bot")
        if "[data-dragon-ai-sidebar-brand]" not in css_txt or "Dragon AI" not in css_txt:
            fail("injected CSS must style the sidebar header lockup")
        if "flex-wrap: wrap" not in css_txt or "min-width: max-content" not in css_txt:
            fail("injected CSS must wrap Teams below a fixed-size logo")
        if "dragon-ai-lockup-wrap:1" not in css_txt:
            fail("copied dragon-ui.css must stamp lockup wrap so live unpacked UI is not an older hash")
        if "container-type: inline-size" not in css_txt or "@container" not in css_txt:
            fail("copied dragon-ui.css must include container wrap rules")
        if "rgba(196,30,58" in css_txt.replace(" ", "") or "rgba(196, 30, 58" in css_txt:
            fail("copied dragon-ui.css must not keep a crimson lockup border")
        if "rgba(196,30,58" in html.replace(" ", "") or "rgba(196, 30, 58" in html:
            fail("index.html inject must not keep a crimson lockup border")
        if "pinWrap" not in html or "border:0" not in html.replace(" ", ""):
            fail("index.html inject must pin the lockup with border:0")
        if not (pack_dir / "sidebar-header.js").is_file() or not (pack_dir / "teams-picker.js").is_file():
            fail("prebuilt inject scripts must be copied into dragon-ai-branding")
        if "18cqi" in css_txt:
            fail("injected CSS must not shrink the sidebar logo with column width")
        if "--dragon-sidebar-control-height: 32px" not in css_txt:
            fail("injected CSS must size the sidebar logo to the Teams button")
        if "flex: 0 0 32px" not in css_txt:
            fail("injected CSS must reserve a 32px sidebar logo")
        if '[role="alert"]' not in css_txt or "-webkit-line-clamp: 2" not in css_txt:
            fail("injected CSS must contain/ellipsis center-column RPC error banners")
        if "dragon-ai-agent-logo.svg" not in html:
            fail("sidebar header script must use the transparent SVG mark")
        if "<rect" in mark_txt.lower() or "#0a0a0a" in mark_txt.lower():
            fail("copied SVG mark must not include a boxed black plate")
        if png_mark.is_file() and png_mark.read_bytes()[25] != 6:
            fail("copied PNG mark must be RGBA (no boxed plate)")
        # Idempotent second pass.
        summary2 = db.apply_to_exe(exe)
        if summary2["replacementsApplied"] != 0:
            fail(f"second pass not idempotent: {summary2}")
        html2 = (dist / "index.html").read_text(encoding="utf-8")
        if html2.count('data-dragon-ai-branding="ui-face"') != 1:
            fail("second pass duplicated the wordmark stylesheet link")
        stale_css = "/* stale unpacked hash without wrap */\n.wordmark{font-family:Syne}\n"
        css.write_text(stale_css, encoding="utf-8")
        (dist / "index.html").write_text(
            '<!doctype html><html><head><title>Dragon AI Agent</title>'
            '<link rel="stylesheet" href="./dragon-ai-branding/dragon-ui.css" data-dragon-ai-branding="ui-face" />'
            '</head><body>'
            '<div data-dragon-ai-sidebar-brand style="border:1px solid rgba(196,30,58,.45)">'
            '<img alt="" style="border:1px solid rgba(196,30,58,.45)"></div>'
            '</body></html>\n',
            encoding="utf-8",
        )
        (dist / "assets" / "index.css").write_text(
            ".wordmark{font-family:'Syne',var(--font-sans)}\n/* dragon-ai-ui-face */\n/* stale appended sheet */\n",
            encoding="utf-8",
        )
        summary3 = db.apply_to_exe(exe)
        if summary3.get("font", {}).get("copied") is not True:
            fail(f"stale unpacked refresh did not copy the pack: {summary3}")
        refreshed_css = css.read_text(encoding="utf-8")
        if "flex-wrap: wrap" not in refreshed_css or "dragon-ai-lockup-wrap:1" not in refreshed_css:
            fail("apply must overwrite an older dragon-ai-branding/dragon-ui.css with wrap rules")
        refreshed_html = (dist / "index.html").read_text(encoding="utf-8")
        if "rgba(196,30,58" in refreshed_html.replace(" ", ""):
            fail("apply must strip a live crimson lockup border from index.html")
        if "pinWrap" not in refreshed_html or 'data-dragon-ai-branding="sidebar-header"' not in refreshed_html:
            fail("apply must refresh the sidebar lockup inject on a previously branded index.html")
        refreshed_bundle = (dist / "assets" / "index.css").read_text(encoding="utf-8")
        if "flex-wrap: wrap" not in refreshed_bundle or "stale appended sheet" in refreshed_bundle:
            fail("apply must refresh the appended renderer CSS block, not skip it")
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
    if 'if ($text.Contains(\'data-dragon-ai-branding="ui-face"\')' in apply_ps and "continue }" in apply_ps:
        # Old apply skipped the entire HTML file once the link existed.
        if apply_ps.count('data-dragon-ai-branding="sidebar-header"') < 1:
            fail("Apply-DesktopBranding.ps1 must upsert sidebar inject even when index.html is already branded")
    if "sidebar-header.js" not in apply_ps or "teams-picker.js" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must ship/copy prebuilt inject scripts without Python")
    if "data-dragon-ai-sidebar-fixed" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must verify the body fixed-overlay fallback landed")
    if "findBotsTab" not in apply_ps or "data-dragon-ai-sidebar-clearance" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must verify BOTS-tab clearance landed")
    if "Teams Marketplace" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must verify the Teams Marketplace label landed")
    if "Get-DragonAIInstallUnpackedRoots" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must also land assets under DragonAIAgent app.asar.unpacked")
    if "Remove-DragonAICrimsonLockupBorder" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must strip a live crimson lockup border")
    if "return $summary" in apply_ps:
        fail("Apply-DesktopBranding.ps1 must not return after Python and skip the PowerShell pack copy")
    if "throw" not in apply_ps or "did not land" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must throw when dragon-ui.css does not land (no silent skip)")
    if '".js"' not in apply_ps and ".js" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy .js inject assets into dragon-ai-branding")
    for path in INSTALLERS:
        text = read(path)
        if "Apply-DesktopBranding.ps1" not in text or "desktop_branding.py" not in text:
            fail(f"{path.name} must install the UI overlay scripts")
        if "branding\\fonts" not in text and "branding/fonts" not in text:
            fail(f"{path.name} must copy branding/fonts for the wordmark overlay")
        if "branding\\voice" not in text and "branding/voice" not in text:
            fail(f"{path.name} must copy branding/voice for the Grok duplex overlay")
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
    if "UI UX Pro Max" not in branding and "ui-ux-pro-max" not in branding:
        fail("BRANDING.md must name the UI UX Pro Max design system")
    if "Python is optional" not in branding or "Apply-DesktopBranding.ps1" not in branding:
        fail("BRANDING.md must say PowerShell apply copies unpacked UI without Python")
    if "dragon-ai-lockup-wrap:1" not in branding:
        fail("BRANDING.md must say how to confirm the live unpacked sheet is the tip pack")
    pack = ROOT / "branding" / "fonts" / "syne"
    if not (pack / "OFL.txt").is_file() or not (pack / "syne-latin-wght-normal.woff2").is_file():
        fail("branding/fonts/syne must bundle OFL.txt and the Syne woff2 files")
    if not (pack / "syne-latin-700-normal.woff2").is_file():
        fail("branding/fonts/syne must include the 700 cut for the wordmark")
    css = read(pack / "dragon-ui.css")
    if "--color-primary: #c41e3a" not in css or "prefers-reduced-motion" not in css:
        fail("dragon-ui.css must ship applied tokens and reduced-motion")
    if "fonts.googleapis.com" in css or "family=Inter" in css:
        fail("dragon-ui.css must not load Inter")
    if "dragon-ai-agent-logo.png" not in css and "dragon-ai-agent-logo.svg" not in css:
        fail("dragon-ui.css must show the front-facing dragon mark")
    if "22rem" not in css or "z-index: 1" not in css:
        fail("dragon-ui.css must put a larger mark behind the wordmark")
    if "overflow: visible" not in css or "72vw" in css:
        fail("dragon-ui.css must not clip the mark or size it with viewport width")
    if "calc(-50% + 5.9%)" not in css:
        fail("dragon-ui.css must shift the empty-state mark so the dragon, not the PNG box, centers on the wordmark")
    if "background-color: transparent" not in css:
        fail("dragon-ui.css must not box the empty-state mark")
    if '[data-roster-key$="::default"]' not in css:
        fail("dragon-ui.css must hide the default Hermes sidebar bot")
    if "[data-dragon-ai-sidebar-brand]" not in css or "Dragon AI" not in css:
        fail("dragon-ui.css must style the sidebar header lockup (Dragon AI)")
    if "flex-wrap: wrap" not in css or "min-width: max-content" not in css:
        fail("sidebar Teams must wrap below a fixed logo (not clip, not shrink the mark)")
    if "dragon-ai-lockup-wrap:1" not in css:
        fail("packaged dragon-ui.css must stamp lockup wrap for unpacked-copy verification")
    if "container-type: inline-size" not in css or "@container" not in css:
        fail("packaged dragon-ui.css must include container wrap rules that actually get copied")
    if "rgba(196,30,58" in css.replace(" ", "") or "rgba(196, 30, 58" in css:
        fail("packaged dragon-ui.css must not include a crimson lockup border")
    sidebar_js = read(pack / "sidebar-header.js")
    teams_js = read(pack / "teams-picker.js")
    assert_sidebar_host_fallback(sidebar_js, teams_js, css)
    host_note = ROOT / "docs" / "airmaze" / "SIDEBAR_HOST.md"
    if not host_note.is_file() or "data-dragon-ai-sidebar-fixed" not in read(host_note):
        fail("docs/airmaze/SIDEBAR_HOST.md must describe the body fixed-overlay fallback")
    if "Teams Marketplace" not in read(host_note):
        fail("SIDEBAR_HOST.md must name the Teams Marketplace control")
    if "16px" not in read(host_note) or "data-dragon-ai-sidebar-clearance" not in read(host_note):
        fail("SIDEBAR_HOST.md must record 16px name parity and BOTS-tab clearance")
    for label, text in (("sidebar-header.js", sidebar_js), ("teams-picker.js", teams_js), ("dragon-ui.css", css)):
        compact = text.replace(" ", "")
        if "rgba(196,30,58" in compact:
            fail(f"{label} must not include border rgba(196,30,58)")
    if "pinWrap" not in sidebar_js or "border:0" not in sidebar_js.replace(" ", ""):
        fail("sidebar-header.js must pin the lockup with border:0")
    if "flex-wrap" not in apply_ps and "lockup-wrap" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must verify wrap rules landed in the copied sheet")
    if "18cqi" in css or "clamp(20px, 18cqi, 32px)" in css:
        fail("sidebar logo must stay a fixed 32px (do not clamp/shrink)")
    if "--dragon-sidebar-control-height: 32px" not in css:
        fail("sidebar logo height must match the 32px Teams button")
    if "flex: 0 0 32px" not in css:
        fail("sidebar logo must reserve 32px matching Teams")
    if "[data-dragon-ai-sidebar-row]" not in css:
        fail("sidebar lockup and Teams must share one header row")
    if '[role="alert"]' not in css or "text-overflow: ellipsis" not in css:
        fail("dragon-ui.css must contain/ellipsis center-column RPC error banners")
    brand_img = css.split("[data-dragon-ai-sidebar-brand] img", 1)[-1][:700]
    if "border: 0" not in brand_img and "border: none" not in brand_img:
        fail("sidebar logo must have no red border")
    if "transparent" not in brand_img:
        fail("sidebar logo must have a transparent background")
    if "height: 32px" not in brand_img or "width: 32px" not in brand_img:
        fail("sidebar logo must be 32px square matching Teams at full width")
    if "Personal Assistant" not in css:
        fail("dragon-ui.css must keep Personal Assistant as the visible sidebar bot")
    if "[data-dragon-voice-provider]" not in css:
        fail("dragon-ui.css must style the GPT | Grok voice selector")
    if "[data-dragon-grok-talk]" not in css:
        fail("dragon-ui.css must style Talk with Grok")
    voice_js = ROOT / "branding" / "voice" / "dragon-voice-selector.js"
    if not voice_js.is_file():
        fail("branding/voice/dragon-voice-selector.js must ship the duplex client")
    if "--dragon-ui-font-size-body: 16px" not in css or "--dragon-ui-line-height-body: 1.55" not in css:
        fail("dragon-ui.css must ship 16px / 1.55 Grok Bot body type")
    if "--conversation-text-base-size: 16px" not in css or "--ui-text-tertiary: #c4c4ce" not in css:
        fail("dragon-ui.css must remap Hermes 13px / 54% tertiary to 16px opaque muted")
    if "--color-muted-foreground: #c4c4ce" not in css:
        fail("dragon-ui.css muted text must be #c4c4ce for dark contrast")
    if '[data-slot="aui_assistant-message-content"]' not in css:
        fail("dragon-ui.css must size chat message content like Grok Bot")
    if _contrast_ratio("#F0F0F5", "#1C1C20") < 4.5 or _contrast_ratio("#C4C4CE", "#1C1C20") < 4.5:
        fail("overlay text tokens must clear 4.5:1 on #1C1C20")
    if "dragon-ai-agent-logo.png" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy the dragon PNG into the overlay pack")
    mark = ROOT / "branding" / "dragon-ai-agent-logo.svg"
    png = ROOT / "branding" / "dragon-ai-agent-logo.png"
    ico = ROOT / "branding" / "dragon-ai-agent-logo.ico"
    if not mark.is_file() or not png.is_file() or not ico.is_file():
        fail("branding/ must ship SVG + PNG + ICO for the dragon mark")
    svg = read(mark)
    if "side-profile" in svg or "side profile" in svg:
        fail("mark must not be a side-profile dragon")
    if "#314a73" not in svg.lower() or "#c41e3a" not in svg.lower():
        fail("mark must be a navy body with red eyes")
    if "<rect" in svg.lower() or "#0a0a0a" in svg.lower():
        fail("mark must not include a boxed black plate")
    for banned in ("#C4A574", "#E8C36A", "#F5C14A", "#B8863A"):
        if banned.lower() in svg.lower():
            fail(f"mark must not use gold/copper {banned}")
    if svg.count("<polygon") > 20:
        fail("mark must stay a few large facets, not a dense mesh")
    png_bytes = png.read_bytes()
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        fail("dragon-ai-agent-logo.png must be a PNG")
    if png_bytes[25] != 6:
        fail("dragon-ai-agent-logo.png must be RGBA so the empty-state mark has no boxed plate")
    if ico.read_bytes()[:4] != b"\x00\x00\x01\x00":
        fail("dragon-ai-agent-logo.ico must be an ICO")
    skill = ROOT / ".cursor" / "skills" / "ui-ux-pro-max" / "SKILL.md"
    if not skill.is_file():
        fail("UI UX Pro Max skill must be installed at .cursor/skills/ui-ux-pro-max")
    for paid in ("brand", "banner-design", "design"):
        if (ROOT / ".cursor" / "skills" / paid).exists():
            fail(f"paid brand/logo skill {paid} must not be vendored")
    master = ROOT / "design-system" / "dragon-ai-agent" / "MASTER.md"
    override = ROOT / "design-system" / "dragon-ai-agent" / "pages" / "desktop-client.md"
    design_note = ROOT / "docs" / "airmaze" / "DESIGN.md"
    if not master.is_file() or "AI-Native UI" not in read(master):
        fail("design-system/dragon-ai-agent/MASTER.md must exist from UI UX Pro Max")
    if not override.is_file() or "Syne" not in read(override) or "#C41E3A" not in read(override):
        fail("desktop-client override must keep Syne and crimson tokens")
    if not design_note.is_file() or "Syne" not in read(design_note):
        fail("docs/airmaze/DESIGN.md must exist and keep Syne")
    design_txt = read(design_note)
    if "front-facing" not in design_txt.lower() and "front facing" not in design_txt.lower():
        fail("DESIGN.md must record the front-facing dragon mark")
    if "navy" not in design_txt.lower() or "red eyes" not in design_txt.lower():
        fail("DESIGN.md must record the navy body and red eyes")
    if "wordmark" not in design_txt.lower() or "in front" not in design_txt.lower():
        fail("DESIGN.md must put the Dragon AI Agent title in front of the mark")
    if "no boxed" not in design_txt.lower() and "unboxed" not in design_txt.lower() and "no plate" not in design_txt.lower():
        fail("DESIGN.md must say the empty-state mark has no boxed background")
    if "Personal Assistant" not in design_txt:
        fail("DESIGN.md must say the sidebar shows Personal Assistant, not Hermes")
    if "hidden" not in design_txt.lower():
        fail("DESIGN.md must say the default Hermes sidebar bot is hidden")
    if "16px" not in design_txt or "Grok" not in design_txt:
        fail("DESIGN.md must record Grok Bot type size (16px) and contrast")
    if "#C4C4CE" not in design_txt and "#c4c4ce" not in design_txt.lower():
        fail("DESIGN.md must record the brighter muted token")
    print("OK  packaging Bot Screen / installer wiring")


def main() -> int:
    sys.path.insert(0, str(SCRIPTS))
    test_table()
    test_engine_self()
    test_fake_unpacked_tree()
    test_packaging_not_regressed()
    print("SMOKE OK: Personal Assistant only in the bot list; unboxed navy mark behind Dragon AI Agent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
