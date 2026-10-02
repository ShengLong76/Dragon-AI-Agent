#!/bin/sh
# Dragon AI Agent — gateway entrypoint wrapper.
#
# Official nousresearch/hermes-agent stage2 only recursively chowns
# $HERMES_HOME/logs when the *top-level* data dir is not hermes-owned.
# A warm bind mount (Windows Docker Desktop → /opt/data) can already be
# hermes-owned while logs/agent.log and logs/errors.log stay root:root.
# The supervised process then hits:
#   PermissionError: [Errno 13] Permission denied: '/opt/data/logs/agent.log'
# and hermes-airmaze-gw never becomes healthy.
#
# This wrapper always heals logs/ and backups/ (the dirs the UltraDragon
# ops workaround chowned), then exec's the official dispatcher so s6 /
# stage2 / s6-setuidgid hermes stay in the chain. Do not run gateway as root.
#
# Modes:
#   (default)   heal, then hand off "$@" (compose: gateway run)
#   --heal-only heal and exit 0
#   --self-test offline heal contract (no Docker, no secrets)
set -eu

HERMES_HOME="${HERMES_HOME:-/opt/data}"

path_has_symlink_component() {
  path="$1"
  root="${2:-$HERMES_HOME}"
  while [ -n "$path" ] && [ "$path" != "/" ]; do
    if [ -L "$path" ]; then
      return 0
    fi
    if [ "$path" = "$root" ]; then
      break
    fi
    parent="$(dirname "$path")"
    if [ "$parent" = "$path" ]; then
      break
    fi
    path="$parent"
  done
  return 1
}

heal_owner() {
  if [ -n "${DRAGON_HEAL_OWNER:-}" ] && id "$DRAGON_HEAL_OWNER" >/dev/null 2>&1; then
    printf '%s\n' "$DRAGON_HEAL_OWNER"
    return
  fi
  if id hermes >/dev/null 2>&1; then
    printf '%s\n' hermes
    return
  fi
  id -un
}

runtime_can_write() {
  target="$1"
  owner="$2"
  probe="$target/.dragon-write-probe"
  if command -v s6-setuidgid >/dev/null 2>&1 && [ "$owner" = "hermes" ]; then
    s6-setuidgid hermes sh -c "echo w > \"$probe\"" >/dev/null 2>&1 || return 1
  elif command -v su >/dev/null 2>&1; then
    su -s /bin/sh "$owner" -c "echo w > \"$probe\"" >/dev/null 2>&1 || return 1
  else
    return 0
  fi
  rm -f "$probe" 2>/dev/null || true
  return 0
}

ensure_runtime_writable() {
  target="$1"
  owner="$2"
  if [ "$(id -u)" != 0 ] || [ ! -d "$target" ]; then
    return 0
  fi
  if ! id "$owner" >/dev/null 2>&1; then
    return 0
  fi
  if runtime_can_write "$target" "$owner"; then
    return 0
  fi
  # Bind mounts that ignore chown still need the hermes process to append
  # agent.log. Open the targeted tree only (not the whole volume).
  echo "[dragon-gateway] $owner cannot write $target after chown; opening a+rwX" >&2
  chmod -R a+rwX "$target" 2>/dev/null || true
}

heal_tree() {
  target="$1"
  if [ -z "$target" ]; then
    return 0
  fi
  if [ -e "$HERMES_HOME" ] && path_has_symlink_component "$HERMES_HOME" "$HERMES_HOME"; then
    echo "[dragon-gateway] refusing heal through symlink $HERMES_HOME" >&2
    return 0
  fi
  if [ -e "$target" ] && path_has_symlink_component "$target" "$HERMES_HOME"; then
    echo "[dragon-gateway] refusing heal through symlink $target" >&2
    return 0
  fi
  if [ ! -e "$target" ]; then
    mkdir -p "$target" || return 0
  fi
  owner="$(heal_owner)"
  if [ "$(id -u)" = 0 ]; then
    chown -R "${owner}:${owner}" "$target" 2>/dev/null || \
      echo "[dragon-gateway] warning: chown $target failed (rootless or bind mount?)" >&2
  fi
  chmod -R u+rwX "$target" 2>/dev/null || true
  ensure_runtime_writable "$target" "$owner"
}

