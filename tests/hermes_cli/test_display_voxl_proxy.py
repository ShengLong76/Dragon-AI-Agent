"""The voxl reverse-proxy admits on a display ticket, never puts the password in a URL, and rewrites the client."""

from __future__ import annotations

from hermes_cli.dashboard_auth import ws_tickets
from hermes_cli.dashboard_auth.public_paths import display_voxl_admitted
from hermes_cli.web_routers import display_voxl


def test_display_voxl_admit_requires_ticket_or_cookie():
    assert display_voxl_admitted("/api/display/voxl", ticket="t") is True
    assert display_voxl_admitted("/api/display/voxl/client.js", cookie="c") is True
    assert display_voxl_admitted("/api/display/voxl", ticket="", cookie="") is False
    assert display_voxl_admitted("/api/display/ws", ticket="t") is False
    assert display_voxl_admitted("/api/status", ticket="t") is False


def test_query_rewrite_drops_token_and_password_fields():
    dropped = display_voxl._drop_secret_query(
        "display_ticket=abc&token=SECRET&stats=1&password=SECRET&basic-auth-password=SECRET")
    assert "SECRET" not in dropped
    assert "token=" not in dropped
    assert "display_ticket=" not in dropped
    assert "stats=1" in dropped


def test_html_rewrite_prefixes_assets_and_injects_ws_bootstrap():
    html = b'<!doctype html><head><link href="/client.css"><script src="/client.js"></script></head><body></body>'
    out = display_voxl._rewrite_html(html).decode("utf-8")
    assert 'href="/api/display/voxl/client.css"' in out
    assert 'src="/api/display/voxl/client.js"' in out
    assert "hermes-display-ws-close" in out
    assert 'prefix + "/ws"' in out
    assert "token=" not in out.lower()


def test_http_proxy_consumes_ticket_and_does_not_echo_password(tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    from hermes_cli import web_server

    ws_tickets._reset_for_tests()
    display_voxl._reset_for_tests()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(display_voxl, "_upstream", lambda info: None)
    prev = {k: getattr(web_server.app.state, k, None) for k in ("auth_required", "bound_host")}
    web_server.app.state.auth_required = False
    web_server.app.state.bound_host = None
    ticket = ws_tickets.mint_ticket(
        user_id="display:v", provider="bot-desktop",
        extra={"hermes_home": str(tmp_path), "viewer_id": "v"},
    )
    client = TestClient(web_server.app)
    try:
        resp = client.get(f"/api/display/voxl?display_ticket={ticket}&token=SHOULD-NOT-LEAK")
        assert resp.status_code == 404
        assert "SHOULD-NOT-LEAK" not in resp.text
        assert "VOXL_PASSWORD" not in resp.text
        again = client.get(f"/api/display/voxl?display_ticket={ticket}")
        assert again.status_code == 401
    finally:
        client.close()
        ws_tickets._reset_for_tests()
        display_voxl._reset_for_tests()
        for key, value in prev.items():
            if value is None:
                if hasattr(web_server.app.state, key):
                    delattr(web_server.app.state, key)
            else:
                setattr(web_server.app.state, key, value)
