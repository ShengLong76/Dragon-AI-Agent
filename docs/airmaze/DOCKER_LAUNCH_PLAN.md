# Plan — start Docker engine on launch (invisible / headless)

Small plan after `docs/airmaze/DOCKER_LAUNCH.md`. Tests first. Extend `start-embedded.ps1`.

## In scope

1. Flip the launch gate: when `docker info` fails, always call `Start-DockerIfNeeded` (not only `-StartDocker`).
2. Before starting anything, patch headless Docker settings (same keys as the installer): no dashboard, no onboarding, no tray.
3. Prefer `com.docker.service` + `com.docker.backend.exe` Hidden. Last-resort Hidden `Docker Desktop.exe`, then hide/stop the Electron UI so there is no tray icon.
4. Update VBS comment + launch-plan smoke string (auto-start is default, invisible).
5. Docs: README, `PACKAGING.md`, `EMBEDDED_GATEWAY.md`, `CHANGELOG.md`.
6. Flip `Test-LaunchSmoke.py` so a tray announcement is no longer required.

## Tests first

- Launcher calls `Start-DockerIfNeeded` when the engine is down without gating on `if ($StartDocker)`.
- `Test-DockerEngine` / already-running returns before `Start-Process`.
- Headless keys (`openUIOnStartupDisabled`, `Set-DockerHeadlessSettings`, `Hide-DockerDesktopUi`) live in the launcher.
- No Docker dashboard URL start; `:9119` still requires `-OpenDashboard`.
- VBS still hidden / no `-StartDocker` required.
- `-Smoke` plan text says auto-start invisible / headless Docker, not fail-closed, not tray.

## Out of scope

- New VBS/exe entrypoint
- Docker installer download on every open
- Merging PR #10
