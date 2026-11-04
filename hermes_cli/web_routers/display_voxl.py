"""Gateway reverse-proxy for a profile's localhost voxl (HTTP + WebSocket).

The pane never talks to voxl directly and never sees its password. A single-use
display ticket (query ``display_ticket``) admits the first request; a short-lived
HttpOnly cookie then covers ``/client.js``'s socket and the static client. The
proxy injects ``Authorization: Bearer`` toward 127.0.0.1 and strips ``token``
from URLs so the password cannot leak into a logged location bar.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import secrets
import threading
import time
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from hermes_cli.web_server_chat import _ws_request_is_allowed

logger = logging.getLogger(__name__)

router = APIRouter()

PREFIX = "/api/display/voxl"
COOKIE = "display_voxl"
_SESSION_TTL_S = 12 * 3600
_CLOSE_CONTROL_TAKEN = 4000
_CLOSE_DESKTOP_GONE = 4001
_CLOSE_BAD_TICKET = 4401
_CLOSE_NOT_ALLOWED = 4403
_CLEAN_CLOSE = frozenset({1000, 1001})
_LEASE_REFRESH_S = 0.25
_HOP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "authorization",
    "cookie",
})

_lock = threading.Lock()
_sessions: dict[str, tuple[int, dict]] = {}  # cookie -> (expires, info)

_BOOTSTRAP = """<script>
(function(){
  var prefix = "/api/display/voxl";
  var NativeWS = window.WebSocket;
  function rewrite(url) {
    try {
      var u = new URL(url, location.href);
      if (u.pathname === "/ws" || u.pathname === "/ws/") { u.pathname = prefix + "/ws"; }
      return u.toString();
    } catch (e) { return url; }
  }
  window.WebSocket = function(url, protocols) {
    url = rewrite(url);
    var sock = protocols !== undefined ? new NativeWS(url, protocols) : new NativeWS(url);
    sock.addEventListener("close", function(ev) {
      try { parent.postMessage({ type: "hermes-display-ws-close", code: ev.code }, "*"); } catch (e) {}
    });
    return sock;
  };
  window.WebSocket.prototype = NativeWS.prototype;
  window.WebSocket.CONNECTING = NativeWS.CONNECTING;
  window.WebSocket.OPEN = NativeWS.OPEN;
  window.WebSocket.CLOSING = NativeWS.CLOSING;
  window.WebSocket.CLOSED = NativeWS.CLOSED;
  var origFetch = window.fetch;
  window.fetch = function(input, init) {
    if (typeof input === "string" && input.charAt(0) === "/" && input.indexOf(prefix) !== 0) {
      input = prefix + input;
    }
    return origFetch.call(this, input, init);
  };
})();
</script>"""

_ASSET = re.compile(r"""(\b(?:src|href)=["'])/(?!api/display/voxl)""")


def _gc_locked(now: int) -> None:
    dead = [key for key, (exp, _) in _sessions.items() if exp < now]
    for key in dead:
        _sessions.pop(key, None)


def _mint_session(info: dict) -> str:
    token = secrets.token_urlsafe(24)
    with _lock:
        _gc_locked(int(time.time()))
        _sessions[token] = (int(time.time()) + _SESSION_TTL_S, {
            "hermes_home": info.get("hermes_home"),
            "viewer_id": info.get("viewer_id") or info.get("user_id") or "viewer",
        })
    return token


def _session_info(token: str) -> Optional[dict]:
    if not token:
        return None
    now = int(time.time())
    with _lock:
        entry = _sessions.get(token)
        if entry is None or entry[0] < now:
            _sessions.pop(token, None)
            return None
        return dict(entry[1])


def _consume_ticket(request_or_ws) -> Optional[dict]:
    from hermes_cli.dashboard_auth.ws_tickets import TicketInvalid, consume_ticket
    ticket = ""
    if hasattr(request_or_ws, "query_params"):
        ticket = request_or_ws.query_params.get("display_ticket", "")
    if not ticket:
        return None
    try:
        info = consume_ticket(ticket)
    except TicketInvalid:
        return None
    if info.get("provider") != "bot-desktop" or not info.get("hermes_home"):
        return None
    return info


def _admit_http(request: Request) -> Optional[dict]:
    info = _consume_ticket(request)
    if info is not None:
        info["_set_cookie"] = True
        return info
    return _session_info(request.cookies.get(COOKIE, ""))


def _admit_ws(ws: WebSocket) -> Optional[dict]:
    info = _consume_ticket(ws)
    if info is not None:
        return info
    return _session_info(ws.cookies.get(COOKIE, ""))


def _profile_call(profile_home: str, fn, *args, **kwargs):
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override
    token = set_hermes_home_override(profile_home)
    try:
        return fn(*args, **kwargs)
    finally:
        reset_hermes_home_override(token)


def _upstream(info: dict) -> Optional[tuple[str, int, str]]:
    from tools.bot_desktop import voxl as _voxl
    profile_home = str(info["hermes_home"])
    ep = _profile_call(profile_home, _voxl.endpoint)
    password = _profile_call(profile_home, _voxl.load_password)
    if ep is None or not password:
        return None
    return ep[0], ep[1], password


def _drop_secret_query(query: str) -> str:
    pairs = [(k, v) for k, v in parse_qsl(query, keep_blank_values=True)
             if k not in {"display_ticket", "token", "basic-auth-password", "password"}]
    return urlencode(pairs)


def _rewrite_html(body: bytes) -> bytes:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    text = _ASSET.sub(rf"\1{PREFIX}/", text)
    if "<head" in text.lower():
        text = re.sub(r"(<head[^>]*>)", r"\1" + _BOOTSTRAP, text, count=1, flags=re.I)
    else:
        text = _BOOTSTRAP + text
    return text.encode("utf-8")


def _cookie_header(token: str) -> str:
    return f"{COOKIE}={token}; Path={PREFIX}; HttpOnly; SameSite=Lax; Max-Age={_SESSION_TTL_S}"


def _attach_cookie(response: Response, info: dict) -> Response:
    if info.get("_set_cookie"):
        response.headers.append("set-cookie", _cookie_header(_mint_session(info)))
    return response


async def _proxy_http(request: Request, path: str) -> Response:
    info = _admit_http(request)
    if info is None:
        # A dashboard session without a display ticket must not 401 (the inventory
        # sweep treats 401 as "this GET is still gated"). The ticket is still
        # required to reach voxl; 404 keeps the route off the public allowlist.
        if request.query_params.get("display_ticket") or request.cookies.get(COOKIE):
            return Response("display ticket missing, expired or used", status_code=401)
        return Response("display ticket required", status_code=404)
    upstream = _upstream(info)
    if upstream is None:
        return Response("Bot Desktop is not running", status_code=404)
    host, port, password = upstream
    query = _drop_secret_query(urlsplit(str(request.url)).query)
    rel = "/" + path.lstrip("/") if path else "/"
    url = urlunsplit(("http", f"{host}:{port}", rel, query, ""))
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP}
    headers["host"] = f"{host}:{port}"
    headers["authorization"] = f"Bearer {password}"
    headers["origin"] = f"http://{host}:{port}"
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            resp = await client.request(request.method, url, headers=headers, content=body)
    except httpx.HTTPError as exc:
        logger.warning("voxl proxy: upstream error for %s: %s", rel, type(exc).__name__)
        return Response("voxl upstream error", status_code=502)
    skip = _HOP | {"set-cookie", "x-frame-options", "content-security-policy",
                   "content-security-policy-report-only"}
    out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in skip}
    content = resp.content
    ctype = (resp.headers.get("content-type") or "").lower()
    if "text/html" in ctype:
        content = _rewrite_html(content)
        out_headers.pop("content-length", None)
    response = Response(content=content, status_code=resp.status_code, headers=out_headers)
    return _attach_cookie(response, info)


