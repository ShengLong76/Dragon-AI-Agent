# Setup-owned Docker Desktop (Windows package)

Short design. A clean Windows PC gets Docker Desktop through **Dragon AI Agent Setup**, not as a separate install the user does first.

Launch still does **not** download or install Docker (`docs/airmaze/DOCKER_LAUNCH.md`). That path only starts an already-installed engine **headless** (no dashboard, no onboarding, **no tray** icon).

## Why the old path failed

`Ensure-DockerDesktop` treated Docker as a best-effort extra:

1. **Exe-only skip.** If `Docker Desktop.exe` existed, Setup returned success and skipped quiet install — even when `docker` CLI / `resources\bin` was missing (half-installed).
2. **PATH not patched before `docker info`.** After a fresh quiet install, the same PowerShell session often had no `docker` on PATH. `Test-DockerEngine` failed, compose was skipped, and Setup still printed “complete”.
3. **One-string `ArgumentList`.** `install --quiet --accept-license` was passed as a single argument. Official Docker docs want separate `ArgumentList` entries.
4. **No elevation.** Quiet install needs admin for the all-users layout. Without `-Verb RunAs`, UAC never ran and the step failed.
5. **Download-page fallback.** Failure opened `https://www.docker.com/products/docker-desktop/` and told the user to install Docker themselves. That is a prerequisite, not a packaged step.
6. **Installer not in the zip.** The release layout had no `vendor/docker` slot, so Setup always hit the network (or the browser).

Per-user Docker (`%LOCALAPPDATA%\Programs\DockerDesktop`) was also invisible to `Get-DockerDesktopExe`.

## Behavior (clean PC, Docker absent)

1. Setup enables WSL2 best-effort (`wsl --install` / DISM). A reboot may still be required.
2. `Ensure-DockerDesktop` looks for a packaged installer, then a cache, then downloads:
   - `%payload%\vendor\docker\Docker Desktop Installer.exe` (or `DockerDesktopInstaller.exe`)
   - `%payload%\installer\vendor\docker\…`
   - `%LOCALAPPDATA%\DragonAIAgent\vendor\docker\…` (Setup-owned cache)
   - Official `https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe` written into that cache
3. Runs **quiet install**: `install --quiet --accept-license --always-run-service` as separate arguments (Hidden window). Elevates with `RunAs` when Setup is not already admin. Exit `0` or `3010` (reboot required) counts as installer success.
4. Patches **headless** settings (`openUIOnStartupDisabled`, `displayedOnboarding`, `disableTrayIcon`). No Docker dashboard URL. No onboarding. **No tray** icon. No `:9119`.
5. Prepends Docker `resources\bin` (including `Programs\DockerDesktop`) to **this session's** PATH, then starts `com.docker.service` / `com.docker.backend.exe` Hidden (last-resort Hidden `Docker Desktop.exe`, then hide/stop the Electron UI) and waits ~3 minutes for `docker info`.
6. If the engine is up, compose pull + `up -d`. If Windows still needs a reboot, package files and the **Dragon AI Agent** Start Menu shortcut are still written; compose waits until the next Setup run or product launch.

Half-installed (exe present, CLI missing) takes the same quiet-install path. Already-complete Docker is a no-op besides headless settings.

**Not done here:** opening docker.com, telling the user to install Docker, installing Docker from the product shortcut, stamping standalone Hermes, launching WinForms Setup, or creating Bot Groups / Dashboard / Profiles Start Menu tiles. First-run model choice stays the **in-app** Models screen. There must be no sign of Docker to the user during Setup.

## Package slot

The Windows zip may include the official installer so a clean PC never needs a first-hop to docker.com:

```text
payload/vendor/docker/Docker Desktop Installer.exe
```

Stage at release-build time (not committed; ~500MB):

```bash
python3 installer/stage-docker-desktop.py
```

Git keeps `vendor/docker/README.md` only. Setup still downloads when the slot is empty (source checkout or slim zip). The download is Setup’s job, not the user’s.

## Tests

`python3 scripts/airmaze/Test-DockerInstall.py` (also hooked from `Test-LaunchSmoke.py`). No secrets. No live Docker. Safe on Linux CI.
