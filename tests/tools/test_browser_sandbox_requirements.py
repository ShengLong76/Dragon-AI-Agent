"""Browser tools advertise when the bot's screen is inside the sandbox, even
without a host agent-browser / Chromium (Windows Docker Desktop).
"""

from __future__ import annotations

from tools.bot_desktop import placement
from tools.browser_tool_install import check_browser_requirements
from tools import browser_tool as bt
from tools import browser_tool_cdp as cdp
from tools import browser_tool_cloud as cloud
from tools import browser_tool_install as install


def _no_host_browser(monkeypatch) -> None:
    monkeypatch.setattr(bt, "_is_browser_use_cli_mode", lambda: False)
    monkeypatch.setattr(bt, "_is_camofox_mode", lambda: False)
    monkeypatch.setattr(cdp, "_get_cdp_override_raw", lambda: None)
    monkeypatch.setattr(cloud, "_get_cloud_provider", lambda: None)
    monkeypatch.setattr(install, "_find_agent_browser",
                        lambda **_k: (_ for _ in ()).throw(FileNotFoundError("no host agent-browser")))
    monkeypatch.setattr(install, "_chromium_installed", lambda: False)


def test_sandbox_placement_advertises_browser_tools_without_a_host_cli(monkeypatch):
    _no_host_browser(monkeypatch)
    monkeypatch.setattr(placement, "resolve",
                        lambda: placement.Placement(placement.TERMINAL, "docker"))
    assert check_browser_requirements() is True


def test_gateway_placement_still_needs_a_host_browser(monkeypatch):
    _no_host_browser(monkeypatch)
    monkeypatch.setattr(placement, "resolve",
                        lambda: placement.Placement(placement.GATEWAY, "local"))
    assert check_browser_requirements() is False
