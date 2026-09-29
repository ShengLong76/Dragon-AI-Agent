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
    "Dragon AI Agent launched",
    "Smoke",
)

REQUIRED_FINDER = (
    "win-unpacked\\Hermes.exe",
    "Find-HermesDesktopExe",
    "Save-DragonAIDesktopPointer",
    "Start-HermesDesktopClient",
    "Set-DragonAIMainWindowTitle",
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
)

REQUIRED_INSTALLER = (
    '-STA -NoProfile -ExecutionPolicy Bypass -File `"$startScript`"',
    "start the gateway and open the app",
    "win-unpacked",
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


def check_launcher() -> None:
    require_tokens(LAUNCHER, REQUIRED_LAUNCHER, "launcher")
    text = LAUNCHER.read_text(encoding="utf-8")
    if "Start-AgentDesktopIfPresent" in text:
        fail("launcher still treats a missing Hermes client as optional")
    if "Show-DragonDialog" not in text:
        fail("launcher throws without a user-visible dialog helper")


def check_shortcuts() -> None:
    for path in INSTALLERS:
        require_tokens(path, REQUIRED_INSTALLER, "shortcut")
        text = path.read_text(encoding="utf-8")
        if "-WindowStyle Hidden" in text and path.name == "install.ps1":
            if "Do not use -WindowStyle Hidden" not in text:
                fail(f"{path.name} hides the host window without a documented fallback")


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
    run_host_smoke()
    print("SMOKE OK: opening Dragon AI Agent is wired to branded UI or a blocking error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
