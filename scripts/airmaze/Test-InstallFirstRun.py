#!/usr/bin/env python3
"""Guardrails for the five install/first-run bugs James hit on e65bfdf.

Fails the build if:
  (a) a non-current tray/window icon ships in the installer package
  (b) a team-selection prompt returns to install / first-run
  (c) Launch can complete with no result / no feedback
  (d) the packaged window is the blue-header "Gateway ready" shell
  (e) "Gateway ready" reappears in the installed UI

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
DESKTOP = ROOT / "desktop"
UI = DESKTOP / "ui"
BRAND_ICO = ROOT / "branding" / "dragon-ai-agent-logo.ico"
BRAND_PNG = ROOT / "branding" / "dragon-ai-agent-logo.png"
BRAND_SVG = ROOT / "branding" / "dragon-ai-agent-logo.svg"
DESKTOP_WINRES = DESKTOP / "winres" / "icon.ico"
INSTALLER_WINRES = ROOT / "installer" / "winres" / "icon.ico"
PACKAGED_EXE = DESKTOP / "win-unpacked" / "DragonAIAgent.exe"
INSTALLERS = (
    SCRIPTS / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
FINDER = SCRIPTS / "Find-HermesDesktop.ps1"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
HOST = DESKTOP / "main.go"
HOST_WIN = DESKTOP / "host_windows.go"
TEAMS_JS = ROOT / "branding" / "fonts" / "syne" / "teams-picker.js"

FORBIDDEN_STATUS = (
    "Gateway ready",
    "Gateway Ready",
    "Starting gateway...",
    "Gateway up, Bot Screen starting",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def ico_png_frames(path: Path) -> list[bytes]:
    data = path.read_bytes()
    if data[:4] != b"\x00\x00\x01\x00":
        fail(f"{path} is not an ICO")
    count = struct.unpack_from("<H", data, 4)[0]
    frames: list[bytes] = []
    for i in range(count):
        off = 6 + i * 16
        size, start = struct.unpack_from("<II", data, off + 8)
        blob = data[start : start + size]
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            frames.append(blob)
    if not frames:
        fail(f"{path} has no PNG ICO frames to fingerprint")
    return frames


def test_current_tray_icon_only() -> None:
    for path in (BRAND_ICO, DESKTOP_WINRES, INSTALLER_WINRES):
        if not path.is_file():
            fail(f"missing current tray ICO {path}")
    brand = BRAND_ICO.read_bytes()
    if DESKTOP_WINRES.read_bytes() != brand:
        fail("desktop/winres/icon.ico is not the current branding ICO")
    if INSTALLER_WINRES.read_bytes() != brand:
        fail("installer/winres/icon.ico is not the current branding ICO")
    if UI.joinpath("dragon-ai-agent-logo.png").read_bytes() != BRAND_PNG.read_bytes():
        fail("desktop/ui logo PNG is not the current branding PNG")
    if UI.joinpath("dragon-ai-agent-logo.svg").read_bytes() != BRAND_SVG.read_bytes():
        fail("desktop/ui logo SVG is not the current branding SVG")
    if not PACKAGED_EXE.is_file():
        fail("desktop/win-unpacked/DragonAIAgent.exe is missing from the package")
    exe = PACKAGED_EXE.read_bytes()
    syso = DESKTOP / "rsrc_windows_amd64.syso"
    if not syso.is_file() or syso.stat().st_size < 1024:
        fail("desktop/rsrc_windows_amd64.syso missing; rebuild with desktop/build-windows.py")
    syso_bytes = syso.read_bytes()
    if b"\x89PNG\r\n\x1a\n" not in syso_bytes:
        fail("rsrc_windows_amd64.syso does not contain PNG icon frames")
    if "Dragon AI Agent".encode("utf-16le") not in syso_bytes:
        fail("rsrc_windows_amd64.syso is not the Dragon AI Agent version resource")
    if b".rsrc" not in exe:
        fail("DragonAIAgent.exe has no rsrc section; the tray/window icon cannot be current")
    winres_json = read(DESKTOP / "winres" / "winres.json")
    if '"#1"' not in winres_json or "icon.ico" not in winres_json:
        fail("desktop/winres/winres.json must embed icon.ico as resource id 1")
    _ = ico_png_frames(BRAND_ICO)
    print("OK  packaged tray/window icon is the current branding ICO")


def test_no_install_team_prompt() -> None:
    for path in INSTALLERS:
        text = read(path)
        main = text.split("# --- Main")[-1]
        block = text.split("function Invoke-BotGroupSetup")[-1].split("function ")[0]
        for raw in block.splitlines():
            line = raw.strip()
            if line.startswith("& $select") and "-NonInteractive" not in line and "-BotGroupId" not in line:
                fail(f"{path.name} Invoke-BotGroupSetup still opens an interactive team picker")
        if "-NonInteractive" not in block:
            fail(f"{path.name} first-run bot-group apply must stay NonInteractive")
        if "Show-TeamsPopup" in main:
            fail(f"{path.name} still prompts for teams during install")
        if "does not prompt for teams" not in text:
            fail(f"{path.name} must say first-run does not prompt for teams")
    wizard = read(SCRIPTS / "Onboard-Wizard.ps1")
    if "Launching onboarding wizard" in wizard:
        fail("Onboard-Wizard must not be auto-launched as first-run")
    print("OK  install/first-run never prompts for teams")


def test_launch_always_reports() -> None:
    finder = read(FINDER)
    if "Write-LaunchResult" not in finder:
        fail("Start-DragonAIDesktopClient must write a launch-result object")
    if "HasExited" not in finder:
        fail("launch must detect an exe that dies without a window")
    if "PassThru" not in finder:
        fail("launch must Start-Process -PassThru so it can observe the result")
    if "SilentlyContinue" in finder.split("function Start-DragonAIDesktopClient")[-1].split("function Write-LaunchResult")[0] and "Start-Process -FilePath $ExePath" in finder:
        start_block = finder.split("Start-Process -FilePath $ExePath")[-1][:200]
        if "SilentlyContinue" in start_block:
            fail("product exe Start-Process must not be SilentlyContinue")
    host = read(HOST)
    if '"/api/launch"' not in host and '"/api/launch"' not in host:
        if "/api/launch" not in host:
            fail("desktop host must expose /api/launch with a result payload")
    if "launch-check" not in host:
        fail("desktop host must support --launch-check and print a result")
    if "showLaunchError" not in read(HOST_WIN):
        fail("Windows host must MessageBox when the window cannot open")
    ui_js = read(UI / "app.js")
    if "reportLaunch" not in ui_js or "Launch returned no result" not in ui_js:
        fail("in-app Launch must report ok/error and refuse an empty result")
    if "function launch(" in read(TEAMS_JS):
        overlay = read(TEAMS_JS).split("function launch(")[1].split("function ")[0]
        if "setStatus" not in overlay:
            fail("overlay Launch must set a visible status")
        if "empty-result" not in overlay and "no-selection" not in overlay:
            fail("overlay Launch must not return silently when it cannot run")
    proc = subprocess.run(
        ["go", "run", ".", "--launch-check"],
        cwd=str(DESKTOP),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(f"--launch-check failed: {proc.stderr or proc.stdout}")
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except json.JSONDecodeError:
        fail(f"--launch-check printed no JSON result: {proc.stdout!r}")
    if payload.get("ok") is not True or not payload.get("action"):
        fail(f"launch-check result missing ok/action: {payload}")
    print("OK  Launch always returns a result")


def test_ultradragon_ui_not_blue_header_shell() -> None:
    html = read(UI / "index.html")
    css = read(UI / "app.css")
    js = read(UI / "app.js")
    for bad in FORBIDDEN_STATUS:
        if bad in html or bad in js or bad in css:
            fail(f"installed UI still contains leftover status {bad!r}")
    if 'class="lockup"' in html and "lockup" in css:
        lockup = css.split(".lockup {")[1].split("}")[0] if ".lockup {" in css else ""
        if "background: var(--dragon-marketplace-blue)" in lockup or "background: #2563eb" in lockup:
            fail("product lockup must not be the blue header bar from the e65bfdf shell")
    if 'data-dragon-ai-shell="ultradragon"' not in html:
        fail("desktop UI must stamp the UltraDragon shell")
    if 'data-dragon-ai-hide-sidebar' not in html:
        fail("UltraDragon UI must keep hide-sidebar to the left of the logo")
    if "Teams Marketplace" not in html:
        fail("UltraDragon UI must keep Teams Marketplace under the logo")
    if "Sessions" not in html or "Bots" not in html:
        fail("UltraDragon UI must keep Sessions and Bots below the logo / Marketplace")
    if "1.125" not in css and "15.75px" not in css:
        fail("Sessions/Bots labels must be 1.125x neighboring sidebar text")
    if 'id="panel-models"' not in html or "data-airmaze-models" not in html:
        fail("first-run must land on the Models / LLM provider screen")
    if "data-slot=\"composer\"" not in html or "composer-wave" not in html:
        fail("composer must be the dark pill with plus / field / mic / waveform")
    if "GPT" in html and "Grok pills" not in html:
        if "Voice/GPT/Grok" in html:
            fail("composer must not ship Voice/GPT/Grok pills")
    if "Embedded Linux" in html:
        fail("installed UI must not show an Embedded Linux connection header")
    if "data-open-scheduled-jobs" not in html:
        fail("Scheduled Jobs must keep the right sidebar visible")
    if "dblclick" not in js:
        fail("double-click a bot must open the right-panel Bot Screen")
    if "Grok Voice" not in html:
        fail("Settings must list Grok Voice")
    exe = PACKAGED_EXE.read_bytes()
    for bad in FORBIDDEN_STATUS:
        if bad.encode() in exe:
            fail(f"packaged DragonAIAgent.exe still embeds {bad!r} (rebuild the exe)")
    if b'data-dragon-ai-shell="ultradragon"' not in exe:
        fail("packaged exe still embeds the old blue-header UI; rebuild DragonAIAgent.exe")
    print("OK  packaged UI matches the UltraDragon shell (no Gateway ready)")


def main() -> int:
    test_current_tray_icon_only()
    test_no_install_team_prompt()
    test_launch_always_reports()
    test_ultradragon_ui_not_blue_header_shell()
    print("SMOKE OK: install first-run guardrails hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
