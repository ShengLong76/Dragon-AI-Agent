# Upstream Bot Screen Notes

Studied from public docs and GitHub paths (remote reads only — no local clone on Cos).  
Primary doc: https://hermes-agent.nousresearch.com/docs/user-guide/features/bot-screen

---

## Critical constraint for Windows / Dragon AI Agent

> The gateway host runs Linux. macOS and Windows hosts already have a real display; the pane is not offered there.

Bot Screen is **Linux-gateway-only today**. UltraDragon must embed a Linux engine (Docker Desktop preferred; microVM later) so the Windows agent desktop client talks to a **localhost Linux gateway** that actually runs TigerVNC + Xfce. See `ARCHITECTURE.md`.

WSL2 is a supported Linux host for Bot Screen, with a known `/tmp/.X11-unix` remount quirk; Dragon AI Agent Slice 1 prefers a container with packages pre-baked (`*-desktop` / `hermes-sandbox:desktop`) instead of relying on host package installs.

---

## What Bot Screen is

- Per-profile headless Xfce desktop driven by the bot’s `computer_use` and headed browser.
- TigerVNC `Xvnc` = X server + RFB on a **Unix socket only** (mode `0600`); no VNC password, no TCP VNC port.
- Hermes Desktop embeds noVNC; gateway issues a single-use `display_ticket` and splices RFB over `/api/display/ws`.
- Control **lease** gates human vs bot input at RFB byte level and refuses bot tools with `human_has_control` during takeover.
- Screens are work surfaces, not OS security boundaries (shared gateway user / threat model in upstream docs).

---

## Images and packages

| Image | Role |
|-------|------|
| `nousresearch/hermes-agent:latest` / `:v*` | Slim gateway (no desktop packages) |
| `nousresearch/hermes-agent:latest-desktop` / `:v*-desktop` | Gateway **with** TigerVNC + Xfce (+ distro chromium) baked in (~930 MB apt layer on Debian) |
| `nousresearch/hermes-sandbox:desktop` | Default **sandbox** image for docker/ssh/singularity backends when screen is placed inside the sandbox |

Build flag for custom gateway images: `docker build --build-arg HERMES_BOT_DESKTOP=1 …`

Debian/Ubuntu package set (also what `hermes computer-use screen install` targets):  
`tigervnc-standalone-server xfce4-panel xfwm4 xfdesktop4 xfce4-settings xfce4-terminal dbus-x11 x11-xserver-utils x11-utils xauth fonts-dejavu-core` (+ related).

Memory guidance (official image measurements): gateway ~300 MB idle; Xvnc+Xfce ~+220 MB; headed Chromium 0.5–1 GB. Default refuse-to-start if free RAM &lt; `bot_desktop.min_free_memory_mb` (1536).

---

## Source map (`main` as of study)

### `tools/bot_desktop/`

| File | Role (summary) |
|------|----------------|
| `runtime.py` | Start/stop/status of the profile screen; DISPLAY / XAUTHORITY binding; host support checks; orchestrates launcher |
| `launcher.sh` | Component-wise Xfce + Xvnc bring-up (no `xfce4-session`); seeds dock; private D-Bus |
| `placement.py` | `bot_desktop.placement`: `auto` / `gateway` / `terminal` vs `terminal.backend` |
| `install.py` | Package-manager install path used by CLI and Desktop “Install on host” |
| `sandbox_host.py` | Screen inside docker/ssh/singularity sandbox; markers, re-attach after gateway restart |
| `browser.py` | Headed browser / profile path alignment with dock Browser icon |
| `lease.py` | Human/bot control lease file semantics |
| `rfb_filter.py` | Drop input from viewers without lease |
| `resources.py` | Memory / idle-stop resource policy |
| `thumbnail.py` | Preview grabs for Desktop pane |
| `__init__.py` | Package exports |

### CLI

| Path | Role |
|------|------|
| `hermes_cli/subcommands/computer_use_screen.py` | `hermes computer-use screen {status,start,stop,install}` |

### Gateway HTTP / WebSocket

