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
    profiles/...
    scripts/airmaze/...
    templates/profiles/personal-assistant/...
    branding/...
```

## Docker Desktop: tray-only (no dashboard)

Installer patches:

- `%APPDATA%\Docker\settings.json`
- `%APPDATA%\Docker\settings-store.json`

Setting keys include `openUIOnStartupDisabled` / `OpenUIOnStartupDisabled` = true, plus `startMinimized` / `minimizeToTray` / `openAtLogin`. Docker is started via `com.docker.service` when possible, then `Docker Desktop.exe` minimized — **not** a force-open dashboard flag.

## Profiles

Built-in catalog + import/select scripts are copied into `%LOCALAPPDATA%\DragonAIAgent\`. Bots are applied to `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` for the agent desktop Bot Screen picker (internal path).

## Outputs

`/workspace/airmaze-agent-dist/release/Dragon-AI-Agent-v0.1.0-windows.zip` and unpacked folder beside it. Also `dragon-ai-agent-logo.png` at release root for GitHub assets. Source tree zip: `airmaze-agent-source.zip`.

## Launch UI

The **Dragon AI Agent** shortcut targets `wscript.exe` + `scripts/airmaze/Start-DragonAI.vbs` (no console flash). That host requires Docker to already be running (fail-closed; `-StartDocker` to opt in), starts the gateway **and** Desktop serve proxy, waits for host HTTP on `127.0.0.1:8642` and `127.0.0.1:8650/api/health`, wires Remote `connections.json`, then launches the desktop client. It does **not** open `:9119`. Missing Docker or client is a MessageBox. `start-embedded.ps1` remains for debug. See `docs/airmaze/BRANDING.md`. Verify with `python3 scripts/airmaze/Test-LaunchSmoke.py` (no secrets).

## Limitations

- Quiet Docker/WSL install may still need reboot or UAC/UI clicks.
- Agent desktop client is not bundled; the packaged visible UI on open is the on-disk desktop client (`Hermes.exe`) after a launch-time overlay of unpacked renderer product chrome (see `docs/airmaze/BRANDING.md`). Dashboard `:9119` is optional (Start Menu), not the primary launch surface.
- Dashboard basic auth defaults remain the compose local-only values (see `THIRD_PARTY_NOTICES.md` / `EMBEDDED_GATEWAY.md`).
