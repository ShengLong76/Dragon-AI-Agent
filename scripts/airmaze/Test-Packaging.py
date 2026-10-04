#!/usr/bin/env python3
"""Windows handoff is one installer exe, not a zip with a loose desktop exe.

No secrets. Safe on Linux CI. Live pack runs when Go is on PATH.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACK = ROOT / "installer" / "pack.py"
SETUP = ROOT / "installer" / "build-exe.go"
PACKAGING = ROOT / "PACKAGING.md"
README = ROOT / "README.md"
INSTALL_PS1 = ROOT / "scripts" / "airmaze" / "install.ps1"
LAUNCHER = ROOT / "scripts" / "airmaze" / "start-embedded.ps1"
SETUP_PS1 = ROOT / "installer" / "DragonAIAgentSetup.ps1"
TEST_DOCKER = ROOT / "scripts" / "airmaze" / "Test-DockerInstall.py"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def test_packager_source() -> None:
    pack = read(PACK)
    setup = read(SETUP)
    for token in (
        "DragonAIAgentSetup.exe",
        "append",
        "one installer exe",
        "loose DragonAIAgent.exe",
        "--out",
    ):
        if token not in pack:
            fail(f"pack.py missing {token!r}")
    for token in (
        "zip.OpenReader",
        "extractSelfPayload",
        "Re-download DragonAIAgentSetup.exe",
        'filepath.Join(exeDir, "payload", "install.ps1")',
    ):
        if token not in setup:
            fail(f"build-exe.go missing {token!r}")
    if "Unzip the full Dragon-AI-Agent-v0.1.0-windows.zip" in setup:
        fail("build-exe.go still tells the user to unzip a multi-file zip")
    print("OK  packager source is a single-exe handoff")


def test_docs_and_user_copy() -> None:
    packaging = read(PACKAGING)
    readme = read(README)
    for token in (
        "DragonAIAgentSetup.exe",
        "one installer exe",
        "installer/pack.py",
        "vendor/docker",
        "stage-docker-desktop.py",
        "DragonAIAgent.exe",
        "desktop/win-unpacked",
        "does not search",
    ):
        if token not in packaging:
            fail(f"PACKAGING.md missing {token!r}")
    if "Unzip `Dragon-AI-Agent-v0.1.0-windows.zip`" in readme:
        fail("README still tells James to unzip a folder with two exes")
    if "DragonAIAgentSetup.exe" not in readme:
        fail("README must name DragonAIAgentSetup.exe")
    for path in (INSTALL_PS1, SETUP_PS1, LAUNCHER):
        text = read(path)
        if "Re-download Dragon-AI-Agent-v0.1.0-windows.zip and run DragonAIAgentSetup.exe" in text:
            fail(f"{path.name} still points James at the zip")
        if "DragonAIAgentSetup.exe" not in text:
            fail(f"{path.name} must still name DragonAIAgentSetup.exe")
    docker_test = read(TEST_DOCKER)
    if "Windows zip" in docker_test and "single installer exe" not in docker_test:
        fail("Test-DockerInstall.py must accept the single-exe package slot")
    print("OK  docs and user copy describe one installer exe")


def test_live_pack() -> None:
    if shutil.which("go") is None:
        print("SKIP live pack (go not on PATH)")
        return
    desktop = ROOT / "desktop" / "win-unpacked" / "DragonAIAgent.exe"
    skip = ["--skip-desktop-build"] if desktop.is_file() else []
    with tempfile.TemporaryDirectory(prefix="dragon-pack-test-") as tmp:
        dest_dir = pathlib.Path(tmp) / "handoff"
        dest_dir.mkdir()
        decoy = dest_dir / "DragonAIAgent.exe"
        decoy.write_bytes(b"MZ-decoy")
        proc = subprocess.run(
            [sys.executable, str(PACK), "--out", str(dest_dir), *skip],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            fail("pack.py must refuse a handoff folder that already has another exe")
        decoy.unlink()
        proc = subprocess.run(
            [sys.executable, str(PACK), "--out", str(dest_dir), *skip],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            fail(f"pack.py failed:\n{proc.stdout}\n{proc.stderr}")
        exes = [p for p in dest_dir.iterdir() if p.suffix.lower() == ".exe"]
        if len(exes) != 1:
            fail(f"handoff must be exactly one exe, found {[p.name for p in dest_dir.iterdir()]}")
        setup = dest_dir / "DragonAIAgentSetup.exe"
        if setup not in exes:
            fail("handoff exe must be named DragonAIAgentSetup.exe")
        if setup.read_bytes()[:2] != b"MZ":
            fail("DragonAIAgentSetup.exe missing MZ header")
        with zipfile.ZipFile(setup) as zf:
            names = zf.namelist()
        if "install.ps1" not in names:
            fail("embedded payload missing install.ps1")
        if "uninstall.ps1" not in names:
            fail("embedded payload missing uninstall.ps1")
        if "scripts/airmaze/uninstall.ps1" not in names:
            fail("embedded payload missing scripts/airmaze/uninstall.ps1")
        if "desktop/win-unpacked/DragonAIAgent.exe" not in names:
            fail("embedded payload missing desktop/win-unpacked/DragonAIAgent.exe")
        if "docker-compose.embedded.yml" not in names:
            fail("embedded payload missing docker-compose.embedded.yml")
        loose = dest_dir / "DragonAIAgent.exe"
        if loose.exists():
            fail("pack.py left a loose DragonAIAgent.exe beside Setup")
    print("OK  live pack writes one self-extracting installer exe")


def main() -> int:
    test_packager_source()
    test_docs_and_user_copy()
    test_live_pack()
    print("SMOKE OK: Windows handoff is one DragonAIAgentSetup.exe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
