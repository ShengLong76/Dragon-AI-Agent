#!/usr/bin/env python3
"""Guardrails for the install/first-run bugs James hit on UltraDragon.

Fails the build if:
  (a) a non-current tray/window icon ships in the installer package
  (b) a team-selection prompt returns to install / first-run
  (c) Launch can complete with no result / no feedback
  (d) the window would accept the headless hermes serve page
      ("web UI disabled") instead of the desktop web UI
  (e) "Gateway ready" reappears in the installed UI
  (f) first-run no longer lands on the Air Maze Models / LLM provider step

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
FIRST_RUN_JS = ROOT / "branding" / "fonts" / "syne" / "first-run-models.js"
DESKTOP_UI = SCRIPTS / "desktop_ui.py"
COMPOSE = ROOT / "docker-compose.embedded.yml"
SERVE_UI = SCRIPTS / "start-desktop-ui.sh"
HEADLESS_BODY = (
    "Headless backend (hermes serve): web UI disabled - "
    "use `hermes dashboard` for the browser UI."
)

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


def test_desktop_web_ui_not_headless() -> None:
    html = read(UI / "index.html")
    css = read(UI / "app.css")
    js = read(UI / "app.js")
    host = read(HOST)
    launcher = read(LAUNCHER)
    compose = read(COMPOSE)
    for bad in FORBIDDEN_STATUS:
        if bad in html or bad in js or bad in css or bad in host:
            fail(f"installed UI still contains leftover status {bad!r}")
    if "blue header" in html.lower() and 'class="lockup"' in html:
        fail("product window must not ship the e65bfdf blue-header shell")
    if HEADLESS_BODY.replace("`", "") not in host and "web UI disabled" not in host:
        fail("desktop host must detect the headless web UI disabled body")
    if "isHeadlessPage" not in host:
        fail("desktop host must refuse a headless hermes serve page")
    if "8660" not in host or "desktopUIURL" not in host:
        fail("desktop host must default the window upstream to the dashboard web UI (:8660)")
    if "first-run-models" not in host:
        fail("desktop host must inject the Air Maze first-run Models step onto the web UI")
    if "/api/launch" not in host:
        fail("desktop host must expose /api/launch")
    if "refusing headless" not in host:
        fail("Launch must fail when the window URL is the headless serve page")
    if "127.0.0.1:8660:8660" not in compose:
        fail("compose must publish the dashboard web UI on 127.0.0.1:8660")
    if "hermes-airmaze-desktop-ui" not in compose or "start-desktop-ui.sh" not in compose:
        fail("compose must run hermes dashboard as hermes-airmaze-desktop-ui")
    if "dashboard --host" not in read(SERVE_UI) or "--no-open" not in read(SERVE_UI):
        fail("start-desktop-ui.sh must run hermes dashboard --no-open")
    if "web UI disabled" not in launcher or "Test-DesktopWebUIReady" not in launcher:
        fail("launcher must refuse a headless web UI disabled body at the window URL")
    if "8660" not in launcher:
        fail("launcher must wait for the dashboard web UI on 8660")
    if not FIRST_RUN_JS.is_file():
        fail("missing branding/fonts/syne/first-run-models.js")
    first_run = read(FIRST_RUN_JS)
    if "Default chat LLM" not in first_run or "Default image LLM" not in first_run:
        fail("first-run Models step must offer chat + image LLM pickers")
    if "data-airmaze-models" not in first_run:
        fail("first-run Models step must stamp data-airmaze-models")
    if "Continue" not in first_run or "Skip this step" not in first_run:
        fail("first-run Models step must have Continue and Skip this step")
    if "xAI Grok login" not in first_run:
        fail("first-run Models step must reuse the existing xAI login (no new API key)")
    if "Teams Marketplace" not in first_run or "Personal Assistant" not in first_run:
        fail("first-run copy must say Personal Assistant is installed and teams come later")
    if "Select-BotGroup" in first_run or "Choose a Team" in first_run:
        fail("first-run Models step must not include a teams picker")
    branding = read(SCRIPTS / "desktop_branding.py")
    if "inject_first_run_models_script" not in branding:
        fail("desktop branding must inject first-run-models.js onto the real web UI")
    sys.path.insert(0, str(SCRIPTS))
    import desktop_ui as dui  # noqa: E402

    if not dui.is_headless_page(HEADLESS_BODY):
        fail("desktop_ui.is_headless_page missed the live UltraDragon body")
    if dui.is_desktop_web_ui(HEADLESS_BODY):
        fail("desktop_ui accepted the headless serve page as the chat UI")
    proc = subprocess.run([sys.executable, str(DESKTOP_UI), "--self-test"], cwd=str(ROOT))
    if proc.returncode != 0:
        fail("desktop_ui.py --self-test failed (headless page must be refused)")
    exe = PACKAGED_EXE.read_bytes()
    for bad in FORBIDDEN_STATUS:
        if bad.encode() in exe:
            fail(f"packaged DragonAIAgent.exe still embeds {bad!r} (rebuild the exe)")
    if b"web UI disabled" not in exe or b"refusing headless" not in exe:
        fail("packaged exe must refuse the headless web UI disabled page; rebuild DragonAIAgent.exe")
    if b"first-run-models" not in exe:
        fail("packaged exe must inject first-run Models onto the desktop web UI; rebuild")
    print("OK  window loads the desktop web UI (headless serve page refused)")


def test_first_run_models_on_chat_screen() -> None:
    host = read(HOST)
    if "handleModels" not in host and "/dragon-ai-api/models" not in host:
        fail("desktop host must expose the Air Maze Models API used by first-run")
    if "gateway_models.py" not in host:
        fail("first-run Continue must write principal + image_gen through gateway_models.py")
    if "injectOverlay" not in host:
        fail("desktop host must inject overlay + first-run onto the loaded dashboard HTML")
    js = read(UI / "app.js")
    if "web UI disabled" not in js and "headless" not in js:
        fail("loader must fail if /dragon-ai-api/desktop-ui reports the headless page")
    print("OK  first-run Models step is tied to the loaded desktop web UI")


def main() -> int:
    test_current_tray_icon_only()
    test_no_install_team_prompt()
    test_launch_always_reports()
    test_desktop_web_ui_not_headless()
    test_first_run_models_on_chat_screen()
    print("SMOKE OK: install first-run guardrails hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
