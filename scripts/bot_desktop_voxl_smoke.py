#!/usr/bin/env python3
"""Smoke: start Xvfb (-shmem) + voxl and confirm /healthz (and /?stats when present).

Exits 0 on success, 2 when voxl or Xvfb is missing (skip), 1 on failure.
Does not log or print the voxl password. Binds 127.0.0.1 only.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def _which(name: str) -> str | None:
    return shutil.which(name)


def main() -> int:
    voxl = _which("voxl")
    xvfb = _which("Xvfb")
    if not voxl or not xvfb:
        print("skip: voxl or Xvfb not on PATH")
        return 2
    root = Path(tempfile.mkdtemp(prefix="voxl-smoke-"))
    password = "smoke-password-not-for-logs"
    env = os.environ.copy()
    env["VOXL_PASSWORD"] = password
    env.pop("DISPLAY", None)
    xvfb_log = open(root / "xvfb.log", "wb")  # noqa: SIM115
    xvfb_proc = subprocess.Popen(  # noqa: S603
        [xvfb, "-displayfd", "1", "-screen", "0", "640x480x24", "-nolisten", "tcp", "-ac", "-shmem"],
        stdout=subprocess.PIPE, stderr=xvfb_log, env=env,
    )
    xvfb_log.close()
    try:
        assert xvfb_proc.stdout is not None
        raw = xvfb_proc.stdout.readline().decode("ascii", "replace").strip()
        if not raw.isdigit():
            print("Xvfb did not publish a display")
            return 1
        display = f":{raw}"
        env["DISPLAY"] = display
        port = 18765
        voxl_log = open(root / "voxl.err", "wb")  # noqa: SIM115
        voxl_proc = subprocess.Popen(  # noqa: S603
            [voxl, "--addr=127.0.0.1", f"--port={port}", "--enable-basic-auth=true",
             "--title=Dragon AI Screen", "--file-transfers=none", "--framerate=60"],
            stdout=subprocess.DEVNULL, stderr=voxl_log, env=env,
        )
        voxl_log.close()
        health = f"http://127.0.0.1:{port}/healthz"
        deadline = time.monotonic() + 8.0
        ok = False
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(health, timeout=1.0) as resp:
                    if 200 <= getattr(resp, "status", 200) < 300:
                        ok = True
                        break
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.1)
        if not ok:
            print("voxl /healthz did not become ready")
            return 1
        stats_ok = False
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/?stats=1")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                stats_ok = 200 <= getattr(resp, "status", 200) < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            stats_ok = False
        print("healthz=ok stats=" + ("ok" if stats_ok else "absent"))
        voxl_proc.terminate()
        xvfb_proc.terminate()
        return 0
    finally:
        for proc in (locals().get("voxl_proc"), xvfb_proc):
            if proc is not None and proc.poll() is None:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
