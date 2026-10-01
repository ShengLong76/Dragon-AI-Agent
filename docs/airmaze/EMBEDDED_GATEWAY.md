# Embedded Gateway — First Implementation Slice

Concrete steps to run a Linux Hermes gateway **with Bot Screen packages** on UltraDragon via Docker Desktop, and point the Windows agent desktop client at `127.0.0.1`.

Template only. No API keys or tokens belong in this file or in compose checked into the package.

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| Docker Desktop | Linux engine (WSL2 backend). Confirm whale icon → Settings → General → “Use the WSL 2 based engine”. |
| Image pull | First run needs registry access to Docker Hub (`nousresearch/hermes-agent`, optionally `hermes-sandbox`). |
| RAM | ≥ 8 GB free recommended for comfortable headed-browser takeover; 4 GB can run desktop alone. |
| agent desktop client | Windows client; Remote gateway → localhost. |

---

## Preferred image

Use a **desktop-suffixed** gateway tag so TigerVNC + Xfce are already present (no `apt-get` inside an unprivileged container):

```text
nousresearch/hermes-agent:latest-desktop
```

Version-pinned example (replace when you pin a release):

```text
nousresearch/hermes-agent:v*-desktop
```

**Pull required** before first `up` if the tag is not cached:

```powershell
docker pull nousresearch/hermes-agent:latest-desktop
```

Optional sandbox (screen inside terminal backend):

```text
nousresearch/hermes-sandbox:desktop
```

---

## Ports (localhost)

