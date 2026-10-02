#!/bin/sh
# Start a Desktop-compatible hermes backend on loopback inside the embedded
# Linux container. Do NOT bind 0.0.0.0 here: a non-loopback bind engages the
# dashboard password/OAuth gate, and Desktop token-mode /api/ws?token= is then
# refused (NousResearch/hermes-agent#106685). Publish via desktop-loopback-proxy.
#
# This script is the sidecar entrypoint (skips s6 so we do not start a second
# dashboard/API on the shared network namespace).
set -eu

export HOME="${HOME:-/opt/data}"
export HERMES_HOME="${HERMES_HOME:-/opt/data}"
export HERMES_DASHBOARD_SESSION_TOKEN="${HERMES_DASHBOARD_SESSION_TOKEN:-dragon-local}"
# Shared volume with the gateway: heal root-owned logs before dropping to hermes.
if [ -f /opt/dragon/start-gateway.sh ]; then
  /bin/sh /opt/dragon/start-gateway.sh --heal-only || true
fi
# Never start the OpenAI API or the public dashboard from this process.
export API_SERVER_ENABLED="${API_SERVER_ENABLED:-false}"
export HERMES_DASHBOARD="${HERMES_DASHBOARD:-0}"

HOST="${DESKTOP_SERVE_HOST:-127.0.0.1}"
PORT="${DESKTOP_SERVE_PORT:-8651}"

if [ -x /opt/hermes/.venv/bin/hermes ]; then
  HERMES_BIN=/opt/hermes/.venv/bin/hermes
elif command -v hermes >/dev/null 2>&1; then
  HERMES_BIN=hermes
else
  echo "[dragon-desktop-serve] hermes binary not found" >&2
  exit 1
fi

run() {
  if [ "$(id -u)" = 0 ] && command -v s6-setuidgid >/dev/null 2>&1; then
    exec s6-setuidgid hermes "$@"
  fi
  exec "$@"
}

# Give volume / stage2 a moment on a cold compose up.
i=0
while [ "$i" -lt 20 ]; do
  if [ -d "$HERMES_HOME" ]; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

echo "[dragon-desktop-serve] $HERMES_BIN serve --host $HOST --port $PORT (token via HERMES_DASHBOARD_SESSION_TOKEN)" >&2

if "$HERMES_BIN" serve --help >/dev/null 2>&1; then
  run "$HERMES_BIN" serve --host "$HOST" --port "$PORT"
fi

echo "[dragon-desktop-serve] 'hermes serve' is not available; falling back to dashboard --no-open (same web_server)" >&2
run "$HERMES_BIN" dashboard --host "$HOST" --port "$PORT" --no-open
