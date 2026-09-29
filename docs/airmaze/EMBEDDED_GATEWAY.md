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

| Host port | Container | Purpose |
|-----------|-----------|---------|
| `8642` | `8642` | Gateway / OpenAI-compatible API (`gateway run`) |
| `9119` | `9119` | Web dashboard (when `HERMES_DASHBOARD=1`) |

Bot Screen **does not** open a separate VNC TCP port. The Desktop pane uses the gateway’s authenticated WebSocket (`/api/display/ws`) after a single-use display ticket. Binding published ports to `127.0.0.1` keeps the API off the LAN.

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

1. Install / open agent desktop client on UltraDragon.
2. Add or edit a **Remote** gateway connection:
   - Host: `127.0.0.1` (or `localhost`)
   - Port: gateway port you published (`8642` unless changed)
   - Auth: whatever token/key that gateway profile expects (from your local Hermes setup — not stored in this package)
3. Select the Dragon AI Agent / embedded profile.
4. Open **Screen** (Bots → bot → Screen, or right-click → Open Screen).
5. **Start screen** if idle; confirm live preview; test **Take over** / **Hand back**.

If the Screen pane says packages missing, you are on a slim tag — switch compose/run to `:latest-desktop` (or exec install as root per upstream docs).

---

## Smoke checklist

- [ ] `docker version` shows Server (Linux engine)
- [ ] `docker pull nousresearch/hermes-agent:latest-desktop` succeeds
- [ ] **Open Dragon AI Agent** (Desktop / Start Menu / double-click `Start-DragonAI.vbs`): **no PowerShell console** (shortcut target is `wscript.exe`, not Hide-ConsoleWindow after a flash). Desktop client window only. Docker engine stopped → MessageBox + exit 1 (does **not** auto-start Desktop unless `-StartDocker`). Dashboard `:9119` must **not** auto-open. A healthy `docker compose up` must not exit 1 from CLI stderr. Log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`.
- [ ] From Windows: `http://127.0.0.1:8642/` does not connection-close (Bearer `dragon-local` if asked). `http://127.0.0.1:9119/` serves the dashboard login (user `dragon`).
- [ ] Offline wiring check (no secrets): `python3 scripts/airmaze/Test-LaunchSmoke.py` or `powershell -File scripts\airmaze\start-embedded.ps1 -Smoke`
- [ ] `curl http://127.0.0.1:9119/` or gateway health from Desktop connects
- [ ] Screen pane offers Start (not “not offered on this host” — that message is for when gateway **is** Windows; embedded Linux must be the gateway)
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
