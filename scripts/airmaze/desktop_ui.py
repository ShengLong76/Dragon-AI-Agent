#!/usr/bin/env python3
"""Prove a launch URL is the Hermes desktop web UI, not headless serve.

James verified on UltraDragon: DragonAIAgent.exe opened
http://127.0.0.1:8650/ and that URL returned HTTP 200 with

    Headless backend (hermes serve): web UI disabled - use `hermes dashboard`
    for the browser UI.

:8650 is the Bot Screen JSON-RPC/WS API. The window must load the
dashboard web UI (published on :8660 by default) instead. A launch that
only gets the headless body must fail.

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HEADLESS_MARKERS = (
    "web UI disabled",
    "Headless backend (hermes serve)",
    "use `hermes dashboard` for the browser UI",
    "use 'hermes dashboard' for the browser UI",
)

HEADLESS_FIXTURE = (
    "Headless backend (hermes serve): web UI disabled - "
    "use `hermes dashboard` for the browser UI."
)

DEFAULT_WINDOW_UPSTREAM = "http://127.0.0.1:8660/"
DEFAULT_SERVE_API = "http://127.0.0.1:8650/"


def is_headless_page(body: str | bytes | None) -> bool:
    if body is None:
        return False
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    return any(marker in text for marker in HEADLESS_MARKERS)


def is_html_page(body: str | bytes | None) -> bool:
    if body is None:
        return False
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    low = text.lower()
    return "<html" in low or "<!doctype html" in low


def is_desktop_web_ui(body: str | bytes | None) -> bool:
    return is_html_page(body) and not is_headless_page(body)


def fetch_body(url: str, timeout: float = 3.0, token: str = "") -> tuple[int, str]:
    req = Request(url, headers={"Accept": "text/html,*/*"})
    if token:
        req.add_header("X-Hermes-Session-Token", token)
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read(256 * 1024)
            return int(res.status), raw.decode("utf-8", "replace")
    except HTTPError as exc:
        raw = exc.read(256 * 1024) if exc.fp else b""
        return int(exc.code), raw.decode("utf-8", "replace")
    except URLError as exc:
        raise ConnectionError(f"desktop web UI unreachable at {url}: {exc}") from exc


def assert_desktop_web_ui(url: str, timeout: float = 3.0, token: str = "") -> dict[str, Any]:
    status, body = fetch_body(url, timeout=timeout, token=token)
    if is_headless_page(body):
        raise ValueError(
            f"refusing headless hermes serve page at {url} "
            "(body contains 'web UI disabled'). Point the window at hermes dashboard."
        )
    if not is_html_page(body):
        raise ValueError(f"desktop UI at {url} is not an HTML page (HTTP {status})")
    return {
        "ok": True,
        "url": url,
        "status": status,
        "headless": False,
        "html": True,
    }


def overlay_snippets() -> list[tuple[str, str]]:
    return [
        ('data-dragon-ai-branding="ui-face"', '<link rel="stylesheet" href="/dragon-ai-branding/dragon-ui.css" data-dragon-ai-branding="ui-face">'),
        ('data-dragon-ai-branding="sidebar-header"', '<script src="/dragon-ai-branding/sidebar-header.js" data-dragon-ai-branding="sidebar-header"></script>'),
        ('data-dragon-ai-branding="teams-picker"', '<script src="/dragon-ai-branding/teams-picker.js" data-dragon-ai-branding="teams-picker"></script>'),
        ('data-dragon-ai-branding="provider-setup"', '<script src="/dragon-ai-branding/provider-setup.js" data-dragon-ai-branding="provider-setup"></script>'),
        ('data-dragon-ai-branding="bot-workspace"', '<script src="/dragon-ai-branding/bot-workspace.js" data-dragon-ai-branding="bot-workspace"></script>'),
        ('data-dragon-ai-branding="first-run-models"', '<script src="/dragon-ai-branding/first-run-models.js" data-dragon-ai-branding="first-run-models"></script>'),
        ('data-dragon-ai-branding="voice-provider"', '<script src="/dragon-ai-branding/dragon-voice-selector.js" data-dragon-ai-branding="voice-provider"></script>'),
        ('data-dragon-ai-branding="voice-settings"', '<script src="/dragon-ai-branding/dragon-voice-settings.js" data-dragon-ai-branding="voice-settings"></script>'),
    ]


def inject_overlay(html: str) -> str:
    missing = [snip for mark, snip in overlay_snippets() if mark not in html]
    if not missing:
        return html
    insert = "\n".join(missing) + "\n"
    lower = html.lower()
    idx = lower.find("</head>")
    if idx != -1:
        return html[:idx] + insert + html[idx:]
    idx = lower.find("</body>")
    if idx != -1:
        return html[:idx] + insert + html[idx:]
    return html + "\n" + insert


def _self_test() -> int:
    if not is_headless_page(HEADLESS_FIXTURE):
        print("FAIL: headless fixture was not detected", file=sys.stderr)
        return 1
    if is_desktop_web_ui(HEADLESS_FIXTURE):
        print("FAIL: headless fixture was accepted as the desktop web UI", file=sys.stderr)
        return 1
    good = "<!DOCTYPE html><html><head><title>Dragon AI Agent</title></head><body>chat</body></html>"
    if not is_desktop_web_ui(good):
        print("FAIL: HTML desktop page was rejected", file=sys.stderr)
        return 1
    injected = inject_overlay(good)
    if 'data-dragon-ai-branding="first-run-models"' not in injected:
        print("FAIL: overlay inject missed first-run models", file=sys.stderr)
        return 1
    if 'data-dragon-ai-branding="provider-setup"' not in injected:
        print("FAIL: overlay inject missed provider-setup", file=sys.stderr)
        return 1
    if 'data-dragon-ai-branding="bot-workspace"' not in injected:
        print("FAIL: overlay inject missed bot-workspace", file=sys.stderr)
        return 1

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/headless":
                body = HEADLESS_FIXTURE.encode("utf-8")
            else:
                body = good.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        try:
            assert_desktop_web_ui(f"http://127.0.0.1:{port}/headless")
            print("FAIL: assert_desktop_web_ui accepted the headless page", file=sys.stderr)
            return 1
        except ValueError as exc:
            if "web UI disabled" not in str(exc):
                print(f"FAIL: headless refuse message unclear: {exc}", file=sys.stderr)
                return 1
        result = assert_desktop_web_ui(f"http://127.0.0.1:{port}/ok")
        if result.get("ok") is not True:
            print(f"FAIL: good page result {result}", file=sys.stderr)
            return 1
    finally:
        server.shutdown()
        server.server_close()
    print("OK  desktop_ui self-test (headless page refused, HTML web UI accepted)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--url", default="", help="Fetch this URL and refuse a headless body")
    args = parser.parse_args(argv)
    if args.self_test or not args.url:
        return _self_test()
    try:
        print(json.dumps(assert_desktop_web_ui(args.url), indent=2))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
