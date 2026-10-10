"""Stale X11 lock/socket reclaim: a reused sandbox keeps /tmp/.X<N>-lock after Xvnc dies.

The lock file names a pid. After a container restart that pid is often some other
process (PID reuse) — treating 'pid is alive' as 'X server is up' is what made
Start screen fail with 'Server is already active for display 20'.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.bot_desktop import display_lock


def _write_lock(lock_dir: Path, num: int, pid: int) -> None:
    (lock_dir / f".X{num}-lock").write_text(f"     {pid}\n", encoding="utf-8")


def _unix_table(tmp_path: Path, *nums: int) -> Path:
    table = tmp_path / "unix"
    rows = ["Num       RefCount Protocol Flags    Type St Inode Path"]
    for n in nums:
        rows.append(f"0000000000000000: 00000002 00000000 00010000 0001 01 222{n} @/tmp/.X11-unix/X{n}")
    table.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return table


def test_dead_lock_pid_is_cleared_with_the_socket(tmp_path):
    lock_dir = tmp_path / "locks"
    unix_dir = tmp_path / "X11-unix"
    lock_dir.mkdir()
    unix_dir.mkdir()
    _write_lock(lock_dir, 20, 999999)
    (unix_dir / "X20").write_text("stale", encoding="utf-8")
    assert display_lock.reclaim_display(
        20, lock_dir=lock_dir, unix_dir=unix_dir, unix_table=tmp_path / "missing"
    ) == "cleared"
    assert not (lock_dir / ".X20-lock").exists()
    assert not (unix_dir / "X20").exists()


def test_recycled_pid_that_is_not_an_x_server_is_cleared(tmp_path):
    """The lock names this process (alive) but it is not Xvnc — the reused-container case."""
    lock_dir = tmp_path / "locks"
    unix_dir = tmp_path / "X11-unix"
    lock_dir.mkdir()
    unix_dir.mkdir()
    _write_lock(lock_dir, 20, os.getpid())
    (unix_dir / "X20").write_text("stale", encoding="utf-8")
    assert display_lock.display_server_healthy(
        20, lock_dir=lock_dir, unix_table=tmp_path / "missing"
    ) is False
    assert display_lock.reclaim_display(
        20, lock_dir=lock_dir, unix_dir=unix_dir, unix_table=tmp_path / "missing"
    ) == "cleared"
    assert not (lock_dir / ".X20-lock").exists()
    assert not (unix_dir / "X20").exists()


def test_live_x_server_lock_is_reused_not_cleared(tmp_path):
    lock_dir = tmp_path / "locks"
    unix_dir = tmp_path / "X11-unix"
    proc_root = tmp_path / "proc"
    lock_dir.mkdir()
    unix_dir.mkdir()
    (proc_root / "4242").mkdir(parents=True)
    (proc_root / "4242" / "comm").write_text("Xvnc\n", encoding="utf-8")
    (proc_root / "4242" / "cmdline").write_bytes(b"Xvnc\x00:20\x00")
    _write_lock(lock_dir, 20, 4242)
    (unix_dir / "X20").write_text("live", encoding="utf-8")
    assert display_lock.reclaim_display(
        20, lock_dir=lock_dir, unix_dir=unix_dir, unix_table=tmp_path / "missing",
        proc_root=proc_root, alive=lambda pid: pid == 4242,
    ) == "reuse"
    assert (lock_dir / ".X20-lock").exists()
    assert (unix_dir / "X20").exists()


def test_bound_socket_without_a_lock_file_is_still_a_live_server(tmp_path):
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    table = _unix_table(tmp_path, 20)
    assert display_lock.display_server_healthy(20, lock_dir=lock_dir, unix_table=table) is True
    assert display_lock.display_server_healthy(21, lock_dir=lock_dir, unix_table=table) is False
    assert display_lock.display_server_healthy(200, lock_dir=lock_dir, unix_table=table) is False


def test_friendly_error_hides_the_raw_xvnc_dump():
    raw = (
        "sandbox desktop did not publish its display within 20s:\n"
        "(EE) Fatal server error:\n"
        "(EE) Server is already active for display 20\n"
        "If this server is no longer running, remove /tmp/.X20-lock and start again.\n"
        "(EE) Xvnc exited during startup"
    )
    msg = display_lock.format_sandbox_start_error(20, raw)
    assert "leftover display lock" in msg
    assert "(EE)" not in msg
    assert "/tmp/.X20-lock" not in msg
    assert display_lock.is_retryable_sandbox_start_error(raw)


def test_unrelated_timeout_is_not_retryable():
    raw = "sandbox desktop did not publish its display within 20s:\nxfsettingsd hung"
    assert display_lock.is_retryable_sandbox_start_error(raw) is False
    assert "Click Start screen" in display_lock.format_sandbox_start_error(20, raw)
    assert "xfsettingsd" not in display_lock.format_sandbox_start_error(20, raw)


@pytest.mark.platforms("linux")
def test_cli_reclaim_clears_a_stale_lock_on_this_host(tmp_path, monkeypatch):
    """The script the sandbox runs (python3 display_lock.py reclaim N) against real /tmp paths."""
    lock_dir = tmp_path / "locks"
    unix_dir = tmp_path / "X11-unix"
    lock_dir.mkdir()
    unix_dir.mkdir()
    monkeypatch.setattr(display_lock, "_X_LOCK_DIR", lock_dir)
    monkeypatch.setattr(display_lock, "_X_UNIX_DIR", unix_dir)
    monkeypatch.setattr(display_lock, "_X_UNIX_TABLE", tmp_path / "missing")
    _write_lock(lock_dir, 77, os.getpid())
    (unix_dir / "X77").write_text("stale", encoding="utf-8")
    assert display_lock.main(["reclaim", "77"]) == 0
    assert not (lock_dir / ".X77-lock").exists()
    assert not (unix_dir / "X77").exists()
