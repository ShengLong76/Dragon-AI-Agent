# Launch-time Docker Desktop start (invisible / headless)

Short design. James: opening Dragon AI Agent must start the Docker engine when it is down, with **no sign of Docker** — no dashboard, no onboarding, no tray icon, no docker.com page.

## Why

The product shortcut used to **fail-close** unless `-StartDocker` was passed, then later started Docker Desktop **in the tray**. James does not want a whale icon, Containers window, or onboarding during Setup or a later launch. Setup owns install (`docs/airmaze/DOCKER_INSTALL.md`). Launch only starts an already-installed engine.

## Existing path (extend, do not fork)

| Piece | Role |
|-------|------|
| `start-embedded.ps1` `Test-DockerEngine` | `docker info` via `Invoke-NativeDocker` |
| `Start-DockerIfNeeded` | Headless start: settings, `com.docker.service`, `com.docker.backend.exe`, last-resort Hidden `Docker Desktop.exe`, hide/stop the Electron UI |
| `install.ps1` / `DragonAIAgentSetup.ps1` `Set-DockerHeadlessSettings` (`Set-DockerTrayOnlySettings` alias) | Patch `%APPDATA%\Docker\settings.json` (camelCase) + `settings-store.json` (PascalCase) (`openUIOnStartupDisabled`, `displayedOnboarding`, `disableTrayIcon`) |
| `Hide-DockerDesktopUi` | Hide Docker Desktop windows; drop the tray process after `docker info` is up |
| `Start-DragonAI.vbs` | Windowless product host; does **not** open `:9119` |

Do not add a second starter. Call the existing function on every normal launch.

PowerShell hashtables are **case-insensitive**. The `$patch` may list camelCase `openUIOnStartupDisabled` only — a PascalCase duplicate is a parse error and the shortcut dies before `Hermes.exe`. Write PascalCase keys in a **separate** hashtable for `settings-store.json`. Do not assign `$Home` / `$home` (automatic `$HOME` is read-only). Design: `docs/airmaze/WINDOWS_LAUNCH_PARSE.md`.

## Behavior

1. **Engine already up** (`docker info` ok) → no-op besides hiding any leftover Docker UI. Do not relaunch Docker Desktop.
2. **Engine down** → re-apply headless settings, start `com.docker.service` and `com.docker.backend.exe` Hidden / CreateNoWindow. Last resort: `Docker Desktop.exe` Hidden, then `Hide-DockerDesktopUi`. Never `Start-Process` the Docker dashboard URL. Never open `:9119`. No tray icon.
3. **Wait** with a bounded retry (about 3 minutes, a few seconds between `docker info` probes). Progress is logged to `%LOCALAPPDATA%\DragonAIAgent\launch.log` (“Starting background engine…”). Do **not** show the WinForms Waiting for gateway / Setup / Close status window — Hermes desktop is the loading UX.
4. **Still down** → MessageBox that the background engine did not start. Do not tell the user to install Docker or use the tray.
5. **Docker Desktop.exe missing** → fail closed. Do not download the installer from the launch path (Setup owns that).

`-StartDocker` stays as a no-op alias so old docs/scripts do not break. Default launch no longer requires it.

## Out of scope

- Installing Docker from the product shortcut (that is Setup: `docs/airmaze/DOCKER_INSTALL.md`)
- Opening the Docker dashboard or Dragon `:9119` dashboard
- Live UltraDragon smoke in CI
- Merging PR #10
