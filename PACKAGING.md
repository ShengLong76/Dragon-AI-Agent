# Dragon AI Agent packaging notes

**Product version:** 0.1.0  
**Product name:** Dragon AI Agent  
**Installer exe:** `DragonAIAgentSetup.exe`  
**Built on:** Cos box (Linux amd64)  
**Date:** 2026-09-28 (America/New_York)

## Toolchain

| Tool | Version / note |
|------|----------------|
| Go | `go1.24.4 linux/amd64` (cross-compile `GOOS=windows GOARCH=amd64`) |
| go-winres | Embed Windows icon/version resources into the exe (`.syso` beside `build-exe.go`) |
| Zip | Python 3 `zipfile` |
| Logo | `branding/dragon-ai-agent-logo.png` (+ `.ico` generated with Pillow) |

## Build commands

```bash
cd /workspace/airmaze-agent-dist/repo/installer
# Optional: regenerate icon resources
# go-winres simply --icon winres/icon.ico --product-name "Dragon AI Agent" ...
GOOS=windows GOARCH=amd64 go build -o /workspace/airmaze-agent-dist/release/DragonAIAgentSetup.exe .
# Console subsystem (default) — omit -H windowsgui so users see installer logs.
```

If `go-winres` / `.syso` is skipped, the exe may keep the default Go icon; the PNG/ICO still ship beside the exe and are used for desktop shortcut `IconLocation`. Documented here intentionally.

Release zip layout:

```text
Dragon-AI-Agent-v0.1.0-windows/
  DragonAIAgentSetup.exe
  dragon-ai-agent-logo.png
  dragon-ai-agent-logo.ico
  payload/
    install.ps1
    docker-compose.embedded.yml
    README.md
    vendor/docker/Docker Desktop Installer.exe   (staged; see below)
    bot-groups/...
    scripts/airmaze/...
    templates/profiles/personal-assistant/...
    branding/...
```

## Docker Desktop installer (package slot)

A clean Windows PC should get Docker from **Dragon AI Agent Setup**, not from docker.com first.

Stage the official installer into the zip (gitignores the exe; ~500MB):

```bash
python3 installer/stage-docker-desktop.py
```

Setup order when Docker is absent: packaged `vendor/docker/Docker Desktop Installer.exe` → Setup-owned cache/download → quiet `install --quiet --accept-license` (separate PowerShell arguments; `RunAs` if not admin; exit `0` or `3010` is success) → tray-only settings → session `PATH` + engine start → compose if `docker info` works. Half-installed (exe without CLI) takes the same quiet-install path. Setup does **not** open the Docker download page. Product launch still only starts an already-installed engine (`docs/airmaze/DOCKER_LAUNCH.md`). Design: `docs/airmaze/DOCKER_INSTALL.md`.

## Docker Desktop: tray-only (no dashboard)

Installer patches:

- `%APPDATA%\Docker\settings.json`
- `%APPDATA%\Docker\settings-store.json`

Setting keys include `openUIOnStartupDisabled` = true, plus `startMinimized` / `minimizeToTray` / `openAtLogin`. The PowerShell `$patch` hashtable may contain the camelCase key only (hashtables are case-insensitive). Docker is started via `com.docker.service` when possible, then `Docker Desktop.exe` minimized — **not** a force-open dashboard flag.

## Bot groups

`bot-groups/` plus `bot_groups.py` / `Select-BotGroup.ps1` are copied into `%LOCALAPPDATA%\DragonAIAgent\`. The dropdown lists groups from this GitHub repo. Bots are applied to `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` for the agent desktop Bot Screen picker (upstream path, not renamed).

## Outputs

`/workspace/airmaze-agent-dist/release/Dragon-AI-Agent-v0.1.0-windows.zip` and unpacked folder beside it. Also `dragon-ai-agent-logo.png` at release root for GitHub assets. Source tree zip: `airmaze-agent-source.zip`.

## Launch UI

The **Dragon AI Agent** shortcut targets `wscript.exe` + `scripts/airmaze/Start-DragonAI.vbs` (no console flash). The VBS sets `HERMES_DESKTOP_USER_DATA_DIR` to `%LOCALAPPDATA%\DragonAIAgent\electron-userdata` and `start-embedded.ps1` copies/provisions a private client at `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked`. That host starts Docker Desktop in the **tray** when `docker info` fails (already running is a no-op), starts the gateway **and** Desktop serve proxy, wires Remote `connections.json` in Dragon userdata (standalone Hermes primary stays local), launches the **private** desktop client (Hermes default loading — no Waiting for gateway / Setup / Close status window), and waits for host HTTP on `127.0.0.1:8642` and `127.0.0.1:8650/api/health`. It does **not** open `:9119` or the Docker dashboard. Branding is refused outside `DragonAIAgent`. Missing Docker after a wait, or a missing client, is a MessageBox. `start-embedded.ps1` remains for debug. See `docs/airmaze/PRIVATE_DESKTOP.md`, `docs/airmaze/BRANDING.md` and `docs/airmaze/DOCKER_LAUNCH.md`. Verify with `python3 scripts/airmaze/Test-LaunchSmoke.py` (no secrets).

Gateway compose wraps the official image entrypoint with `scripts/airmaze/start-gateway.sh` so a dirty root-owned `/opt/data/logs/agent.log` (or a fresh `compose up`) does not leave `hermes-airmaze-gw` unhealthy. The wrapper heals `logs/` + `backups/` then exec's the image dispatcher (`/init` stays in the chain). Offline: `sh scripts/airmaze/start-gateway.sh --self-test`. UltraDragon dirty-log steps: `docs/airmaze/EMBEDDED_GATEWAY.md`.

## Limitations

- Quiet Docker/WSL install may still need reboot or UAC/UI clicks. Setup still owns the Docker installer; a reboot is a continuation, not a hand-off to docker.com.
- Agent desktop client is not bundled. Install/start copy standalone `win-unpacked` into `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked` and overlay chrome only there (see `docs/airmaze/PRIVATE_DESKTOP.md` and `docs/airmaze/BRANDING.md`). Dashboard `:9119` is optional (`start-embedded.ps1 -OpenDashboard`), not a Start Menu shortcut.
- Dashboard basic auth defaults remain the compose local-only values (see `THIRD_PARTY_NOTICES.md` / `EMBEDDED_GATEWAY.md`).
