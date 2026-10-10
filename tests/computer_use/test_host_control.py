"""computer_use.host_control is off by default: the tool drives the bot's sandbox
screen, never this machine's seat (Windows UIA / macOS AX / the user's X session).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.bot_desktop import placement, runtime, sandbox_host
from tools.computer_use import cua_backend


def _write_config(tmp_path, body: str) -> None:
    (tmp_path / "config.yaml").write_text(body, encoding="utf-8")


def _gateway_without_a_screen(monkeypatch) -> None:
    monkeypatch.setattr(placement, "resolve",
                        lambda: placement.Placement(placement.GATEWAY, "local"))
    monkeypatch.setattr(sandbox_host, "_read_marker", lambda: {})
    monkeypatch.setattr(runtime, "is_running", lambda: False)
    monkeypatch.setattr(runtime, "published_env", lambda: {})


class TestHostControlDefault:
    def test_unspecified_key_is_off_through_the_real_loader(self, tmp_path, monkeypatch):
        _write_config(tmp_path, "model: test\n")
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert cua_backend.host_control_enabled() is False

    def test_explicit_true_reaches_the_reader(self, tmp_path, monkeypatch):
        _write_config(tmp_path, "computer_use:\n  host_control: true\n")
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        assert cua_backend.host_control_enabled() is True


class TestTargetSelection:
    def test_sandbox_placement_wins_while_host_control_is_off(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "host_control_enabled", lambda: False)
        monkeypatch.setattr(placement, "resolve",
                            lambda: placement.Placement(placement.TERMINAL, "docker"))
        assert cua_backend.resolve_computer_use_target() == "sandbox"

    def test_leftover_sandbox_marker_wins_over_gateway_placement(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "host_control_enabled", lambda: False)
        monkeypatch.setattr(placement, "resolve",
                            lambda: placement.Placement(placement.GATEWAY, "local"))
        monkeypatch.setattr(sandbox_host, "_read_marker",
                            lambda: {"container": "hermes-deadbeef", "display": ":20"})
        assert cua_backend.resolve_computer_use_target() == "sandbox"

    def test_host_seat_is_refused_when_host_control_is_off(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "host_control_enabled", lambda: False)
        _gateway_without_a_screen(monkeypatch)
        with pytest.raises(RuntimeError, match="host_control is off"):
            cua_backend.resolve_computer_use_target()

    def test_host_seat_is_refused_by_sandbox_mcp_when_host_control_is_off(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "host_control_enabled", lambda: False)
        _gateway_without_a_screen(monkeypatch)
        with pytest.raises(RuntimeError, match="host_control is off"):
            cua_backend.sandbox_mcp_invocation()

    def test_opt_in_allows_the_host_seat(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "host_control_enabled", lambda: True)
        _gateway_without_a_screen(monkeypatch)
        assert cua_backend.resolve_computer_use_target() == "host"
        assert cua_backend.sandbox_mcp_invocation() is None

    def test_running_gateway_bot_desktop_is_the_bot_screen_not_host_control(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "host_control_enabled", lambda: False)
        monkeypatch.setattr(placement, "resolve",
                            lambda: placement.Placement(placement.GATEWAY, "local"))
        monkeypatch.setattr(sandbox_host, "_read_marker", lambda: {})
        monkeypatch.setattr(runtime, "is_running", lambda: True)
        monkeypatch.setattr(runtime, "published_env", lambda: {"DISPLAY": ":1"})
        assert cua_backend.resolve_computer_use_target() == "host"
        assert cua_backend.sandbox_mcp_invocation() is None


class TestSandboxCliFallback:
    def test_cli_fallback_never_spawns_the_host_driver(self, monkeypatch):
        from tools.computer_use.cua_backend_session import _CuaDriverSession

        spawned: list[list[str]] = []

        def _forbid_cli(cmd, env, name, timeout):
            spawned.append(cmd)
            raise AssertionError("host cua-driver CLI must not run against a sandbox session")

        monkeypatch.setattr("tools.computer_use.cua_backend_session._cli_run_json", _forbid_cli)
        monkeypatch.setattr("tools.computer_use.cua_backend_driver.resolve_cua_driver_cmd",
                            lambda: "/host/cua-driver")
        session = _CuaDriverSession(SimpleNamespace(), None)
        session._sandbox_driver = True
        with pytest.raises(RuntimeError, match="host-only"):
            session._call_tool_via_cli("list_windows", {}, 5.0)
        assert spawned == []