| Host port | Container | Purpose | Desktop Remote? |
|-----------|-----------|---------|-----------------|
| `8650` | `8650` → loopback `hermes serve` `:8651` | **Desktop-compatible** JSON-RPC/WS (`/api/health`, `/api/ws?token=`, `/api/display/ws`) | **Yes — this is the Bot Screen URL** |
| `8642` | `8642` | OpenAI-compatible API (`gateway run`: `/health`, `/v1/*`, Bearer `API_SERVER_KEY`) | **No** — no `/api/ws` |
| `9119` | `9119` | Web dashboard (password / cookie). Has some `/api/*` but is **gated**; Desktop token-mode WS is refused on a non-loopback bind ([upstream #106685](https://github.com/NousResearch/hermes-agent/issues/106685)) | **No** |

Bot Screen **does not** open a separate VNC TCP port. The Desktop pane calls `display.observe` on authenticated `/api/ws`, then splices RFB over `/api/display/ws`. Binding published ports to `127.0.0.1` keeps the API off the LAN.

### Why `:8642` / `:9119` cannot be the Desktop Remote URL

UltraDragon retest (2026-09-29) proved:

1. Desktop Remote **token** mode probes `/api/health` (then `/api/status`), sends `X-Hermes-Session-Token`, and opens `ws:///api/ws?token=`. Extra `Authorization` / `Cookie` headers are forbidden by the connection schema.
2. Embedded `:8642` only has `/health` + `Authorization: Bearer` — `/api/health` and `/api/ws` are **404**.
3. Embedded `:9119` can look “ready” after a translator maps the token header to a dashboard Bearer, but `/api/ws?token=` is still refused on a gated (0.0.0.0) dashboard. Upstream tracks this as #106685.
4. A fake nginx `/api/health` is not enough — without a real `hermes serve` WebSocket + display ticket, boot dies with **WebSocket error before open**.

This package therefore runs a second process, `hermes serve --host 127.0.0.1 --port 8651` (loopback so token auth stays on), and a tiny TCP proxy `0.0.0.0:8650 → 127.0.0.1:8651` so Docker Desktop can publish it. No Electron rebuild.

If a future `-desktop` image drops `hermes serve` / `hermes dashboard` entirely, this adapter cannot invent `/api/ws` — that is an upstream-image follow-up (fork `hermes-agent`, spike `serve` in the image). The sidecar script already falls back to `dashboard --no-open` on the same loopback port when `serve` is missing.

---

## UltraDragon re-smoke (Bot Screen)

After installing this revision (or copying `docker-compose.embedded.yml` + `scripts/airmaze/*` into `%LOCALAPPDATA%\DragonAIAgent\`):

1. Docker Desktop running (WSL2 engine). Do **not** expect Local / This device Screen to work.
2. Open **Dragon AI Agent** (Start Menu shortcut). Wait until the client window appears. Launch log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`.
3. Confirm containers: `docker ps --filter name=hermes-airmaze` shows `hermes-airmaze-gw` healthy, plus `hermes-airmaze-desktop` and `hermes-airmaze-desktop-proxy`.
4. From Windows (PowerShell), **no real key in the command line beyond the compose placeholder**:

```powershell
$h = @{ "X-Hermes-Session-Token" = "dragon-local" }
Invoke-WebRequest http://127.0.0.1:8650/api/health -Headers $h -UseBasicParsing
```

5. Settings → Gateways: **Embedded Linux** is primary, URL `http://127.0.0.1:8650`. If an older **Embedded Linux** still says `:8642`, Make primary after the launcher rewrite, or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\DragonAIAgent\scripts\airmaze\Set-EmbeddedDesktopConnection.ps1"
```

6. Restart Dragon AI Agent if it booted before the rewrite. Bots roster should show the **Embedded Linux** source (not only This device).
7. Right-click **Personal Assistant** (Remote) → **Open Screen** → **Start**. Expect live Xfce/noVNC, not “No bot screen on this host”.
8. **Take over** / **Hand back**. Inside the container, `hermes computer-use screen status` should stay **running** DISPLAY `:20`.

**Fail closed (do not document as pass):** boot overlay “WebSocket error before open”, “Hermes backend did not become ready: 404”, roster stuck Unavailable, or Screen on **This device**. Those mean Desktop is still on Local or still pointed at `:8642`/`:9119`.

---

## Option A — `docker run` (one-shot)

```powershell
# Persist Hermes home on the Windows side
$HermesData = Join-Path $env:USERPROFILE ".hermes-airmaze-embedded"
New-Item -ItemType Directory -Force -Path $HermesData | Out-Null

docker pull nousresearch/hermes-agent:latest-desktop

docker run -d `
  --name hermes-airmaze-gw `
  --restart unless-stopped `
  -v "${HermesData}:/opt/data" `
  -p 127.0.0.1:8642:8642 `
  -p 127.0.0.1:9119:9119 `
  -e HERMES_DASHBOARD=1 `
  -e HERMES_DASHBOARD_HOST=0.0.0.0 `
  -e HERMES_DASHBOARD_PORT=9119 `
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME=dragon `
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=dragon-local `
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET=dragon-local-dashboard-session-secret `
  -e API_SERVER_ENABLED=true `
  -e API_SERVER_HOST=0.0.0.0 `
  -e API_SERVER_KEY=dragon-local `
  nousresearch/hermes-agent:latest-desktop `
  gateway run
```

Notes:

- Option A starts **only** `gateway run` + dashboard. It is **not** enough for Desktop Bot Screen (no loopback `hermes serve` on `:8650`). Use Option B (compose) for Screen.
- Map secrets via the volume (`/opt/data` ↔ `%USERPROFILE%\.hermes-airmaze-embedded`), not via this package.
- The OpenAI-compatible API (`8642`) defaults to `127.0.0.1` **inside** the container. Without `API_SERVER_ENABLED=true` and `API_SERVER_HOST=0.0.0.0`, Windows `127.0.0.1:8642` is docker-proxy only and HTTP connection-closes. Host publish stays `127.0.0.1`. Local compose uses `API_SERVER_KEY=dragon-local` (min 8 chars).
- Dashboard on a non-loopback bind (`0.0.0.0` inside the container, required for `-p 9119:9119`) needs `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` + `_PASSWORD` (not `_USER`). Wrong names → “no auth providers” crash-loop.

Stop / remove:

```powershell
docker stop hermes-airmaze-gw
docker rm hermes-airmaze-gw
```

---

## Option B — Compose (recommended)

From this package directory:

```powershell
docker compose -f docker-compose.embedded.yml pull
docker compose -f docker-compose.embedded.yml up -d
docker compose -f docker-compose.embedded.yml ps
docker compose -f docker-compose.embedded.yml logs -f --tail=100
```

Compose file: `docker-compose.embedded.yml` (same ports/image intent as Option A). Override data dir with env `HERMES_EMBEDDED_DATA` if desired.

---

## Config sketch (gateway / profile)

Inside the container Hermes home (`/opt/data` or profile subtree), align Bot Screen for a headless Linux gateway:

```yaml
# Conceptual sketch — merge into the profile config Hermes actually uses.
# Do not paste secrets here.

bot_desktop:
  geometry: "1440x900"
  auto_start: true          # optional: start on first computer_use / headed browser
  min_free_memory_mb: 1536
  idle_stop_minutes: 30
  placement: auto

browser:
  headed: true              # bot browsing visible on the screen

# Optional: place screen + shell inside sandbox desktop image
# terminal:
#   backend: docker
#   docker_image: nousresearch/hermes-sandbox:desktop
```

After the container is up, from a shell **inside** the gateway container (or via Desktop Screen pane):

```bash
hermes computer-use screen status
hermes computer-use screen start
```

With `:*-desktop` images, packages should already be present; `install` should report ready.

---

## agent desktop client (Windows) → localhost

`start-embedded.ps1` (the **Dragon AI Agent** shortcut) now:

1. Brings compose up (gateway + `hermes-airmaze-desktop` + proxy).
2. Mirrors `%LOCALAPPDATA%\hermes\profiles\*` into `%USERPROFILE%\.hermes-airmaze-embedded\profiles\` so Remote sees the same bots.
3. Waits for `http://127.0.0.1:8650/api/health` with `X-Hermes-Session-Token: dragon-local`.
4. Upserts `%APPDATA%\Hermes\connections.json` — Remote **Embedded Linux** → `http://127.0.0.1:8650`, primary (rewrites a leftover `:8642` Remote from the UltraDragon retest).

Manual wiring (if you skip the shortcut):

1. Open Dragon AI Agent.
2. Settings → Gateways → **Add connection** → **Remote gateway**:
   - URL: `http://127.0.0.1:8650`
   - Auth: **Session token** = `dragon-local` (compose placeholder; same value as `HERMES_DASHBOARD_SESSION_TOKEN`)
3. **Make primary**. Restart the client if boot still uses **This device**.
4. Open **Screen** on a Remote bot (not a Windows “This device” bot).
5. **Start screen** if idle; confirm live preview; test **Take over** / **Hand back**.

**This device / Local** still shows *“No bot screen on this host / Bot screens run on Linux gateway hosts.”* That is upstream-by-design on Windows. Screen only works on the Embedded Linux Remote.

If the Screen pane says packages missing, you are on a slim tag — switch compose/run to `:latest-desktop` (or exec install as root per upstream docs).

---

## Smoke checklist

- [ ] `docker version` shows Server (Linux engine)
- [ ] `docker pull nousresearch/hermes-agent:latest-desktop` succeeds
- [ ] **Open Dragon AI Agent** (Desktop / Start Menu / double-click `Start-DragonAI.vbs`): **no PowerShell console** (shortcut target is `wscript.exe`, not Hide-ConsoleWindow after a flash). Desktop client window only. Docker engine stopped → launcher starts **Docker Desktop in the tray** (no Containers dashboard) and waits; MessageBox only if it stays down. Dashboard `:9119` must **not** auto-open. A healthy `docker compose up` must not exit 1 from CLI stderr. Log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`.
- [ ] From Windows: `http://127.0.0.1:8642/` does not connection-close (Bearer `dragon-local` if asked). `http://127.0.0.1:9119/` serves the dashboard login (user `dragon`).
- [ ] Desktop serve: `http://127.0.0.1:8650/api/health` returns 200 with header `X-Hermes-Session-Token: dragon-local`. `GET /api/ws` without Upgrade may 404 — that is normal; the client uses a WebSocket upgrade + `?token=`.
- [ ] Offline wiring check (no secrets): `python3 scripts/airmaze/Test-LaunchSmoke.py` (includes `Test-DesktopServeAdapter.py`) or `powershell -File scripts\airmaze\start-embedded.ps1 -Smoke`
- [ ] After a normal Dragon AI Agent start, `%APPDATA%\Hermes\connections.json` has Remote `embedded-linux` → `http://127.0.0.1:8650` as primary (token value is the placeholder, not a production secret)
- [ ] Screen pane on the **Embedded Linux** Remote offers Start / live preview (not “No bot screen on this host” — that message is **This device** on Windows)
- [ ] `hermes computer-use screen status` (in container) → installed / running
- [ ] Headed browser login survives handoff (shared browser profile)

---

## Out of scope for this slice

- microVM packaging
- Proxmox wiring (alternate path only)
- Public image rebuilds / CI for Dragon AI Agent
- Pushing the local fork anywhere

---

## Docker Desktop UI (Dragon AI Agent installer)

The Dragon AI Agent Windows installer configures Docker Desktop to **start minimized to the system tray** and sets `openUIOnStartupDisabled` (and related keys) in `%APPDATA%\Docker\settings.json` / `settings-store.json` so the dashboard window does not pop on first run. The engine still starts; open the dashboard from the tray when needed.
