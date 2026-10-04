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

Release is **one file**: `DragonAIAgentSetup.exe`. The payload is embedded (not a zip with a second exe beside it).

```text
DragonAIAgentSetup.exe   (self-extracting; embeds install.ps1 + desktop + scripts)
```

Build:

```bash
python3 installer/pack-payload.py /tmp/DragonAIAgentSetup.exe
```

## Docker Desktop installer (package slot)

A clean Windows PC should get Docker from **Dragon AI Agent Setup**, not from docker.com first.

Stage the official installer into the zip (gitignores the exe; ~500MB):

```bash
python3 installer/stage-docker-desktop.py
```

Setup order when Docker is absent: packaged `vendor/docker/Docker Desktop Installer.exe` → Setup-owned cache/download → quiet `install --quiet --accept-license --always-run-service` (separate PowerShell arguments; Hidden; `RunAs` if not admin; exit `0` or `3010` is success) → headless settings (no dashboard / onboarding / tray) → session `PATH` + invisible engine start → compose if `docker info` works. Half-installed (exe without CLI) takes the same quiet-install path. Setup does **not** open the Docker download page and does **not** tell the user to install Docker. Product launch still only starts an already-installed engine (`docs/airmaze/DOCKER_LAUNCH.md`). Design: `docs/airmaze/DOCKER_INSTALL.md`.

## Docker Desktop: invisible / headless (no dashboard, no tray)

Installer patches:

- `%APPDATA%\Docker\settings.json` (camelCase `$patch` only)
- `%APPDATA%\Docker\settings-store.json` (separate PascalCase table)

Setting keys include `openUIOnStartupDisabled` = true, `displayedOnboarding` = true, `disableTrayIcon` = true. The PowerShell `$patch` hashtable may contain the camelCase key only (hashtables are case-insensitive). Docker is started via `com.docker.service` and `com.docker.backend.exe` Hidden when possible; `Docker Desktop.exe` Hidden is last resort and is then hidden/stopped so there is **no tray** icon.

## Bot groups

`bot-groups/` plus `bot_groups.py` / `Select-BotGroup.ps1` are copied into `%LOCALAPPDATA%\DragonAIAgent\`. The dropdown lists groups from this GitHub repo. Bots are applied to `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` for the agent desktop Bot Screen picker (upstream path, not renamed).

## Outputs

`/workspace/airmaze-agent-dist/release/Dragon-AI-Agent-v0.1.0-windows.zip` and unpacked folder beside it. Also `dragon-ai-agent-logo.png` at release root for GitHub assets. Source tree zip: `airmaze-agent-source.zip`.

## Launch UI

The **Dragon AI Agent** shortcut targets `wscript.exe` + `scripts/airmaze/Start-DragonAI.vbs` (no console flash). The VBS sets user data to `%LOCALAPPDATA%\DragonAIAgent\electron-userdata` and `start-embedded.ps1` launches packaged `DragonAIAgent.exe` at `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked`. Setup copies that exe from the Dragon package. It does not search for a Hermes install. That host starts the Docker engine **invisibly** when `docker info` fails (already running is a no-op; no tray icon), starts the gateway **and** Desktop serve proxy, wires Remote `connections.json` in Dragon userdata (standalone Hermes primary stays local), launches **Dragon AI Agent**, and waits for host HTTP on `127.0.0.1:8642` and `127.0.0.1:8650/api/health`. It does **not** open `:9119` or the Docker dashboard. Branding is refused outside `DragonAIAgent`. Missing Docker after a wait, or a missing package desktop, is a MessageBox. `start-embedded.ps1` remains for debug. See `docs/airmaze/PRIVATE_DESKTOP.md`, `docs/airmaze/BRANDING.md` and `docs/airmaze/DOCKER_LAUNCH.md`. Verify with `python3 scripts/airmaze/Test-DragonDesktop.py` and `python3 scripts/airmaze/Test-LaunchSmoke.py` (no secrets).

```bash
cd desktop
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -ldflags="-H windowsgui -s -w" -o win-unpacked/DragonAIAgent.exe .
```

Gateway compose wraps the official image entrypoint with `scripts/airmaze/start-gateway.sh` so a dirty root-owned `/opt/data/logs/agent.log` (or a fresh `compose up`) does not leave `hermes-airmaze-gw` unhealthy. The wrapper heals `logs/` + `backups/` then exec's the image dispatcher (`/init` stays in the chain). Offline: `sh scripts/airmaze/start-gateway.sh --self-test`. UltraDragon dirty-log steps: `docs/airmaze/EMBEDDED_GATEWAY.md`.

## Limitations

- Quiet Docker/WSL install may still need reboot or UAC/UI clicks. Setup still owns the Docker installer; a reboot is a continuation, not a hand-off to docker.com.
- Agent desktop client **is** bundled as `desktop/win-unpacked/DragonAIAgent.exe`. Install/start copy that Dragon package tree into `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked`. They do not search a Hermes install (see `docs/airmaze/PRIVATE_DESKTOP.md` and `docs/airmaze/BRANDING.md`). Dashboard `:9119` is optional (`start-embedded.ps1 -OpenDashboard`), not a Start Menu shortcut.
- Dashboard basic auth defaults remain the compose local-only values (see `THIRD_PARTY_NOTICES.md` / `EMBEDDED_GATEWAY.md`).