| Path | Role |
|------|------|
| `hermes_cli/web_routers/display.py` | Display observe tickets + `/api/display/ws` RFB splice for noVNC |

### Docker

| Path | Role |
|------|------|
| `docker/sandbox-desktop.Dockerfile` | Builds `nousresearch/hermes-sandbox:desktop` (nikolaik base + TigerVNC/Xfce + Chromium + cua-driver + agent-browser) |
| `docker/sandbox-desktop-smoke.sh` | Smoke checks for the sandbox desktop image |
| Gateway Dockerfile (repo root) | `HERMES_BOT_DESKTOP=1` opt-in for `*-desktop` gateway tags |

---

## Placement quick table

| `terminal.backend` | `placement: auto` | Screen lives |
|--------------------|-------------------|--------------|
| `local` | gateway host | Same machine as gateway |
| `docker` / `ssh` / `singularity` | inside sandbox | Needs desktop-capable sandbox image |
| `modal` / `daytona` / `vercel_sandbox` | refused | Opt in `placement: gateway` explicitly if forcing host screen |

---

## Config knobs (upstream)

```yaml
bot_desktop:
  geometry: "1440x900"
  auto_start: false
  min_free_memory_mb: 1536
  idle_stop_minutes: 30
  placement: auto   # auto | terminal | gateway
```

State: `<HERMES_HOME>/bot-desktop/` per profile (RFB socket, Xauthority, launcher log, xfconf, lease).

CLI ops:

```bash
hermes computer-use screen status
hermes computer-use screen start
hermes computer-use screen stop [--force]
hermes computer-use screen install [-y]
```

---

## Desktop Remote protocol vs `gateway run`

The Windows client’s Remote **token** mode talks to `hermes serve` / `hermes dashboard` (`hermes_cli/web_server.py`), **not** the OpenAI API (`hermes gateway` / `api_server`):

| Call | `hermes serve` (loopback) | `gateway run` `:8642` | `hermes dashboard` on `0.0.0.0` |
|------|---------------------------|------------------------|----------------------------------|
| Ready | `/api/health` or `/api/status` | `/health` only | `/api/health` (gated) |
| REST auth | `X-Hermes-Session-Token` = `HERMES_DASHBOARD_SESSION_TOKEN` | `Authorization: Bearer` `API_SERVER_KEY` | Cookie / dashboard Bearer |
| Control WS | `/api/ws?token=` | **404** | Ticket-only; `?token=` refused ([#106685](https://github.com/NousResearch/hermes-agent/issues/106685)) |
| Bot Screen | `display.observe` then `/api/display/ws?display_ticket=` | **404** | Same routes, but Desktop cannot mint the ticket in token mode |

A non-loopback bind always engages the June 2026 auth gate. Docker publish requires `0.0.0.0` inside the container, so this package binds **serve to 127.0.0.1:8651** and proxies **0.0.0.0:8650**. That is the smallest packaging fix that does not rebuild Electron or fork the image.

If the official `-desktop` image later removes `serve`/`dashboard`/`web_server`, packaging cannot add `/api/ws`. Follow-up: `hermes-agent` image fork — add a supervised `serve --host 127.0.0.1` (or accept `?token=` on gated WS, #106685) and republish a Dragon-tagged `-desktop` image.

## Implication for AirMaze fork work

On UltraDragon after bootstrap:

1. Prefer **no** early patches to `runtime.py` / `display.py` — embed a Linux gateway instead.
2. Desktop Remote must target the packaged `:8650` serve proxy, not `:8642`.
3. Re-read these paths after `git pull` on UltraDragon; upstream moves quickly.

## Bot group overlay (do not wipe on sync)

Bot groups live beside this desktop-agent base, not inside Bot Screen:

- `bot-groups/` — GitHub catalog
- `scripts/airmaze/bot_groups.py`, `Select-BotGroup.ps1`, `Test-BotGroups.py`
- `docs/airmaze/BOT_GROUPS.md`

A sync of the upstream desktop / hermes-agent tree does not contain those paths. Keep them. Deploy still writes `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` so the picker and Bot Screen keep working.

License: MIT, Copyright (c) 2025 Nous Research.
