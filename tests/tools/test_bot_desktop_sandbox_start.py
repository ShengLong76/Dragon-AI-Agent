"""Sandbox Bot Desktop start: stale X lock retry + friendly error (reused Docker guest)."""
from __future__ import annotations

import pytest

from tools.bot_desktop import display_lock, sandbox_host


class _FakeDocker:
    _docker_exe = "docker"
    _container_id = "c0ffee"

    def get_temp_dir(self):
        return "/tmp"  # no-tmp: ok — sandbox-side path


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


_STALE = (
    "sandbox desktop did not publish its display within 20s:\n"
    "(EE) Fatal server error:\n"
    "(EE) Server is already active for display 20\n"
    "If this server is no longer running, remove /tmp/.X20-lock and start again.\n"
    "(EE) Xvnc exited during startup"
)


def test_start_retries_once_after_a_stale_display_lock(monkeypatch, isolated_home):
    """A reused sandbox leaves .X<N>-lock; the first Xvnc dies 'already active'. One reclaim+retry
    must bring the screen up instead of surfacing the raw Xvnc dump."""
    env = _FakeDocker()
    num = sandbox_host.sandbox_display_num("default")
    monkeypatch.setattr(sandbox_host, "_published", lambda *a, **k: {})
    monkeypatch.setattr(sandbox_host, "missing_binaries", lambda e: [])
    monkeypatch.setattr(sandbox_host, "stop", lambda *a, **k: True)
    reclaimed: list[int] = []
    monkeypatch.setattr(sandbox_host, "_reclaim_sandbox_display", lambda e, n: reclaimed.append(n) or "cleared")
    attempts: list[int] = []

    def _attempt(*a, **k):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError(_STALE)
        return {"DISPLAY": f":{num}", "XAUTHORITY": "/x"}

    monkeypatch.setattr(sandbox_host, "_attempt_start", _attempt)
    out = sandbox_host.start(env, "default", geometry="1280x800")
    assert out["DISPLAY"] == f":{num}"
    assert attempts == [1, 1]
    assert reclaimed == [num, num]


def test_start_surfaces_a_friendly_error_after_the_retry(monkeypatch, isolated_home):
    env = _FakeDocker()
    monkeypatch.setattr(sandbox_host, "_published", lambda *a, **k: {})
    monkeypatch.setattr(sandbox_host, "missing_binaries", lambda e: [])
    monkeypatch.setattr(sandbox_host, "stop", lambda *a, **k: True)
    monkeypatch.setattr(sandbox_host, "_reclaim_sandbox_display", lambda e, n: "cleared")
    attempts: list[int] = []

    def _attempt(*a, **k):
        attempts.append(1)
        raise RuntimeError(_STALE)

    monkeypatch.setattr(sandbox_host, "_attempt_start", _attempt)
    with pytest.raises(RuntimeError) as ei:
        sandbox_host.start(env, "default", geometry="1280x800")
    msg = str(ei.value)
    assert attempts == [1, 1]
    assert msg == display_lock.STALE_DISPLAY_ERROR
    assert "(EE)" not in msg
    assert "already active" not in msg.lower()


def test_start_does_not_retry_an_unrelated_seed_failure(monkeypatch, isolated_home):
    env = _FakeDocker()
    monkeypatch.setattr(sandbox_host, "_published", lambda *a, **k: {})
    monkeypatch.setattr(sandbox_host, "missing_binaries", lambda e: [])
    monkeypatch.setattr(sandbox_host, "stop", lambda *a, **k: True)
    monkeypatch.setattr(sandbox_host, "_reclaim_sandbox_display", lambda e, n: "cleared")
    attempts: list[int] = []

    def _attempt(*a, **k):
        attempts.append(1)
        raise RuntimeError("could not seed the sandbox desktop dir: disk full")

    monkeypatch.setattr(sandbox_host, "_attempt_start", _attempt)
    with pytest.raises(RuntimeError, match="disk full"):
        sandbox_host.start(env, "default", geometry="1280x800")
    assert attempts == [1]


def test_start_in_sandbox_surfaces_sandbox_image_error(monkeypatch, isolated_home):
    """display.start shows the operator-facing image-fallback text, not a generic miss."""
    from tools.bot_desktop import runtime
    from tools.environments.sandbox_image import (
        SandboxImageError,
        UPSTREAM_SANDBOX_IMAGE,
        unavailable_sandbox_image_message,
    )

    def _boom(*, create):
        raise SandboxImageError(unavailable_sandbox_image_message())

    monkeypatch.setattr(runtime, "_sandbox_env", _boom)
    with pytest.raises(SandboxImageError, match="Bot Desktop cannot start") as ei:
        runtime._start_in_sandbox(1.0)
    assert UPSTREAM_SANDBOX_IMAGE in str(ei.value)
    assert "pull access denied" in str(ei.value)


def test_start_in_sandbox_surfaces_docker_daemon_error(monkeypatch, isolated_home):
    """Docker-not-running must reach the Computer pane, not become a generic close."""
    from tools.bot_desktop import runtime
    from tools.environments.base import EnvironmentConnectionError

    def _boom(*, create):
        raise EnvironmentConnectionError(
            "Docker daemon is not responding. Ensure Docker is running and try again.",
            retry_hint="Start Docker Desktop, then retry.",
        )

    monkeypatch.setattr(runtime, "_sandbox_env", _boom)
    with pytest.raises(EnvironmentConnectionError, match="Docker daemon is not responding") as ei:
        runtime._start_in_sandbox(1.0)
    assert "Start Docker Desktop" in ei.value.retry_hint


def test_stop_clears_the_sandbox_display_lock(monkeypatch, isolated_home):
    env = _FakeDocker()
    cleared: list[int] = []
    monkeypatch.setattr(sandbox_host, "_user_for", lambda e: "pn")
    monkeypatch.setattr(sandbox_host.streams, "run_in", lambda *a, **k: type("P", (), {"returncode": 0, "stdout": b""})())
    monkeypatch.setattr(sandbox_host, "_clear_sandbox_display", lambda e, n: cleared.append(n))
    sandbox_host.stop(env, "default")
    assert cleared == [sandbox_host.sandbox_display_num("default")]


def test_seed_files_travel_on_stdin_not_argv(monkeypatch, tmp_path):
    """Windows CreateProcess caps a command line at 32,767 chars; the seeded launcher/lock/wallpaper must not
    ride in argv ([WinError 206])."""
    import io
    import tarfile

    calls = []

    class _Proc:
        returncode = 1
        stdout = b""
        stderr = b"stop here"

    def _run_in(env, argv, *, child_env=None, user=None, timeout=30.0, stdin=None):
        calls.append((argv, stdin))
        return _Proc()

    monkeypatch.setattr(sandbox_host.streams, "run_in", _run_in)
    monkeypatch.setattr(sandbox_host, "_user_for", lambda env: None)
    with pytest.raises(RuntimeError, match="could not seed"):
        sandbox_host._attempt_start(object(), "researcher", "/tmp/x", geometry="1280x800", wait_seconds=1,
                                    browser_exec=None, browser_exec_line=None, display_num=11)
    argv, stdin = calls[0]
    assert sum(len(a) for a in argv) < 2000
    names = tarfile.open(fileobj=io.BytesIO(stdin)).getnames()
    assert sorted(names) == ["display_lock.py", "launcher.sh", "wallpaper.png"]