@router.api_route("/api/display/voxl", methods=["GET", "HEAD", "POST", "PUT"])
async def voxl_root(request: Request) -> Response:
    return await _proxy_http(request, "")


@router.api_route("/api/display/voxl/{path:path}", methods=["GET", "HEAD", "POST", "PUT"])
async def voxl_path(request: Request, path: str) -> Response:
    if path == "ws":
        return Response("websocket only", status_code=426)
    return await _proxy_http(request, path)


def _ws_connect(uri: str, headers: list[tuple[str, str]]):
    import websockets
    sig = inspect.signature(websockets.connect)
    if "additional_headers" in sig.parameters:
        return websockets.connect(uri, additional_headers=headers, max_size=64 * 1024 * 1024)
    return websockets.connect(uri, extra_headers=headers, max_size=64 * 1024 * 1024)


def _should_evict(held: dict, lease, viewer_id: str) -> bool:
    from hermes_cli.web_routers.display import _should_evict as _rfb_evict
    return _rfb_evict(held, lease, viewer_id)


@router.websocket("/api/display/voxl/ws")
async def voxl_ws(ws: WebSocket) -> None:
    if not _ws_request_is_allowed(ws):
        await ws.close(code=_CLOSE_NOT_ALLOWED)
        return
    await ws.accept()
    info = _admit_ws(ws)
    if info is None:
        await ws.close(code=_CLOSE_BAD_TICKET, reason="display ticket missing, expired or used")
        return
    upstream = _upstream(info)
    if upstream is None:
        await ws.close(code=_CLOSE_DESKTOP_GONE, reason="Bot Desktop is not running")
        return
    host, port, password = upstream
    from pathlib import Path
    from tools.bot_desktop import lease as _lease
    from tools.bot_desktop.voxl_filter import VoxlClientFilter
    from hermes_constants import hermes_home_key

    profile_home = str(info["hermes_home"])
    profile_key = hermes_home_key(profile_home)
    viewer_id = str(info.get("viewer_id") or info.get("user_id") or "viewer")
    uri = f"ws://{host}:{port}/ws"
    try:
        upstream_ws = await _ws_connect(uri, [("Authorization", f"Bearer {password}")])
    except Exception as exc:
        logger.warning("voxl ws: cannot reach %s:%s: %s", host, port, type(exc).__name__)
        await ws.close(code=_CLOSE_DESKTOP_GONE, reason="Bot Desktop is not running")
        return

    loop = asyncio.get_running_loop()
    evicted = asyncio.Event()
    held = {"ever": _lease.viewer_may_send_input(viewer_id, profile_key=profile_home)}
    allowed = {"input": held["ever"], "at": loop.time()}

    def _refresh_allowed(lease=None) -> None:
        if lease is None:
            lease = _lease.get(profile_key=profile_home)
        allowed["input"] = lease.holder == _lease.HUMAN and lease.viewer_id == viewer_id
        allowed["at"] = loop.time()

    def _may_send_input() -> bool:
        if loop.time() - allowed["at"] > _LEASE_REFRESH_S:
            _refresh_allowed()
        return allowed["input"]

    def _on_lease(key: str, lease) -> None:
        if key != profile_key:
            return
        loop.call_soon_threadsafe(_refresh_allowed, lease)
        if _should_evict(held, lease, viewer_id):
            loop.call_soon_threadsafe(evicted.set)

    unsubscribe = _lease.on_change(_on_lease)
    voxl_filter = VoxlClientFilter(_may_send_input)
    viewer_closed = asyncio.Event()
    activity_file = Path(profile_home) / "bot-desktop" / "activity"
    stamped = {"at": 0.0}

    def _stamp_activity() -> None:
        if loop.time() - stamped["at"] < 60.0:
            return
        stamped["at"] = loop.time()
        try:
            activity_file.touch()
        except OSError:
            pass

    async def up_to_viewer() -> None:
        try:
            async for message in upstream_ws:
                _stamp_activity()
                if isinstance(message, bytes):
                    await ws.send_bytes(message)
                else:
                    await ws.send_text(str(message))
        except Exception:
            return

    async def viewer_to_up() -> None:
        try:
            while True:
                message = await ws.receive()
                if message.get("type") == "websocket.disconnect":
                    if message.get("code") in _CLEAN_CLOSE:
                        viewer_closed.set()
                    return
                data = message.get("bytes")
                text = message.get("text")
                if data is not None:
                    allowed_bin = voxl_filter.binary(data)
                    if allowed_bin is not None:
                        await upstream_ws.send(allowed_bin)
                elif text is not None:
                    allowed_text = voxl_filter.text(text)
                    if allowed_text is not None:
                        await upstream_ws.send(allowed_text)
        except WebSocketDisconnect:
            return

    async def watch_eviction() -> None:
        await evicted.wait()
        await ws.close(code=_CLOSE_CONTROL_TAKEN, reason="control-taken")

    tasks = [
        asyncio.create_task(up_to_viewer()),
        asyncio.create_task(viewer_to_up()),
        asyncio.create_task(watch_eviction()),
    ]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, ConnectionError)):
                logger.debug("voxl ws ended: %r", exc)
    finally:
        unsubscribe()
        try:
            await upstream_ws.close()
        except Exception:
            pass
        if viewer_closed.is_set() and _lease.viewer_may_send_input(viewer_id, profile_key=profile_home):
            _lease.release(viewer_id, profile_key=profile_home)
        try:
            await ws.close()
        except Exception:
            pass


def _reset_for_tests() -> None:
    with _lock:
        _sessions.clear()
