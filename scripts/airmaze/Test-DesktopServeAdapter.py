#!/usr/bin/env python3
"""Offline contract + unit tests for the Desktop↔embedded Bot Screen adapter.

No secrets. No Docker required. Safe on Linux CI and a Windows checkout.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "airmaze"
COMPOSE = ROOT / "docker-compose.embedded.yml"
LAUNCHER = SCRIPTS / "start-embedded.ps1"
PROXY = SCRIPTS / "desktop-loopback-proxy.py"
SERVE_SH = SCRIPTS / "start-desktop-serve.sh"
GATEWAY_SH = SCRIPTS / "start-gateway.sh"
CONN_PY = SCRIPTS / "embedded_desktop_connection.py"
CONN_PS1 = SCRIPTS / "Set-EmbeddedDesktopConnection.ps1"
DOCS = (
    ROOT / "docs" / "airmaze" / "EMBEDDED_GATEWAY.md",
    ROOT / "docs" / "airmaze" / "ARCHITECTURE.md",
    ROOT / "docs" / "airmaze" / "UPSTREAM_NOTES.md",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing {path}")
    return path.read_text(encoding="utf-8")


def test_proxy_self() -> None:
    proc = subprocess.run(
        [sys.executable, str(PROXY), "--self-test"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        fail(f"proxy --self-test exited {proc.returncode}")


def test_connection_merge() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import embedded_desktop_connection as edc  # noqa: E402

    fresh = edc.merge_registry(None)
    ids = [c["id"] for c in fresh["connections"]]
    if ids[0] != "local" or "embedded-linux" not in ids:
        fail(f"fresh registry ids={ids}")
    remote = next(c for c in fresh["connections"] if c["id"] == "embedded-linux")
    if remote["url"] != "http://127.0.0.1:8650":
        fail(f"remote url {remote['url']}")
    if remote["token"]["value"] != "dragon-local":
        fail("token must stay the compose placeholder")
    if fresh["primary"] != "embedded-linux":
        fail(f"primary {fresh['primary']}")
    standalone_kept = edc.merge_registry(
        {"version": 2, "primary": "local", "connections": [{"id": "local", "kind": "local", "label": "This device"}]},
        make_primary=False,
    )
    if standalone_kept["primary"] != "local":
        fail("standalone connections primary must stay local")

    broken = {
        "version": 2,
        "primary": "embedded-linux",
        "connections": [
            {"id": "local", "kind": "local", "label": "This device"},
            {
                "id": "embedded-linux",
                "kind": "remote",
                "label": "Embedded Linux",
                "url": "http://127.0.0.1:8642",
                "authMode": "token",
                "token": {"encoding": "plain", "value": "dragon-local"},
            },
        ],
    }
    fixed = edc.merge_registry(broken)
    remotes = [c for c in fixed["connections"] if c.get("kind") == "remote"]
    if len(remotes) != 1 or remotes[0]["url"] != "http://127.0.0.1:8650":
        fail(f"legacy :8642 was not rewritten: {remotes}")

    other = {
        "version": 2,
        "primary": "office-gw",
        "connections": [
            {
                "id": "office-gw",
                "kind": "remote",
                "label": "Office",
                "url": "https://office.example",
                "authMode": "token",
                "token": {"encoding": "plain", "value": "keep-me"},
            }
        ],
    }
    merged = edc.merge_registry(other)
    if merged["primary"] != "office-gw":
        fail("must not steal an unrelated primary")
    office = next(c for c in merged["connections"] if c["id"] == "office-gw")
    if office["token"]["value"] != "keep-me":
        fail("must not rewrite an unrelated token")
    print("OK  connections merge")


def test_compose_and_scripts() -> None:
    compose = read(COMPOSE)
    for token in (
        "127.0.0.1:8650:8650",
        "hermes-airmaze-desktop",
        "start-desktop-serve.sh",
        "start-desktop-proxy.sh",
        "start-gateway.sh",
        "desktop-loopback-proxy.py",
        "HERMES_DASHBOARD_SESSION_TOKEN",
        'HERMES_DASHBOARD_SESSION_TOKEN: "dragon-local"',
        "network_mode: service:hermes-gateway",
        "DESKTOP_SERVE_PORT",
    ):
        if token not in compose:
            fail(f"compose missing {token!r}")
    if 'command: ["gateway", "run"]' not in compose:
        fail("gateway service must still run 'gateway run'")
    if "start-gateway.sh" not in compose or "/opt/dragon/start-gateway.sh" not in compose:
        fail("gateway must wrap official entrypoint with start-gateway.sh (heal root-owned logs)")
    if "\n    user:" in compose:
        fail("compose must not pin user: (stage2/heal need root, then official drop to hermes)")
    if "API_SERVER_KEY: " in compose and "dragon-local" not in compose:
        fail("compose lost local-only key placeholder")

    gateway = read(GATEWAY_SH)
    for token in (
        "entrypoint-dispatch.sh",
        "/init",
        "s6-setuidgid",
        "--heal-only",
        "--self-test",
        "logs/agent.log",
        "backups",
        "refusing to start gateway as root",
    ):
        if token not in gateway:
            fail(f"start-gateway.sh missing {token!r}")
    proc = subprocess.run(
        ["/bin/sh", str(GATEWAY_SH), "--self-test"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        fail(f"start-gateway.sh --self-test exited {proc.returncode}")
    if "OK  start-gateway.sh --self-test" not in proc.stdout:
        fail("start-gateway.sh --self-test did not print OK")

    serve = read(SERVE_SH)
    if "127.0.0.1" not in serve or "8651" not in serve:
        fail("start-desktop-serve.sh must bind loopback 8651")
    if "0.0.0.0" in serve and "Do NOT bind 0.0.0.0" not in serve:
        fail("serve script must not bind all interfaces")
    if "106685" not in serve:
        fail("serve script must cite upstream token/WS issue 106685")
    if "start-gateway.sh --heal-only" not in serve:
        fail("desktop serve must heal shared /opt/data logs before dropping to hermes")

    launcher = read(LAUNCHER)
    for token in (
        "8650",
        "Set-EmbeddedDesktopConnection",
        "/api/health",
        "X-Hermes-Session-Token",
        "Embedded Linux",
    ):
        if token not in launcher:
            fail(f"start-embedded.ps1 missing {token!r}")

    if not CONN_PS1.is_file():
        fail(f"missing {CONN_PS1}")
    conn_ps = read(CONN_PS1)
    conn_py = read(CONN_PY)
    for token in ("HERMES_DESKTOP_USER_DATA_DIR", "electron-userdata", "NoPrimary"):
        if token not in conn_ps or token not in conn_py:
            fail(f"connection helpers must mention {token}")
    print("OK  compose + launcher contract")


def test_docs_do_not_lie() -> None:
    body = "\n".join(read(p) for p in DOCS)
    if "8650" not in body:
        fail("docs must name the Desktop serve proxy port 8650")
    if "106685" not in body:
        fail("docs must cite upstream #106685 (token WS vs gated bind)")
    if "start-gateway.sh" not in body or "agent.log" not in body:
        fail("docs must name start-gateway.sh and the dirty root-owned agent.log re-smoke")
    # The old "Remote → 8642 then Open Screen" path is the UltraDragon FAIL.
    if "Remote gateway → `127.0.0.1:8642`" in body or "Port: gateway port you published (`8642`" in body:
        fail("docs still tell operators to point Desktop Remote at :8642 for Screen")
    print("OK  docs name the working Desktop URL")


def main() -> int:
    test_proxy_self()
    test_connection_merge()
    test_compose_and_scripts()
    test_docs_do_not_lie()
    print("SMOKE OK: Desktop serve adapter contract holds (no secrets).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
