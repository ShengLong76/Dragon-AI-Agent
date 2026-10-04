#!/bin/sh
# Start the Hermes browser web UI (hermes dashboard) on loopback inside the
# embedded Linux container. This is the page DragonAIAgent.exe must load.
#
# hermes serve on :8651/:8650 is the headless Bot Screen API. GET / there
# returns "web UI disabled - use hermes dashboard". Do not point the window
# at that surface. Bind loopback here so the dashboard password/OAuth gate
# does not engage; publish via the 8660 TCP proxy.
set -eu

export HOME="${HOME:-/opt/data}"
export HERMES_HOME="${HERMES_HOME:-/opt/data}"
export HERMES_DASHBOARD_SESSION_TOKEN="${HERMES_DASHBOARD_SESSION_TOKEN:-dragon-local}"
if [ -f /opt/dragon/start-gateway.sh ]; then
  /bin/sh /opt/dragon/start-gateway.sh --heal-only || true
fi
# This sidecar is the browser UI only. Do not start a second OpenAI API.
export API_SERVER_ENABLED="${API_SERVER_ENABLED:-false}"

HOST="${DESKTOP_UI_HOST:-127.0.0.1}"
PORT="${DESKTOP_UI_PORT:-8652}"

if [ -x /opt/hermes/.venv/bin/hermes ]; then
  HERMES_BIN=/opt/hermes/.venv/bin/hermes
elif command -v hermes >/dev/null 2>&1; then
  HERMES_BIN=hermes
else
  echo "[dragon-desktop-ui] hermes binary not found" >&2
  exit 1
fi

run() {
  if [ "$(id -u)" = "0" ] && command -v s6-setuidgid >/dev/null 2>&1; then
    exec s6-setuidgid hermes "$@"
  fi
  exec "$@"
}

i=0
while [ "$i" -lt 20 ]; do
  if [ -d "$HERMES_HOME" ]; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

echo "[dragon-desktop-ui] $HERMES_BIN dashboard --host $HOST --port $PORT --no-open (browser web UI for DragonAIAgent.exe)" >&2
run "$HERMES_BIN" dashboard --host "$HOST" --port "$PORT" --no-open
