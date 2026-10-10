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


def test_stop_clears_the_sandbox_display_lock(monkeypatch, isolated_home):
    env = _FakeDocker()
    cleared: list[int] = []
    monkeypatch.setattr(sandbox_host, "_user_for", lambda e: "pn")
    monkeypatch.setattr(sandbox_host.streams, "run_in", lambda *a, **k: type("P", (), {"returncode": 0, "stdout": b""})())
    monkeypatch.setattr(sandbox_host, "_clear_sandbox_display", lambda e, n: cleared.append(n))
    sandbox_host.stop(env, "default")
    assert cleared == [sandbox_host.sandbox_display_num("default")]
