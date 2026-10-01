#!/usr/bin/env python3
"""Validate Dragon AI Agent launch is wired to show branded UI (or a blocking error).

No secrets. Safe to run on Linux CI or a Windows checkout without Docker.
Optionally invokes pwsh/powershell -Smoke when a host is present.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "airmaze" / "start-embedded.ps1"
VBS = ROOT / "scripts" / "airmaze" / "Start-DragonAI.vbs"
FINDER = ROOT / "scripts" / "airmaze" / "Find-HermesDesktop.ps1"
WIZARD = ROOT / "scripts" / "airmaze" / "Onboard-Wizard.ps1"
COMPOSE = ROOT / "docker-compose.embedded.yml"
INSTALLERS = (
    ROOT / "scripts" / "airmaze" / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)

REQUIRED_LAUNCHER = (
    "Show-DragonDialog",
    "Find-HermesDesktopExe",
    "Start-AgentDesktopOrThrow",
    "win-unpacked",
    "hermes-airmaze-gw is not running",
    "error during connect",
    "New-LaunchStatusForm",
    "SilentHost",
    "OpenDashboard",
    "StartDocker",
    "Start-DockerIfNeeded",
    "Set-DockerTrayOnlySettings",
    "openUIOnStartupDisabled",
    "DebugConsole",
    "Invoke-NativeDocker",
    "Repair-DragonAIProductShortcuts",
    "CreateNoWindow",
    "Test-LaunchedFromShortcut",
    "Dragon AI Agent launched",
    "Smoke",
    "Set-EmbeddedDesktopRemoteConnection",
    "X-Hermes-Session-Token",
    "8650",
    "Apply-DragonAIDesktopUiBranding",
    "Exclude-DragonAIHermesBots",
    "teams_picker",
    "8653",
    "srcNames",
    "Remove-Item",
)

REQUIRED_FINDER = (
    "win-unpacked\\Hermes.exe",
    "Find-HermesDesktopExe",
    "Save-DragonAIDesktopPointer",
    "Start-HermesDesktopClient",
    "content-strategist",
    "Apply-DragonAIDesktopUiBranding",
    "Set-DragonAIMainWindowTitle",
    "SetTitleForPids",
    "Dragon AI Agent Client.lnk",
)

REQUIRED_WIZARD = (
    "Test-DictHasKey",
    "Initialize-WizardWinForms",
    "[System.Drawing.Color]",
    "OrderedDictionary",
)

REQUIRED_COMPOSE = (
    "HERMES_DASHBOARD_BASIC_AUTH_USERNAME",
    "API_SERVER_ENABLED",
    "API_SERVER_HOST",
    "API_SERVER_KEY",
    'HERMES_DASHBOARD_BASIC_AUTH_USERNAME: "dragon"',
    "HERMES_DASHBOARD_SESSION_TOKEN",
    "127.0.0.1:8650:8650",
    "hermes-airmaze-desktop",
    "start-desktop-serve.sh",
)

REQUIRED_INSTALLER = (
    "Start-DragonAI.vbs",
    "wscript.exe",
    "start the gateway and open the app",
    "win-unpacked",
)

REQUIRED_VBS = (
    "wscript",
    "start-embedded.ps1",
    "-WindowStyle Hidden",
    "-SilentHost",
    "-NonInteractive",
    "RepairProductShortcuts",
    "MsgBox",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def require_tokens(path: pathlib.Path, tokens: tuple[str, ...], label: str) -> None:
    if not path.is_file():
        fail(f"missing {path}")
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token not in text:
            fail(f"{path.name} missing required {label} token: {token}")
    print(f"OK  {label}: {path.relative_to(ROOT)}")


def check_docker_launch_design() -> None:
    design = ROOT / "docs" / "airmaze" / "DOCKER_LAUNCH.md"
    plan = ROOT / "docs" / "airmaze" / "DOCKER_LAUNCH_PLAN.md"
    for path in (design, plan):
        if not path.is_file():
            fail(f"missing {path}")
    text = design.read_text(encoding="utf-8")
    for needle in ("Start-DockerIfNeeded", "openUIOnStartupDisabled", "tray", "docker info"):
        if needle not in text:
            fail(f"DOCKER_LAUNCH.md must document {needle!r}")
    print("OK  docker launch design")


def check_launcher() -> None:
    require_tokens(LAUNCHER, REQUIRED_LAUNCHER, "launcher")
    text = LAUNCHER.read_text(encoding="utf-8")
    if "Start-AgentDesktopIfPresent" in text:
        fail("launcher still treats a missing Hermes client as optional")
    if "Open-Dashboard" in text and 'if ($OpenDashboard' not in text:
        fail("launcher still opens the dashboard without -OpenDashboard")
    if "Start-Process `$script:DashboardUrl" in text or "Start-Process $script:DashboardUrl" in text:
        fail("splash/status form still auto-opens the :9119 dashboard")
    if "if ($StartDocker)" in text and "does not auto-start Docker unless you pass -StartDocker" in text:
        fail("launcher must start Docker Desktop when the engine is down (not only -StartDocker)")
    if "Start-DockerIfNeeded" not in text:
        fail("launcher must reuse Start-DockerIfNeeded (do not invent a second starter)")
    if "if (-not (Start-DockerIfNeeded))" not in text:
        fail("normal launch must call Start-DockerIfNeeded when docker info fails")
    if "Set-DockerTrayOnlySettings" not in text or "openUIOnStartupDisabled" not in text:
        fail("launch-time Docker start must patch tray-only settings (no dashboard window)")
    if "WindowStyle Hidden" not in text and "WindowStyle Minimized" not in text:
        fail("Docker Desktop.exe must start Hidden/Minimized (tray-only)")
    if "does not auto-start Docker unless you pass -StartDocker" in text:
        fail("default launch must auto-start Docker; -StartDocker is no longer required")
    if "no auto-start unless -StartDocker" in text:
        fail("launch plan must say Docker starts in the tray when the engine is down")
    if "Starting Docker Desktop (system tray)" not in text:
        fail("Start-DockerIfNeeded must tell James Docker is starting in the tray")
    if "Start-Process `$script:DashboardUrl" in text:
        fail("splash/status form still auto-opens the :9119 dashboard")
    if "Show-DragonDialog" not in text:
        fail("launcher throws without a user-visible dialog helper")
    if '$ErrorActionPreference = "Continue"' not in text:
        fail("launcher missing Continue around Docker CLI (stderr progress must not terminate)")
    if "$output = & docker compose" in text or "& docker inspect" in text or "& docker info" in text:
        fail("launcher still calls docker compose/inspect/info without Invoke-NativeDocker")


def check_shortcuts() -> None:
    for path in INSTALLERS:
        require_tokens(path, REQUIRED_INSTALLER, "shortcut")
        text = path.read_text(encoding="utf-8")
        if "$sc1.TargetPath = $targetPs" in text:
            fail(f"{path.name} still points Dragon AI Agent.lnk at powershell.exe")
        if "Start-DragonAI.vbs" not in text:
            fail(f"{path.name} missing windowless Start-DragonAI.vbs host")
        if "openUIOnStartupDisabled" not in text or "Set-DockerTrayOnlySettings" not in text:
            fail(f"{path.name} must keep tray-only Docker settings")


def check_vbs() -> None:
    require_tokens(VBS, REQUIRED_VBS, "vbs")
    text = VBS.read_text(encoding="utf-8", errors="replace")
    if "cscript" in text.lower() and "not cscript" not in text.lower():
        fail("VBS host must use wscript (cscript flashes a console)")
    if "sh.Run cmd, 0, False" not in text:
        fail("VBS host must Run powershell hidden (window style 0)")
    if "CreateShortcut" not in text:
        fail("VBS host must rewrite product shortcuts to wscript (old powershell .lnk flashes)")
    if " -StartDocker" in text.replace("Do not pass -StartDocker", "").replace("fail-closed", ""):
        fail("VBS product host must not pass -StartDocker; default launch starts Docker itself")
    if "fail-closed" in text.lower():
        fail("VBS comment still describes fail-closed Docker; launch now starts Docker in the tray")


def check_compose_auth() -> None:
    require_tokens(COMPOSE, REQUIRED_COMPOSE, "compose")
    text = COMPOSE.read_text(encoding="utf-8")
    if "HERMES_DASHBOARD_BASIC_AUTH_USER:" in text and "USERNAME" not in text:
        fail("compose still uses BASIC_AUTH_USER (image wants USERNAME)")
    if 'HERMES_DASHBOARD_BASIC_AUTH_USERNAME: "airmaze"' in text:
        fail("dashboard login username is still airmaze (customer-facing)")


def check_wizard() -> None:
    require_tokens(WIZARD, REQUIRED_WIZARD, "wizard")
    text = WIZARD.read_text(encoding="utf-8")
    if "$steps.ContainsKey(" in text or "$ns.ContainsKey(" in text:
        fail("wizard still calls ContainsKey on OrderedDictionary/IDictionary")
    if "$script:BrandBack = [System.Drawing.Color]::FromArgb" in text.split("function Initialize-WizardWinForms")[0]:
        fail("wizard still initializes Drawing.Color before Add-Type System.Drawing")


def run_host_smoke() -> None:
    host = shutil.which("pwsh") or shutil.which("powershell")
    if not host:
        print("SKIP host -Smoke (pwsh/powershell not on PATH)")
        return
    cmd = [host, "-NoProfile", "-File", str(LAUNCHER), "-Smoke"]
    print("RUN", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        fail(f"host -Smoke exited {proc.returncode}")
    if "SMOKE OK" not in proc.stdout:
        fail("host -Smoke did not print SMOKE OK")
    print("OK  host -Smoke")


def main() -> int:
    require_tokens(FINDER, REQUIRED_FINDER, "finder")
    check_docker_launch_design()
    check_vbs()
    check_launcher()
    check_shortcuts()
    check_compose_auth()
    check_wizard()
    branding = ROOT / "docs" / "airmaze" / "BRANDING.md"
    if not branding.is_file():
        fail("missing docs/airmaze/BRANDING.md")
    btxt = branding.read_text(encoding="utf-8")
    if "rebuilt Electron" not in btxt:
        fail("BRANDING.md must say what still needs a rebuilt Electron binary")
    print(f"OK  branding: {branding.relative_to(ROOT)}")
    adapter = ROOT / "scripts" / "airmaze" / "Test-DesktopServeAdapter.py"
    if adapter.is_file():
        proc = subprocess.run([sys.executable, str(adapter)], cwd=str(ROOT))
        if proc.returncode != 0:
            fail("Test-DesktopServeAdapter.py failed")
    branding_test = ROOT / "scripts" / "airmaze" / "Test-DesktopBranding.py"
    if branding_test.is_file():
        proc = subprocess.run([sys.executable, str(branding_test)], cwd=str(ROOT))
        if proc.returncode != 0:
            fail("Test-DesktopBranding.py failed")
    bot_groups_test = ROOT / "scripts" / "airmaze" / "Test-BotGroups.py"
    if bot_groups_test.is_file():
        proc = subprocess.run([sys.executable, str(bot_groups_test)], cwd=str(ROOT))
        if proc.returncode != 0:
            fail("Test-BotGroups.py failed")
    exclude_test = ROOT / "scripts" / "airmaze" / "Test-ExcludeHermesBot.py"
    if exclude_test.is_file():
        proc = subprocess.run([sys.executable, str(exclude_test)], cwd=str(ROOT))
        if proc.returncode != 0:
            fail("Test-ExcludeHermesBot.py failed")
    teams_test = ROOT / "scripts" / "airmaze" / "Test-TeamsPicker.py"
    if teams_test.is_file():
        proc = subprocess.run([sys.executable, str(teams_test)], cwd=str(ROOT))
        if proc.returncode != 0:
            fail("Test-TeamsPicker.py failed")
    run_host_smoke()
    print("SMOKE OK: opening Dragon AI Agent is wired to branded UI or a blocking error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
