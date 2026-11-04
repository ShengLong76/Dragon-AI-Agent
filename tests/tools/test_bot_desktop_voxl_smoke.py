"""Run the voxl smoke script when Xvfb + voxl are present; otherwise skip."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "bot_desktop_voxl_smoke.py"


@pytest.mark.platforms("linux")
def test_voxl_smoke_script_healthz_or_skip():
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if proc.returncode == 2:
        pytest.skip(proc.stdout.strip() or "voxl/Xvfb not installed")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "healthz=ok" in proc.stdout
    assert "token=" not in (proc.stdout + proc.stderr).lower()