heal_data_volume() {
  if [ ! -e "$HERMES_HOME" ]; then
    mkdir -p "$HERMES_HOME" || return 0
  fi
  if path_has_symlink_component "$HERMES_HOME" "$HERMES_HOME"; then
    echo "[dragon-gateway] refusing heal through symlink $HERMES_HOME" >&2
    return 0
  fi
  # Same trees the UltraDragon workaround repaired. Targeted — do not
  # chown -R the whole bind mount (host files may live beside Hermes state).
  heal_tree "$HERMES_HOME/logs"
  heal_tree "$HERMES_HOME/backups"
}

hand_off() {
  # Test-only override so CI can prove heal-then-exec without the official image.
  if [ -n "${DRAGON_HANDOFF_DISPATCH:-}" ] && [ -x "$DRAGON_HANDOFF_DISPATCH" ]; then
    exec "$DRAGON_HANDOFF_DISPATCH" "$@"
  fi
  # Keep /init (or the official dispatcher that exec's it) in the chain.
  if [ -x /opt/hermes/docker/entrypoint-dispatch.sh ]; then
    exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
  fi
  if [ -x /init ] && [ -x /opt/hermes/docker/main-wrapper.sh ]; then
    exec /init /opt/hermes/docker/main-wrapper.sh "$@"
  fi
  if [ -x /opt/hermes/docker/entrypoint.sh ]; then
    exec /opt/hermes/docker/entrypoint.sh "$@"
  fi
  echo "[dragon-gateway] official image entrypoint not found; refusing to start gateway as root" >&2
  exit 1
}

self_test() {
  tmp="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf \"$tmp\"" EXIT
  HERMES_HOME="$tmp/data"
  mkdir -p "$HERMES_HOME/logs" "$HERMES_HOME/backups"
  printf 'stale\n' > "$HERMES_HOME/logs/agent.log"
  printf 'stale\n' > "$HERMES_HOME/logs/errors.log"
  chmod 000 "$HERMES_HOME/logs/agent.log" "$HERMES_HOME/logs/errors.log"
  heal_data_volume
  printf 'healed\n' >> "$HERMES_HOME/logs/agent.log" || {
    echo "FAIL: could not append to healed agent.log" >&2
    exit 1
  }
  printf 'healed\n' >> "$HERMES_HOME/logs/errors.log" || {
    echo "FAIL: could not append to healed errors.log" >&2
    exit 1
  }
  if [ ! -d "$HERMES_HOME/backups" ]; then
    echo "FAIL: backups dir missing after heal" >&2
    exit 1
  fi

  # Fresh empty home: wrapper must create writable logs/.
  fresh="$tmp/fresh"
  HERMES_HOME="$fresh"
  heal_data_volume
  printf 'fresh\n' >> "$fresh/logs/agent.log" || {
    echo "FAIL: fresh compose home could not create agent.log" >&2
    exit 1
  }

  # Symlink refuse: do not chown/chmod through logs → other tree.
  evil="$tmp/evil"
  mkdir -p "$evil"
  printf 'secret\n' > "$evil/owned"
  chmod 644 "$evil/owned"
  HERMES_HOME="$tmp/sym"
  mkdir -p "$HERMES_HOME"
  ln -s "$evil" "$HERMES_HOME/logs"
  heal_data_volume
  if [ ! -L "$HERMES_HOME/logs" ]; then
    echo "FAIL: symlink logs/ was replaced" >&2
    exit 1
  fi
  if [ ! -f "$evil/owned" ] || [ ! -r "$evil/owned" ]; then
    echo "FAIL: symlink target was disturbed" >&2
    exit 1
  fi
  echo "OK  start-gateway.sh --self-test"
}

mode="${1:-}"
case "$mode" in
  --self-test)
    self_test
    exit 0
    ;;
  --heal-only)
    heal_data_volume
    exit 0
    ;;
esac

accept_grok_voice_mode() {
  # Settings → Voice conversation mode writes voice.voice_chat_mode: grok-live
  # beside chained|gpt-live. Fail open if the image file is missing.
  patch="/opt/dragon/patch_grok_voice_mode.py"
  if [ -f "$patch" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$patch" --apply >/dev/null 2>&1 || \
      echo "[dragon-gateway] warning: could not accept grok-live in methods_config_set.py" >&2
  fi
}

heal_data_volume
accept_grok_voice_mode
hand_off "$@"
