#!/usr/bin/env python3
"""Dragon AI Agent must register in Settings > Apps and uninstall from there.

Per-user HKCU Uninstall key (install is under LocalAppData). Uninstall
removes the app folder, desktop shortcut, Start Menu shortcut/folder,
and that registry entry. Handoff stays one installer exe.

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
UNINSTALL = SCRIPTS / "uninstall.ps1"
INSTALLERS = (
    SCRIPTS / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
PACK = ROOT / "installer" / "pack.py"
PACKAGING = ROOT / "PACKAGING.md"

HKCU_KEY = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DragonAIAgent"
HKLM_KEY = r"HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DragonAIAgent"

REQUIRED_INSTALLER = (
    "Register-DragonAIAppsEntry",
    HKCU_KEY,
    "DisplayName",
    "UninstallString",
    "QuietUninstallString",
    "InstallLocation",
    "uninstall.ps1",
    "Copied uninstall.ps1",
)

REQUIRED_UNINSTALL = (
    HKCU_KEY,
    r"Dragon AI Agent.lnk",
    r"Start Menu\Programs\Dragon AI Agent",
    "LOCALAPPDATA",
    "DragonAIAgent",
    "Remove-Item",
    "docker compose",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def test_installers_register_hkcu() -> None:
    for path in INSTALLERS:
        text = read(path)
        for token in REQUIRED_INSTALLER:
            if token not in text:
                fail(f"{path.name} missing {token!r}")
        if HKLM_KEY in text:
            fail(f"{path.name} must not write an HKLM Uninstall key (per-user install)")
        if "Register-DragonAIAppsEntry" not in text.split("Install-Shortcuts", 1)[-1]:
            fail(f"{path.name} must call Register-DragonAIAppsEntry after shortcuts")
        if "UninstallString" not in text or "uninstall.ps1" not in text:
            fail(f"{path.name} UninstallString must point at uninstall.ps1")
    print("OK  installers write a per-user HKCU Apps entry")


def test_uninstaller_removes_app() -> None:
    text = read(UNINSTALL)
    for token in REQUIRED_UNINSTALL:
        if token not in text:
            fail(f"uninstall.ps1 missing {token!r}")
    if HKLM_KEY in text:
        fail("uninstall.ps1 must not touch HKLM")
    if "Docker Desktop" in text and "uninstall" in text.lower():
        # compose down is fine; uninstalling Docker Desktop is not
        if "Docker Desktop Installer" in text or "Uninstall-Package" in text:
            fail("uninstall.ps1 must not uninstall Docker Desktop")
    for needle in (
        "Get-DesktopShortcutPath",
        "Get-StartMenuShortcutPath",
        "Remove-Item -LiteralPath $InstallRoot",
        "Remove-Item -LiteralPath $UninstallRegPath",
        "Remove-Item -LiteralPath $StartMenuDir",
    ):
        if needle not in text:
            fail(f"uninstall.ps1 must {needle}")
    if "SelfTest" not in text:
        fail("uninstall.ps1 must support -SelfTest for contract checks")
    print("OK  uninstaller removes app, shortcuts, and HKCU Apps entry")


def test_payload_includes_uninstaller() -> None:
    pack = read(PACK)
    if "uninstall.ps1" not in pack:
        fail("pack.py must stage uninstall.ps1 in the payload")
    packaging = read(PACKAGING)
    if "HKCU" not in packaging and "Apps" not in packaging:
        fail("PACKAGING.md must document the per-user Apps / uninstall entry")
    print("OK  payload and docs include uninstall")


def main() -> int:
    test_installers_register_hkcu()
    test_uninstaller_removes_app()
    test_payload_includes_uninstaller()
    print("SMOKE OK: Setup registers Dragon AI Agent in Apps; Uninstall removes it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
