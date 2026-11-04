"""Locate or install a pinned voxl binary (crate ``voxl-server``, binary ``voxl``).

GitHub releases for tembo/voxl ship the crate, not prebuilt executables, so the
installer prefers a PATH / managed-home copy of the pinned version and otherwise
runs ``cargo install voxl-server --version <pin> --locked`` into the profile's
runtime dir. Native libraries (x264, libyuv, Opus, PulseAudio on Linux; vcpkg
x264/libyuv/opus on Windows) must already be on the system.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PINNED_VERSION = "0.3.3"
PINNED_CRATE = "voxl-server"
PINNED_CRATE_SHA256 = "11b169314ce321050ff336c80b295716d152cafbdc4058fdfa6e3108733363a9"
GITHUB_CRATE_URL = f"https://github.com/tembo/voxl/releases/download/v{PINNED_VERSION}/{PINNED_CRATE}-{PINNED_VERSION}.crate"

# Runtime libraries voxl links. Documented for operators; the cargo build needs the -dev set.
LINUX_RUNTIME_LIBS = ("libx264", "libyuv", "libopus", "libpulse")
WINDOWS_VCPKG_PACKAGES = ("x264", "libyuv", "opus")


def binary_name() -> str:
    return "voxl.exe" if sys.platform == "win32" else "voxl"


def runtime_root() -> Path:
    from hermes_constants import get_hermes_home
    return get_hermes_home() / "runtime" / "voxl"


def managed_binary() -> Path:
    return runtime_root() / "bin" / binary_name()


def parse_version(text: str) -> Optional[str]:
    """Pull a dotted version out of ``voxl --version`` output. Never logs the text."""
    for token in (text or "").replace(",", " ").split():
        token = token.strip().lstrip("v")
        parts = token.split(".")
        if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
            return token
    return None


def _run_version(path: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            [str(path), "--version"],
            capture_output=True, text=True, timeout=8, check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_version((proc.stdout or "") + " " + (proc.stderr or ""))


def resolve_binary() -> Optional[Path]:
    """PATH first (so an operator-built voxl wins), then the managed cargo --root copy."""
    found = shutil.which("voxl") or shutil.which(binary_name())
    if found:
        path = Path(found)
        version = _run_version(path)
        if version is None or version == PINNED_VERSION or version.startswith(PINNED_VERSION + "."):
            return path
        logger.info("voxl at %s reports %s (want %s); trying managed copy", path, version, PINNED_VERSION)
    managed = managed_binary()
    if managed.is_file() and os.access(managed, os.X_OK):
        return managed
    return Path(found) if found else None


def is_available() -> bool:
    return resolve_binary() is not None


def cargo_install(timeout: int = 1800) -> Optional[Path]:
    """Install the pinned crate into the managed runtime dir. None when cargo is missing or it fails."""
    cargo = shutil.which("cargo")
    if cargo is None:
        logger.info("voxl: cargo not on PATH; skip install of %s %s", PINNED_CRATE, PINNED_VERSION)
        return None
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("VOXL_PASSWORD", None)
    cmd = [
        cargo, "install", PINNED_CRATE,
        "--version", PINNED_VERSION,
        "--locked",
        "--root", str(root),
        "--force",
    ]
    logger.info("voxl: installing %s %s into %s", PINNED_CRATE, PINNED_VERSION, root)
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout,
            check=False, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("voxl: cargo install failed: %s", exc)
        return None
    if proc.returncode != 0:
        logger.warning("voxl: cargo install exited %s", proc.returncode)
        return None
    binary = managed_binary()
    return binary if binary.is_file() else None


def ensure() -> Optional[Path]:
    """Return a voxl binary, installing the pin when nothing usable is on PATH."""
    existing = resolve_binary()
    if existing is not None:
        return existing
    return cargo_install()
