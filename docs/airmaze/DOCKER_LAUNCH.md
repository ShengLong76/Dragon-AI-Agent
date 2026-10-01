# Launch-time Docker Desktop start (tray-only)

Short design. James: opening Dragon AI Agent must start Docker Desktop when the engine is down, without opening the Containers / dashboard window.

## Why

The product shortcut currently **fail-closes** unless `-StartDocker` is passed. `Start-DragonAI.vbs` does not pass that switch, so a cold boot (Docker tray not running) shows a MessageBox instead of bringing the gateway up. James wants: check → start if needed → continue.

## Existing path (extend, do not fork)

| Piece | Role |
|-------|------|
| `start-embedded.ps1` `Test-DockerEngine` | `docker info` via `Invoke-NativeDocker` |
| `Start-DockerIfNeeded` | Find `Docker Desktop.exe`, start Hidden/Minimized, wait ~3 min |
| `install.ps1` / `DragonAIAgentSetup.ps1` `Set-DockerTrayOnlySettings` | Patch `%APPDATA%\Docker\settings.json` + `settings-store.json` (`openUIOnStartupDisabled`, `startMinimized`, `minimizeToTray`) |
| `Start-DragonAI.vbs` | Windowless product host; does **not** open `:9119` |

Do not add a second starter. Call the existing function on every normal launch.

## Behavior

1. **Engine already up** (`docker info` ok) → no-op. Do not relaunch Docker Desktop.
2. **Engine down** → re-apply tray-only settings, start `Docker Desktop.exe` Hidden (fallback Minimized). Never `Start-Process` the Docker dashboard URL. Never open `:9119`.
3. **Wait** with a bounded retry (about 3 minutes, a few seconds between `docker info` probes). Status form stays “Starting Docker Desktop (system tray)…”.
4. **Still down** → friendly MessageBox: start Docker from the tray, then open Dragon AI Agent again. Only then fail closed.
5. **Docker Desktop.exe missing** → same class of error (install Docker, then retry). Do not download the installer from the launch path.

`-StartDocker` stays as a no-op alias so old docs/scripts do not break. Default launch no longer requires it.

## Out of scope

- Installing Docker from the product shortcut
- Opening the Docker dashboard or Dragon `:9119` dashboard
- Live UltraDragon smoke in CI
- Merging PR #10
