"""launcher.sh must drop a stale X lock whose pid is alive but is not an X server.

That is the reused-sandbox case: /tmp/.X<N>-lock and /tmp/.X11-unix/X<N> survive
the previous Xvnc, and the pid in the lock has been recycled by bash/sleep.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "tools" / "bot_desktop" / "launcher.sh"
pytestmark = pytest.mark.platforms("linux")


def _bindir(tmp_path: Path, xvnc_log: Path) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "Xvnc").write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$@" > "{xvnc_log}"\nexec sleep 3\n', encoding="utf-8"
    )
    for stub in ("xdpyinfo", "setxkbmap", "xsetroot", "xset", "dbus-run-session", "xauth"):
        (bindir / stub).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for exe in bindir.iterdir():
        exe.chmod(0o755)
    for tool in ("mkdir", "sed", "cat", "printf", "dirname", "bash", "sh", "rm", "ln", "touch",
                 "chmod", "xauth", "od", "tr", "awk", "grep", "seq", "sleep", "kill", "python3"):
        real = shutil.which(tool)
        if real and not (bindir / tool).exists():
            (bindir / tool).symlink_to(real)
    return bindir


def _run_launcher(tmp_path: Path, bindir: Path, num: int, *, own: bool = True) -> subprocess.CompletedProcess:
    env = {
        "PATH": str(bindir), "HOME": str(tmp_path),
        "HERMES_BD_PROFILE": "t", "HERMES_BD_DISPLAY_NUM": str(num),
        "HERMES_BD_SOCKET": str(tmp_path / "rfb.sock"), "HERMES_BD_XAUTH": str(tmp_path / "Xauthority"),
        "HERMES_BD_ENV_FILE": str(tmp_path / "env"), "HERMES_BD_CONFIG_HOME": str(tmp_path / "xdg"),
        "HERMES_BD_OWN_DISPLAY": "1" if own else "",
    }
    return subprocess.run(
        ["bash", str(LAUNCHER)], env=env, cwd=str(tmp_path), check=False,
        stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
    )


def test_launcher_clears_a_recycled_lock_pid_and_starts_xvnc(tmp_path):
    """Lock names this pytest process (alive, not Xvnc) + leftover socket file → start Xvnc."""
    num = 91
    lock = Path(f"/tmp/.X{num}-lock")  # no-tmp: ok — X11 protocol path
    sock = Path(f"/tmp/.X11-unix/X{num}")
    sock.parent.mkdir(mode=0o1777, exist_ok=True)
    lock.write_text(f"     {os.getpid()}\n", encoding="utf-8")
    try:
        sock.write_text("stale", encoding="utf-8")
    except OSError:
        pytest.skip("cannot write the X11 unix socket dir")
    xvnc_log = tmp_path / "xvnc-argv"
    bindir = _bindir(tmp_path, xvnc_log)
    try:
        proc = _run_launcher(tmp_path, bindir, num)
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[-800:]
        assert xvnc_log.exists(), "Xvnc must start after the stale lock is dropped"
        assert not lock.exists(), "stale lock must be removed"
        assert not sock.exists() or sock.is_socket()
    finally:
        lock.unlink(missing_ok=True)
        if sock.exists() and not sock.is_socket():
            sock.unlink(missing_ok=True)


def test_launcher_reuses_a_healthy_xvnc_instead_of_starting_another(tmp_path):
    """Live Xvnc + bound X11 socket + existing RFB socket → do not exec a second Xvnc."""
    num = 92
    lock = Path(f"/tmp/.X{num}-lock")
    xsock_path = Path(f"/tmp/.X11-unix/X{num}")
    xsock_path.parent.mkdir(mode=0o1777, exist_ok=True)
    fake_xvnc = tmp_path / "Xvnc"
    sleep = shutil.which("sleep")
    assert sleep, "sleep is required to stand in for a live Xvnc"
    shutil.copy(sleep, fake_xvnc)
    holder = subprocess.Popen([str(fake_xvnc), "60"], start_new_session=True)
    rfb = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    xsock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        lock.write_text(f"{holder.pid}\n", encoding="utf-8")
        if xsock_path.exists():
            xsock_path.unlink()
        xsock.bind(str(xsock_path))
        xsock.listen(1)
        rfb_path = tmp_path / "rfb.sock"
        if rfb_path.exists():
            rfb_path.unlink()
        rfb.bind(str(rfb_path))
        rfb.listen(1)
        xvnc_log = tmp_path / "xvnc-argv"
        bindir = _bindir(tmp_path, xvnc_log)
        proc = _run_launcher(tmp_path, bindir, num)
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[-800:]
        assert not xvnc_log.exists(), "a healthy leftover Xvnc must be reused, not replaced"
    finally:
        holder.terminate()
        holder.wait(timeout=5)
        rfb.close()
        xsock.close()
        lock.unlink(missing_ok=True)
        if xsock_path.exists():
            xsock_path.unlink()
