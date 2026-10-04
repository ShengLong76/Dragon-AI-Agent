#!/usr/bin/env python3
"""Stage a single-file DragonAIAgentSetup.exe payload zip.

Does not include Docker Desktop Installer.exe (downloaded at install time).
Safe on Linux. No secrets.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"
EMBED = INSTALLER / "embed"
ZIP_PATH = EMBED / "payload.zip"
DESKTOP = ROOT / "desktop"


INCLUDE_FILES = [
    "docker-compose.embedded.yml",
    "README.md",
    "CHANGELOG.md",
    "PACKAGING.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
]

INCLUDE_DIRS = [
    "scripts/airmaze",
    "branding",
    "bot-groups",
    "templates",
    "docs/airmaze",
    "vendor/desktop",
    "vendor/docker",
    "desktop",
    "installer/winres",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def build_desktop() -> None:
    dest = DESKTOP / "win-unpacked"
    dest.mkdir(parents=True, exist_ok=True)
    exe = dest / "DragonAIAgent.exe"
    cmd = [
        "go",
        "build",
        "-ldflags=-H windowsgui -s -w",
        "-o",
        str(exe),
        ".",
    ]
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    print("Building", exe)
    proc = subprocess.run(cmd, cwd=str(DESKTOP), env=env)
    if proc.returncode != 0:
        fail("desktop cross-compile failed")
    if exe.stat().st_size < 1000:
        fail("DragonAIAgent.exe is too small")


def add_tree(zf: zipfile.ZipFile, src: pathlib.Path, arc: str) -> None:
    if src.is_file():
        if src.name.endswith(".exe") and "Docker Desktop" in src.name:
            return
        zf.write(src, arc)
        return
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".exe" and "Docker Desktop" in path.name:
            continue
        if path.name == "payload.zip":
            continue
        rel = path.relative_to(src)
        zf.write(path, f"{arc}/{rel.as_posix()}")


def write_zip() -> None:
    EMBED.mkdir(parents=True, exist_ok=True)
    tmp = ZIP_PATH.with_suffix(".tmp.zip")
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        install = ROOT / "scripts" / "airmaze" / "install.ps1"
        if not install.is_file():
            fail("missing scripts/airmaze/install.ps1")
        zf.write(install, "install.ps1")
        zf.write(install, "scripts/airmaze/install.ps1")
        for rel in INCLUDE_FILES:
            src = ROOT / rel
            if src.is_file():
                zf.write(src, rel)
        for rel in INCLUDE_DIRS:
            src = ROOT / rel
            if src.exists():
                add_tree(zf, src, rel)
    tmp.replace(ZIP_PATH)
    print("Wrote", ZIP_PATH, "bytes", ZIP_PATH.stat().st_size)


def build_setup(out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["go", "build", "-o", str(out), "."]
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    print("Building", out)
    proc = subprocess.run(cmd, cwd=str(INSTALLER), env=env)
    if proc.returncode != 0:
        fail("setup cross-compile failed")
    if out.stat().st_size < 10000:
        fail("DragonAIAgentSetup.exe is too small")
    print("OK", out, "bytes", out.stat().st_size)


def main() -> int:
    build_desktop()
    write_zip()
    dest = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else INSTALLER / "DragonAIAgentSetup.exe"
    build_setup(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
