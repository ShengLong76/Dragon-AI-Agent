#!/usr/bin/env python3
"""Contract: Dragon AI Agent Setup owns Docker Desktop on a clean Windows PC.

No secrets. No live Docker. Safe on Linux CI.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
INSTALLERS = (
    SCRIPTS / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)
LAUNCHER = SCRIPTS / "start-embedded.ps1"
DESIGN = ROOT / "docs" / "airmaze" / "DOCKER_INSTALL.md"
LAUNCH_DESIGN = ROOT / "docs" / "airmaze" / "DOCKER_LAUNCH.md"
PACKAGING = ROOT / "PACKAGING.md"
README = ROOT / "README.md"
STAGE = ROOT / "installer" / "stage-docker-desktop.py"
VENDOR_README = ROOT / "vendor" / "docker" / "README.md"

REQUIRED_INSTALLER = (
    "Find-BundledDockerInstaller",
    "Resolve-DockerInstaller",
    "Save-DockerInstallerFromUrl",
    "Invoke-DockerDesktopQuietInstall",
    "Ensure-DockerDesktop",
    "Test-DockerDesktopComplete",
    "Test-DockerCliPresent",
    "vendor\\docker",
    "Docker Desktop Installer.exe",
    "install",
    "--quiet",
    "--accept-license",
    "3010",
    "RunAs",
    "half-installed",
    "Setup owns this step",
    "Setup-owned",
    "Programs\\DockerDesktop",
    "Fix-DockerPath",
    "Set-DockerTrayOnlySettings",
    "openUIOnStartupDisabled",
    "Start-DockerHeadless",
    "Remove-DeprecatedProductShortcuts",
    "Dragon AI Agent.lnk",
    "Dragon AI Agent Bot Groups.lnk",
    "Dragon AI Agent Dashboard.lnk",
    "Dragon AI Agent Profiles.lnk",
    "Install-DragonAIPrivateDesktop",
    "HERMES_DESKTOP_USER_DATA_DIR",
    "desktop\\win-unpacked",
    "in-app Models UI",
)

RETIRED_START_MENU_LINKS = (
    "Dragon AI Agent Setup.lnk",
    "Dragon AI Agent Bot Groups.lnk",
    "Dragon AI Agent Dashboard.lnk",
    "Dragon AI Agent Profiles.lnk",
)

FORBIDDEN_INSTALLER = (
    "https://www.docker.com/products/docker-desktop/",
    "Opening Docker Desktop download page for manual install",
    "ACTION REQUIRED: Install Docker Desktop, then re-run",
    "Re-run after installing Docker.",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def require_tokens(path: pathlib.Path, tokens: tuple[str, ...], label: str) -> None:
    text = read(path)
    for token in tokens:
        if token not in text:
            fail(f"{path.name} missing {label} token: {token}")
    print(f"OK  {label}: {path.relative_to(ROOT)}")


def test_design() -> None:
    text = read(DESIGN)
    for needle in (
        "clean Windows PC",
        "vendor/docker",
        "half-installed",
        "install --quiet --accept-license",
        "3010",
        "docker.com",
        "Start Menu",
        "in-app",
        "Hermes",
        "DOCKER_LAUNCH",
    ):
        if needle not in text:
            fail(f"DOCKER_INSTALL.md must document {needle!r}")
    if "Install Docker Desktop, then re-run" in text:
        fail("DOCKER_INSTALL.md must not tell the user to install Docker first")
    print("OK  docker install design")


def test_package_slot() -> None:
    if not VENDOR_README.is_file():
        fail("missing vendor/docker/README.md")
    vendor = read(VENDOR_README)
    if "Docker Desktop Installer.exe" not in vendor:
        fail("vendor/docker/README.md must name Docker Desktop Installer.exe")
    if "stage-docker-desktop.py" not in vendor:
        fail("vendor/docker/README.md must name the stage script")
    stage = read(STAGE)
    if "desktop.docker.com/win/main/amd64" not in stage:
        fail("stage-docker-desktop.py must use the official Docker Desktop URL")
    if "vendor" not in stage or "Docker Desktop Installer.exe" not in stage:
        fail("stage-docker-desktop.py must write vendor/docker/Docker Desktop Installer.exe")
    packaging = read(PACKAGING)
    if "vendor/docker" not in packaging:
        fail("PACKAGING.md must list vendor/docker in the Windows zip")
    if "stage-docker-desktop.py" not in packaging:
        fail("PACKAGING.md must document staging the Docker installer")
    readme = read(README)
    if "Setup-owned" not in readme and "Setup owns" not in readme:
        fail("README must say Setup owns Docker Desktop")
    print("OK  package slot + stage script")


def test_installers_own_docker() -> None:
    for path in INSTALLERS:
        require_tokens(path, REQUIRED_INSTALLER, "docker-install")
        text = read(path)
        for bad in FORBIDDEN_INSTALLER:
            if bad in text:
                fail(f"{path.name} still hands Docker to the user ({bad!r})")
        if "ArgumentList = $argList" not in text and 'ArgumentList = @("install"' not in text:
            fail(f"{path.name} must pass install/--quiet/--accept-license as separate arguments")
        if "if (Get-DockerDesktopExe)" in text.split("function Ensure-DockerDesktop")[0]:
            pass
        ensure = text.split("function Ensure-DockerDesktop", 1)[-1]
        if "if (Get-DockerDesktopExe)" in ensure.split("function ", 1)[0] and "Test-DockerDesktopComplete" not in ensure.split("function ", 1)[0]:
            fail(f"{path.name} still treats exe-only as installed (skips half-installed repair)")
        if "Ensure-DockerDesktop -PayloadRoot $root" not in text:
            fail(f"{path.name} must pass payload root so the packaged installer is found")
        if "Fix-DockerPath" not in text.split("function Test-DockerEngine", 1)[-1].split("function ", 1)[0]:
            fail(f"{path.name} Test-DockerEngine must Fix-DockerPath before docker info")
        if "Launching onboarding wizard" in text or "& $wizard @wizArgs" in text:
            fail(f"{path.name} still auto-launches WinForms Onboard-Wizard")
        if "CreateShortcut($sc3Path)" in text or "CreateShortcut($scDashPath)" in text:
            fail(f"{path.name} still CreateShortcut Bot Groups or Dashboard .lnk")
        for name in RETIRED_START_MENU_LINKS:
            idx = text.find(name)
            while idx >= 0:
                window = text[max(0, idx - 80) : idx + 80]
                if "CreateShortcut" in window:
                    fail(f"{path.name} still CreateShortcut {name}")
                idx = text.find(name, idx + 1)
        if "Refuse *outside DragonAIAgent*" not in text and "desktop\\win-unpacked" not in text:
            fail(f"{path.name} must keep the private Dragon desktop path")
    print("OK  both installers own Docker")


def test_launch_does_not_install() -> None:
    text = read(LAUNCHER)
    if "desktop.docker.com" in text or "Docker%20Desktop%20Installer" in text:
        fail("start-embedded.ps1 must not download the Docker Desktop installer")
    if "www.docker.com/products/docker-desktop" in text:
        fail("start-embedded.ps1 must not open the Docker download page")
    if "Start-DockerIfNeeded" not in text:
        fail("launcher must still start an already-installed engine")
    if "Programs\\DockerDesktop" not in text:
        fail("launcher must find the per-user Docker Desktop path Setup may install")
    launch_design = read(LAUNCH_DESIGN)
    if "DOCKER_INSTALL" not in launch_design and "Installing Docker from the product shortcut" not in launch_design:
        fail("DOCKER_LAUNCH.md must keep install out of the product shortcut")
    print("OK  launch still does not install Docker")


def main() -> int:
    test_design()
    test_package_slot()
    test_installers_own_docker()
    test_launch_does_not_install()
    print("SMOKE OK: Setup owns Docker Desktop; launch only starts it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
