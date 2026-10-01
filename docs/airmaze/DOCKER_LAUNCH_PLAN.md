# Plan — start Docker Desktop on launch (tray-only)

Small plan after `docs/airmaze/DOCKER_LAUNCH.md`. Tests first. Extend `start-embedded.ps1`.

## In scope

1. Flip the launch gate: when `docker info` fails, always call `Start-DockerIfNeeded` (not only `-StartDocker`).
2. Before starting the exe, patch tray-only Docker settings (same keys as the installer).
3. Keep Hidden/Minimized start, 3-minute retry, fail only after timeout.
4. Update VBS comment + launch-plan smoke string (auto-start is default).
5. Docs: README, `PACKAGING.md`, `EMBEDDED_GATEWAY.md`, `CHANGELOG.md`.
6. Flip `Test-LaunchSmoke.py` so fail-closed-without-flag is no longer required.

## Tests first

- Launcher calls `Start-DockerIfNeeded` when the engine is down without gating on `if ($StartDocker)`.
- `Test-DockerEngine` / already-running returns before `Start-Process`.
- Tray-only keys (`openUIOnStartupDisabled` or `Set-DockerTrayOnlySettings`) live in the launcher.
- No Docker dashboard URL start; `:9119` still requires `-OpenDashboard`.
- VBS still hidden / no `-StartDocker` required.
- `-Smoke` plan text says auto-start tray Docker, not fail-closed.

## Out of scope

- New VBS/exe entrypoint
- Docker installer download on every open
- Merging PR #10
