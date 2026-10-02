#!/usr/bin/env python3
"""Upsert the Embedded Linux Remote entry in Desktop connections.json.

Desktop token mode must target the Desktop-compatible serve proxy
(http://127.0.0.1:8650), not the OpenAI API on :8642.

No real API keys: default token is the compose placeholder ``dragon-local``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from private_desktop import (
    USER_DATA_ENV,
    dragon_connections_path,
    is_standalone_hermes_connections,
    should_make_embedded_primary,
    standalone_hermes_connections_path,
)

DEFAULT_ID = "embedded-linux"
DEFAULT_LABEL = "Embedded Linux"
DEFAULT_URL = "http://127.0.0.1:8650"
DEFAULT_TOKEN = "dragon-local"
LOCAL_ID = "local"

# Prior UltraDragon Remote attempts pointed at the OpenAI API. Rewrite those.
LEGACY_API_URLS = frozenset(
    {
        "http://127.0.0.1:8642",
        "http://localhost:8642",
        "http://127.0.0.1:8642/",
        "http://localhost:8642/",
    }
)


def default_connections_path() -> Path:
    """Dragon userdata when HERMES_DESKTOP_USER_DATA_DIR / install root exist.

    Standalone %APPDATA%\\Hermes\\connections.json is never the Dragon default.
    """
    if os.environ.get(USER_DATA_ENV):
        return dragon_connections_path()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "DragonAIAgent" / "electron-userdata" / "connections.json"
    return standalone_hermes_connections_path()


def merge_registry(
    existing: dict[str, Any] | None,
    *,
    connection_id: str = DEFAULT_ID,
    label: str = DEFAULT_LABEL,
    url: str = DEFAULT_URL,
    token: str = DEFAULT_TOKEN,
    make_primary: bool = True,
) -> dict[str, Any]:
    """Return an updated v2 registry. Never drops unrelated connections."""
    data = dict(existing or {})
    data.setdefault("version", 2)
    connections = list(data.get("connections") or [])
    if not any(isinstance(c, dict) and c.get("id") == LOCAL_ID for c in connections):
        connections.insert(0, {"id": LOCAL_ID, "kind": "local", "label": "This device"})

    remote = {
        "id": connection_id,
        "kind": "remote",
        "label": label,
        "url": url.rstrip("/") if url.endswith("/") and url.count("/") == 3 else url,
        "authMode": "token",
        "token": {"encoding": "plain", "value": token},
    }

    replaced = False
    out: list[Any] = []
    for row in connections:
        if not isinstance(row, dict):
            out.append(row)
            continue
        rid = str(row.get("id") or "")
        rurl = str(row.get("url") or "").rstrip("/")
        if rid == connection_id or (
            row.get("kind") == "remote" and rurl in {u.rstrip("/") for u in LEGACY_API_URLS}
        ):
            merged = dict(row)
            merged.update(remote)
            out.append(merged)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(remote)

    data["connections"] = out
    primary = str(data.get("primary") or "")
    if make_primary:
        if primary in ("", LOCAL_ID, connection_id) or any(
            isinstance(c, dict)
            and c.get("id") == primary
            and str(c.get("url") or "").rstrip("/") in {u.rstrip("/") for u in LEGACY_API_URLS}
            for c in out
        ):
            data["primary"] = connection_id
            data["lastUsed"] = connection_id
            data["launchMode"] = data.get("launchMode") or "primary"
    return data


def write_registry(path: Path, registry: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    return path


def load_registry(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def apply(
    path: Path | None = None,
    *,
    url: str = DEFAULT_URL,
    token: str = DEFAULT_TOKEN,
    make_primary: bool | None = None,
) -> dict[str, Any]:
    dest = path or default_connections_path()
    primary = make_primary
    if primary is None:
        # Standalone Hermes connections.json primary stays local.
        primary = should_make_embedded_primary(dest)
        if is_standalone_hermes_connections(dest):
            primary = False
    updated = merge_registry(load_registry(dest), url=url, token=token, make_primary=primary)
    write_registry(dest, updated)
    return {"path": str(dest), "primary": updated.get("primary"), "url": url}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--path",
        default="",
        help="connections.json path (default HERMES_DESKTOP_USER_DATA_DIR / DragonAIAgent\\electron-userdata)",
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--no-primary", action="store_true")
    parser.add_argument("--primary", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args(argv)
    dest = Path(args.path) if args.path else default_connections_path()
    # NoPrimary: standalone Hermes connections.json primary stays local.
    make_primary: bool | None
    if args.no_primary:
        make_primary = False
    elif args.primary:
        make_primary = True
    else:
        make_primary = None
    if args.print_only:
        updated = merge_registry(
            load_registry(dest) if dest.is_file() else None,
            url=args.url,
            token=args.token,
            make_primary=False if make_primary is False else (
                True if make_primary is True else should_make_embedded_primary(dest)
            ),
        )
        print(json.dumps(updated, indent=2))
        return 0
    result = apply(dest, url=args.url, token=args.token, make_primary=make_primary)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
