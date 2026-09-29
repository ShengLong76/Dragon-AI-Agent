#!/usr/bin/env python3
"""Transparent TCP proxy: publish a loopback hermes serve on 0.0.0.0.

Desktop Remote token mode only authenticates (X-Hermes-Session-Token and
``/api/ws?token=``) when the *serve process* bound loopback. Docker publish
requires something listening on 0.0.0.0 inside the container. This proxy
splices bytes so WebSocket upgrades pass through unchanged.

No secrets. Safe to run as a compose sidecar on the gateway network namespace.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

DEFAULT_LISTEN = "0.0.0.0:8650"
DEFAULT_UPSTREAM = "127.0.0.1:8651"


def parse_hostport(value: str) -> tuple[str, int]:
    text = (value or "").strip()
    if not text or ":" not in text:
        raise ValueError(f"expected host:port, got {value!r}")
    host, port_s = text.rsplit(":", 1)
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    port = int(port_s)
    if not 1 <= port <= 65535:
        raise ValueError(f"invalid port in {value!r}")
    return host, port


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await reader.read(64 * 1024)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _open_upstream(host: str, port: int, timeout: float) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    last: Exception | None = None
    deadline = time.monotonic() + timeout
    while True:
        try:
            return await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2.0)
        except Exception as exc:
            last = exc
            if time.monotonic() >= deadline:
                raise
            await asyncio.sleep(0.2)
    raise last or ConnectionError("upstream connect failed")


async def _handle(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
    connect_timeout: float,
) -> None:
    peer = client_writer.get_extra_info("peername")
    try:
        up_reader, up_writer = await _open_upstream(upstream_host, upstream_port, connect_timeout)
    except Exception as exc:
        print(f"[desktop-proxy] upstream {upstream_host}:{upstream_port} failed for {peer}: {exc}", flush=True)
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass
        return
    # Drain both directions to completion. Cancelling the peer pipe on the
    # first EOF drops HTTP responses (and broke the self-test).
    results = await asyncio.gather(
        _pipe(client_reader, up_writer),
        _pipe(up_reader, client_writer),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            print(f"[desktop-proxy] pipe error: {result!r}", flush=True)


async def serve(listen: str, upstream: str, connect_timeout: float = 30.0) -> None:
    listen_host, listen_port = parse_hostport(listen)
    up_host, up_port = parse_hostport(upstream)

    async def on_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await _handle(reader, writer, up_host, up_port, connect_timeout)

    server = await asyncio.start_server(on_client, listen_host, listen_port)
    sockets = server.sockets or []
    bound = [s.getsockname() for s in sockets]
    print(f"[desktop-proxy] listening {bound} -> {up_host}:{up_port}", flush=True)
    async with server:
        await server.serve_forever()


async def _self_test() -> int:
    """Echo splice + a fake HTTP Upgrade line — no Docker, no secrets."""
    echo = await asyncio.start_server(
        lambda r, w: _pipe(r, w),
        "127.0.0.1",
        0,
    )
    echo_port = echo.sockets[0].getsockname()[1]

    proxy = await asyncio.start_server(
        lambda r, w: _handle(r, w, "127.0.0.1", echo_port, 5.0),
        "127.0.0.1",
        0,
    )
    proxy_port = proxy.sockets[0].getsockname()[1]

    payload = (
        b"GET /api/ws?token=dragon-local HTTP/1.1\r\n"
        b"Host: 127.0.0.1\r\n"
        b"Upgrade: websocket\r\n"
        b"Connection: Upgrade\r\n"
        b"\r\n"
        b"\x81\x05hello"
    )
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
        writer.write(payload)
        await writer.drain()
        echoed = await asyncio.wait_for(reader.readexactly(len(payload)), timeout=3.0)
        writer.close()
        writer.close()
        await writer.wait_closed()
    finally:
        echo.close()
        proxy.close()
        await echo.wait_closed()
        await proxy.wait_closed()

    if echoed != payload:
        print(f"FAIL proxy self-test: got {echoed!r}", file=sys.stderr)
        return 1
    print("OK  desktop-loopback-proxy self-test (TCP + Upgrade bytes)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--listen", default=DEFAULT_LISTEN, help="bind host:port (default 0.0.0.0:8650)")
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM, help="loopback serve host:port")
    parser.add_argument("--connect-timeout", type=float, default=30.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return asyncio.run(_self_test())
    try:
        asyncio.run(serve(args.listen, args.upstream, args.connect_timeout))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
