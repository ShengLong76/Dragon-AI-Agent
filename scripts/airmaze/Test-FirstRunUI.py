#!/usr/bin/env python3
"""Contract tests for the UltraDragon-required first-run UI.

Required flow:
  1. Expanded provider screen, xAI Grok recommended, no Hermes wording
  2. grok-4.7 confirmation with Change + Begin (does not bounce to providers)
  3. Home: agents left, chat middle, Bots tab default, VM right pane

Must not ship the living-room Chat/Sessions/Files page or a disabled-web notice.
No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
UI = ROOT / "desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "app.css"
HOST = ROOT / "desktop" / "main.go"
SETUP = ROOT / "installer" / "build-exe.go"
UNINSTALL = ROOT / "scripts" / "airmaze" / "Uninstall-DragonAI.ps1"
INSTALLERS = (
    ROOT / "scripts" / "airmaze" / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def test_provider_screen() -> None:
    html = read(HTML)
    js = read(JS)
    if 'id="screen-providers"' not in html:
        fail("first screen must be the provider setup")
    if "is-expanded" not in html or 'aria-expanded="true"' not in html:
        fail("provider list must ship expanded")
    if "Let's get you set up with Dragon AI Agent" not in html:
        fail("provider heading must name Dragon AI Agent")
    if 'data-provider="xai-grok"' not in html:
        fail("xAI Grok must be a provider row")
    if "RECOMMENDED" not in html:
        fail("a recommended badge is required")
    grok = html.split('data-provider="xai-grok"', 1)[1].split("</button>", 1)[0]
    if "RECOMMENDED" not in grok:
        fail("xAI Grok must be the recommended provider")
    if "Nous Portal" in html:
        fail("Nous Portal must not appear on the provider screen")
    if "connectGrok" not in js or 'showScreen("screen-confirm")' not in js:
        fail("clicking Grok must go to the confirmation screen")
    if "Hermes" in html or "Hermes" in js:
        fail("first-run UI must not contain Hermes wording")
    print("OK  provider screen: expanded, Grok recommended, no Hermes")


def test_grok_confirm() -> None:
    html = read(HTML)
    js = read(JS)
    if 'id="screen-confirm"' not in html:
        fail("confirmation screen missing")
    if "XAI Grok OAuth (SuperGrok / Premium+) connected" not in html:
        fail("confirmation must state XAI Grok OAuth SuperGrok / Premium+ connected")
    if "grok-4.7" not in html:
        fail("default model must be grok-4.7")
    if 'id="change-model"' not in html or 'id="begin"' not in html:
        fail("confirmation must have Change and Begin")
    if "showScreen(\"screen-providers\")" in js.split("connectGrok", 1)[-1].split("beginHome", 1)[0]:
        fail("Grok connect must not return to the provider list")
    if 'id="begin"' in html and "beginHome" not in js:
        fail("Begin must open the home screen")
    print("OK  grok-4.7 confirmation with Change and Begin")


def test_home_layout() -> None:
    html = read(HTML)
    js = read(JS)
    css = read(CSS)
    if 'id="screen-home"' not in html:
        fail("home screen missing")
    if "data-dragon-ai-sidebar-logo" not in html:
        fail("home must show the Dragon logo")
    if "Teams Marketplace" not in html:
        fail("home must include Teams Marketplace")
    if 'data-rail="sessions"' not in html or 'data-rail="bots"' not in html:
        fail("home must have Sessions | Bots")
    bots = html.split('data-rail="bots"', 1)[1].split("</button>", 1)[0]
    if "is-on" not in bots and 'aria-pressed="true"' not in bots:
        fail("Bots tab must be selected by default")
    if 'id="agents"' not in html or "Personal Assistant" not in html:
        fail("left pane must list agents")
    if 'id="thread"' not in html or 'id="composer"' not in html:
        fail("middle pane must be chat")
    if 'id="vm-pane"' not in html or "Bot Screen" not in html:
        fail("right pane must be the VM / Bot Screen")
    if "Embedded Linux" in html or "Embedded Linux" in js:
        fail("home must not show an Embedded Linux header")
    if "selectRail(\"bots\")" not in js:
        fail("Begin must default the rail to Bots")
    if 'frame.src = "/vm/"' not in js:
        fail("VM pane must load Bot Screen only after the desktop service is up")
    if "fallback.hidden = false" not in js:
        fail("VM pane must keep the Bot Screen fallback when the desktop service is down")
    if "[hidden]" not in css or "display: none" not in css:
        fail("hidden confirmation controls must stay hidden until Change")
    if "border-radius: 28px" not in css:
        fail("composer must be one dark rounded pill")
    block = css.split(".composer {", 1)
    if len(block) < 2:
        fail("composer pill rule missing")
    body = block[1].split("}", 1)[0]
    if "border: 0" not in body and "border:0" not in body:
        fail("composer pill must not have a persistent red border")
    if "#c41e3a" in body or "#C41E3A" in body:
        fail("composer pill must not use a crimson border")
    logo = html.find("data-dragon-ai-sidebar-logo")
    teams = html.find("Teams Marketplace")
    sessions = html.find('data-rail="sessions"')
    bots_i = html.find('data-rail="bots"')
    if not (logo < teams < sessions < bots_i):
        fail("sidebar stack must be logo, then Teams Marketplace, then Sessions | Bots")
    print("OK  home: agents | chat | VM, Bots default, no Embedded Linux")


def test_not_livingroom() -> None:
    html = read(HTML)
    js = read(JS)
    css = read(CSS)
    blob = "\n".join((html, js, css))
    if "web UI is disabled" in blob:
        fail("must not ship a headless disabled-web page")
    if re.search(r">\s*Sessions\s*<", html) and re.search(r">\s*Files\s*<", html) and re.search(r">\s*Chat\s*<", html):
        fail("must not ship the living-room Chat / Sessions / Files page")
    if 'id="panel-models"' in html:
        fail("old Models-only living-room panel must not be the product UI")
    print("OK  not the living-room page")


def test_no_hermes_ui() -> None:
    for path in (HTML, JS, CSS):
        text = read(path)
        if re.search(r"Hermes", text):
            fail(f"{path.name} still contains Hermes wording")
        if "Nous Portal" in text:
            fail(f"{path.name} still mentions Nous Portal")
    go = read(HOST)
    if "Dragon AI Agent" not in go:
        fail("desktop host must remain Dragon AI Agent")
    print("OK  no Hermes traces in the product UI")


def test_installer_and_uninstall() -> None:
    setup = read(SETUP)
    if "go:embed embed/payload.zip" not in setup:
        fail("DragonAIAgentSetup.exe must embed payload.zip (one file)")
    if "Unzip the full" in setup:
        fail("setup exe must not tell the user to unzip a sibling payload")
    uninstall = read(UNINSTALL)
    if "Docker Desktop" not in uninstall:
        fail("uninstaller must document that Docker Desktop is left installed")
    if re.search(r"(?i)Restart-Computer|shutdown\.exe\s|/r\s", uninstall):
        fail("uninstaller must not reboot")
    if "Uninstall-Package" in uninstall or "Docker Desktop Installer" in uninstall:
        fail("uninstaller must not remove Docker Desktop")
    for path in INSTALLERS:
        text = read(path)
        if "Register-DragonAIUninstall" not in text:
            fail(f"{path.name} must register a Windows Apps uninstall entry")
        if "DisplayName" not in text or "UninstallString" not in text:
            fail(f"{path.name} must write DisplayName and UninstallString")
        if "Uninstall-DragonAI.ps1" not in text:
            fail(f"{path.name} must ship Uninstall-DragonAI.ps1")
    print("OK  single-file setup + Apps uninstall, Docker left installed, no reboot")


def main() -> int:
    test_provider_screen()
    test_grok_confirm()
    test_home_layout()
    test_not_livingroom()
    test_no_hermes_ui()
    test_installer_and_uninstall()
    print("SMOKE OK: first-run UI is Grok provider -> grok-4.7 confirm -> Bots/VM home.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
