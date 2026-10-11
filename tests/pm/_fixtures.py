"""Minimal PM test helpers used by scripts/CLI tests in this checkout.

Upstream Hermes vendors a richer ``tests.pm`` package. Dragon's snapshot does
not, but several posix-marked files still import these names at collection
time. Keep ``stage_host_python`` real (a symlink to the host interpreter);
fixtures we do not own skip instead of inventing a client.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest


def stage_host_python(dest: Path) -> Path:
    """Place a usable interpreter at ``dest`` without copying the whole prefix."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.symlink_to(source)
    return dest


def _wheel(directory: Path, name: str) -> Path:
    """Write a tiny pure-Python wheel so bundle tests have a find-links target."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    dist_name = name.replace("_", "-")
    path = directory / f"{dist_name}-1.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{name}-1.0.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {dist_name}\nVersion: 1.0\n",
        )
        archive.writestr(
            f"{name}-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: tests.pm\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(f"{name}/__init__.py", "")
    return path


@pytest.fixture
def client():
    pytest.skip("PM client fixture is not vendored in this checkout")


@pytest.fixture
def isolated_python():
    pytest.skip("PM isolated_python fixture is not vendored in this checkout")


@pytest.fixture
def source_launch():
    pytest.skip("PM source_launch fixture is not vendored in this checkout")
