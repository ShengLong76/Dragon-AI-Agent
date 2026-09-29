#!/bin/sh
# Run the TCP proxy with whichever Python the official image actually ships.
set -eu
SCRIPT="${DESKTOP_PROXY_SCRIPT:-/opt/dragon/desktop-loopback-proxy.py}"
LISTEN="${DESKTOP_PROXY_LISTEN:-0.0.0.0:8650}"
UPSTREAM="${DESKTOP_PROXY_UPSTREAM:-127.0.0.1:8651}"

if [ -x /opt/hermes/.venv/bin/python ]; then
  PY=/opt/hermes/.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[dragon-desktop-proxy] python not found" >&2
  exit 1
fi

exec "$PY" "$SCRIPT" --listen "$LISTEN" --upstream "$UPSTREAM"
