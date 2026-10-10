"""Reclaim a leftover X11 display lock/socket in a reused sandbox.

TigerVNC refuses to start when ``/tmp/.X<N>-lock`` exists and the pid inside it
is alive — even when that pid is some other process (PID reuse after a container
restart) or ``/tmp/.X11-unix/X<N>`` is a leftover file from a dead server. A
live X server is detected by *what the pid is*, not merely that a pid exists,
plus the kernel's bound-socket table (the lock file can vanish under a live
Xvnc).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

# no-tmp: ok — the X11 protocol fixes the lock and the display socket under /tmp
_X_LOCK_DIR = Path("/tmp")
_X_UNIX_DIR = Path("/tmp/.X11-unix")
_X_UNIX_TABLE = Path("/proc/net/unix")
_X_SERVER_NAMES = frozenset({"X", "Xorg", "Xvnc", "Xtigervnc"})

STALE_DISPLAY_ERROR = (
    "The sandbox screen could not start because a leftover display lock from a "
    "previous run was still in the reused container. That lock is cleared "
    "automatically — click Start screen again if this keeps happening."
)
START_TIMEOUT_ERROR = (
    "The sandbox screen did not become ready in time. Click Start screen to try again."
)


def lock_path(num: int, lock_dir: Optional[Path] = None) -> Path:
    return (lock_dir if lock_dir is not None else _X_LOCK_DIR) / f".X{int(num)}-lock"


def socket_path(num: int, unix_dir: Optional[Path] = None) -> Path:
    return (unix_dir if unix_dir is not None else _X_UNIX_DIR) / f"X{int(num)}"


def lock_pid(num: int, lock_dir: Optional[Path] = None) -> Optional[int]:
    try:
        return int(lock_path(num, lock_dir).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _pid_comm(pid: int, proc_root: Path) -> str:
    try:
        return (proc_root / str(pid) / "comm").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _pid_cmdline(pid: int, proc_root: Path) -> str:
    try:
        raw = (proc_root / str(pid) / "cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace")


def is_x_server_pid(pid: int, proc_root: Path = Path("/proc")) -> bool:
    """True when ``pid`` is an X server, not a recycled pid that inherited the lock file."""
    comm = _pid_comm(pid, proc_root)
    if comm in _X_SERVER_NAMES:
        return True
    cmd = _pid_cmdline(pid, proc_root)
    if not cmd:
        return False
    first = Path(cmd.split(" ", 1)[0]).name
    return first in _X_SERVER_NAMES or "Xvnc" in cmd or "Xorg" in cmd


def socket_bound(num: int, unix_table: Optional[Path] = None) -> bool:
    """A running X server keeps ``@/tmp/.X11-unix/X<n>`` (or the filesystem socket) bound."""
    table = unix_table if unix_table is not None else _X_UNIX_TABLE
    try:
        lines = table.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    target = f"/tmp/.X11-unix/X{int(num)}"
    return any(line.split()[-1].lstrip("@") == target for line in lines if line.strip())


def display_server_healthy(
    num: int,
    *,
    lock_dir: Optional[Path] = None,
    unix_table: Optional[Path] = None,
    proc_root: Path = Path("/proc"),
    alive: Callable[[int], bool] = pid_alive,
) -> bool:
    """True when a live X server (not a recycled pid or a leftover socket file) owns ``:num``."""
    pid = lock_pid(num, lock_dir)
    if pid is not None and alive(pid) and is_x_server_pid(pid, proc_root):
        return True
    return socket_bound(num, unix_table)


def clear_display_files(num: int, *, lock_dir: Optional[Path] = None, unix_dir: Optional[Path] = None) -> None:
    lock_path(num, lock_dir).unlink(missing_ok=True)
    socket_path(num, unix_dir).unlink(missing_ok=True)


def reclaim_display(
    num: int,
    *,
    lock_dir: Optional[Path] = None,
    unix_dir: Optional[Path] = None,
    unix_table: Optional[Path] = None,
    proc_root: Path = Path("/proc"),
    alive: Callable[[int], bool] = pid_alive,
) -> str:
    """``reuse`` if a healthy server owns the display; otherwise drop stale files and return ``cleared``."""
    if display_server_healthy(num, lock_dir=lock_dir, unix_table=unix_table,
                              proc_root=proc_root, alive=alive):
        return "reuse"
    clear_display_files(num, lock_dir=lock_dir, unix_dir=unix_dir)
    return "cleared"


def is_stale_display_log(text: str) -> bool:
    low = (text or "").lower()
    return (
        "already active for display" in low
        or "xvnc exited during startup" in low
        or (".x" in low and "-lock" in low and "no longer running" in low)
    )


def is_retryable_sandbox_start_error(text: str) -> bool:
    return is_stale_display_log(text)


def format_sandbox_start_error(wait_seconds: float, log_or_message: str) -> str:
    if is_stale_display_log(log_or_message):
        return STALE_DISPLAY_ERROR
    if "did not publish" in (log_or_message or "").lower():
        return START_TIMEOUT_ERROR
    return (
        f"The sandbox screen did not become ready within {wait_seconds:.0f}s. "
        "Click Start screen to try again."
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2 or args[0] not in {"reclaim", "clear"}:
        print("usage: display_lock.py reclaim|clear <display-num>", file=sys.stderr)
        return 2
    try:
        num = int(args[1])
    except ValueError:
        print("display-num must be an integer", file=sys.stderr)
        return 2
    if args[0] == "clear":
        clear_display_files(num)
        print("cleared")
        return 0
    print(reclaim_display(num))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
