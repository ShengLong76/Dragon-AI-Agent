#!/usr/bin/env python3
"""Build the Dragon AI Agent Windows handoff: one installer exe.

James receives DragonAIAgentSetup.exe only. The desktop payload
(DragonAIAgent.exe and the rest of the install tree) is zipped and
appended to that PE. Setup extracts it at run time. Do not also write
a loose DragonAIAgent.exe next to the installer.

Usage:
    python3 installer/pack.py --out /path/DragonAIAgentSetup.exe

No secrets. Safe to run on Linux with Go (cross-compiles windows/amd64).
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER_DIR = ROOT / "installer"
DESKTOP_DIR = ROOT / "desktop"
DEFAULT_OUT = ROOT / "dist" / "DragonAIAgentSetup.exe"
HANDOFF_NAME = "DragonAIAgentSetup.exe"

TREE_DIRS = (
    "scripts/airmaze",
    "docs/airmaze",
    "bot-groups",
    "branding",
    "templates",
)
ROOT_FILES = (
    "docker-compose.embedded.yml",
    "README.md",
    "CHANGELOG.md",
    "PACKAGING.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
)
LEAF_FILES = (
    "vendor/desktop/README.md",
    "vendor/docker/README.md",
    "desktop/README.md",
    "installer/stage-docker-desktop.py",
    "installer/winres/icon.ico",
    "installer/winres/winres.json",
)
SKIP_DIR_NAMES = {".git", "__pycache__", ".cursor", ".cursor-plugin", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], cwd: pathlib.Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    if proc.returncode != 0:
        fail(f"command failed ({proc.returncode}): {' '.join(cmd)}")


def should_skip(path: pathlib.Path) -> bool:
    if path.name in SKIP_DIR_NAMES:
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    return False


def copy_tree(src: pathlib.Path, dest: pathlib.Path) -> None:
    if not src.is_dir():
        fail(f"missing tree {src}")
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if should_skip(item):
            continue
        target = dest / item.name
        if item.is_dir():
            copy_tree(item, target)
        else:
            shutil.copy2(item, target)


def stage_payload(dest: pathlib.Path, desktop_exe: pathlib.Path, with_docker: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for rel in TREE_DIRS:
        copy_tree(ROOT / rel, dest / pathlib.Path(rel))
    for rel in ROOT_FILES:
        src = ROOT / rel
        if not src.is_file():
            fail(f"missing {rel}")
        shutil.copy2(src, dest / rel)
    for rel in LEAF_FILES:
        src = ROOT / rel
        if not src.is_file():
            fail(f"missing {rel}")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

    install_src = ROOT / "scripts" / "airmaze" / "install.ps1"
    shutil.copy2(install_src, dest / "install.ps1")
    uninstall_src = ROOT / "scripts" / "airmaze" / "uninstall.ps1"
    if not uninstall_src.is_file():
        fail("missing scripts/airmaze/uninstall.ps1")
    shutil.copy2(uninstall_src, dest / "uninstall.ps1")

    unpacked = dest / "desktop" / "win-unpacked"
    unpacked.mkdir(parents=True, exist_ok=True)
    if not desktop_exe.is_file():
        fail(f"desktop exe missing: {desktop_exe}")
    shutil.copy2(desktop_exe, unpacked / "DragonAIAgent.exe")

    docker_src = ROOT / "vendor" / "docker" / "Docker Desktop Installer.exe"
    if with_docker:
        if not docker_src.is_file():
            fail(" --with-docker set but vendor/docker/Docker Desktop Installer.exe is not staged")
        docker_dest = dest / "vendor" / "docker"
        docker_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(docker_src, docker_dest / "Docker Desktop Installer.exe")

    if not (dest / "install.ps1").is_file():
        fail("payload staging lost install.ps1")
    if not (dest / "uninstall.ps1").is_file():
        fail("payload staging lost uninstall.ps1")
    if not (unpacked / "DragonAIAgent.exe").is_file():
        fail("payload staging lost desktop/win-unpacked/DragonAIAgent.exe")


def zip_payload(payload_dir: pathlib.Path, zip_path: pathlib.Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(payload_dir.rglob("*")):
            if path.is_dir():
                continue
            zf.write(path, path.relative_to(payload_dir).as_posix())
    if zip_path.stat().st_size < 1000:
        fail(f"payload zip is too small: {zip_path.stat().st_size} bytes")


def build_desktop(out_exe: pathlib.Path) -> None:
    out_exe.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    run(
        [
            "go",
            "build",
            "-ldflags=-H windowsgui -s -w",
            "-o",
            str(out_exe),
            ".",
        ],
        cwd=DESKTOP_DIR,
        env=env,
    )
    if not out_exe.is_file():
        fail("desktop go build produced no exe")


def build_setup(out_exe: pathlib.Path) -> None:
    out_exe.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    run(
        ["go", "build", "-o", str(out_exe), "."],
        cwd=INSTALLER_DIR,
        env=env,
    )
    if not out_exe.is_file():
        fail("installer go build produced no exe")


def append_zip(exe_path: pathlib.Path, zip_path: pathlib.Path) -> None:
    with exe_path.open("ab") as out, zip_path.open("rb") as zf:
        shutil.copyfileobj(zf, out)


def assert_pe(path: pathlib.Path) -> None:
    magic = path.read_bytes()[:2]
    if magic != b"MZ":
        fail(f"{path.name} is not a Windows PE (missing MZ header)")


def assert_self_zip(path: pathlib.Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile as exc:
        fail(f"{path.name} is not a self-extracting zip: {exc}")
    if "install.ps1" not in names:
        fail(f"{path.name} embedded zip is missing install.ps1")
    desktop = "desktop/win-unpacked/DragonAIAgent.exe"
    if desktop not in names:
        fail(f"{path.name} embedded zip is missing {desktop}")
    return names


def resolve_out(raw: str) -> pathlib.Path:
    path = pathlib.Path(raw).expanduser().resolve()
    if path.exists() and path.is_dir():
        return path / HANDOFF_NAME
    if path.suffix.lower() != ".exe":
        path.mkdir(parents=True, exist_ok=True)
        return path / HANDOFF_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def assert_single_handoff_exe(out_exe: pathlib.Path) -> None:
    parent = out_exe.parent
    extras = [
        p
        for p in parent.iterdir()
        if p.is_file() and p.suffix.lower() == ".exe" and p.resolve() != out_exe.resolve()
    ]
    if extras:
        names = ", ".join(p.name for p in extras)
        fail(f"handoff folder has extra exe(s) beside {out_exe.name}: {names}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"handoff file or directory (default {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--skip-desktop-build",
        action="store_true",
        help="reuse desktop/win-unpacked/DragonAIAgent.exe instead of rebuilding",
    )
    parser.add_argument(
        "--with-docker",
        action="store_true",
        help="embed vendor/docker/Docker Desktop Installer.exe if already staged",
    )
    args = parser.parse_args()

    if shutil.which("go") is None:
        fail("Go is not installed; cannot cross-compile DragonAIAgentSetup.exe")

    out_exe = resolve_out(args.out)
    if out_exe.name != HANDOFF_NAME:
        fail(f"handoff file must be named {HANDOFF_NAME}, got {out_exe.name}")

    packaged_desktop = DESKTOP_DIR / "win-unpacked" / "DragonAIAgent.exe"
    if args.skip_desktop_build and not packaged_desktop.is_file():
        fail(" --skip-desktop-build set but desktop/win-unpacked/DragonAIAgent.exe is missing")

    with tempfile.TemporaryDirectory(prefix="dragon-pack-") as tmp:
        tmp_path = pathlib.Path(tmp)
        payload = tmp_path / "payload"
        payload_zip = tmp_path / "payload.zip"
        setup_exe = tmp_path / HANDOFF_NAME
        if args.skip_desktop_build:
            desktop_exe = packaged_desktop
        else:
            desktop_exe = tmp_path / "DragonAIAgent.exe"
            build_desktop(desktop_exe)
        stage_payload(payload, desktop_exe, with_docker=args.with_docker)
        zip_payload(payload, payload_zip)
        build_setup(setup_exe)
        append_zip(setup_exe, payload_zip)
        assert_pe(setup_exe)
        names = assert_self_zip(setup_exe)
        if out_exe.exists():
            out_exe.unlink()
        # Artifact stores often reject chmod/copystat; copy bytes only.
        shutil.copyfile(setup_exe, out_exe)

    assert_pe(out_exe)
    names = assert_self_zip(out_exe)
    assert_single_handoff_exe(out_exe)
    size = out_exe.stat().st_size
    print(f"OK  {out_exe} ({size} bytes)")
    print(f"    embedded {len(names)} payload files; top-level handoff is one exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
