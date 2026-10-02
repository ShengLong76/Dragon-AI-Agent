# Plan — durable Dragon logo + tray

After `docs/airmaze/DURABLE_BRANDING.md`. Tests first. No Electron rebuild. Draft PR only. James merges.

## Tasks

1. **Docs** — this file + `DURABLE_BRANDING.md`. Update `BRANDING.md`, `TRAY_ICON.md`, `PRODUCT_BRANDING.md`, `DESIGN.md`, `CHANGELOG.md`.
2. **Tests first** (must fail on current main, then pass)
   - `Test-DesktopBranding.py`: after `apply_to_exe` on a fake `%…%\DragonAIAgent\desktop\win-unpacked`, the pack SVG/PNG exist and are referenced; `dist/apple-touch-icon.png` is the Dragon PNG; apply still refuses standalone Hermes.
   - `Test-TrayIcon.py`: `stamp_app_icon` copies Dragon ICO **and** PNG (`icon.png`, `apple-touch-icon.png`) only on a DragonAIAgent path; standalone Hermes is refused with `Refuse branding outside DragonAIAgent`.
   - `Test-PrivateDesktop.py` / installer string checks: apply + installers hard-fail when required logo files are missing; PowerShell copies PNG candidates.
3. **Engine** — `desktop_branding.py` / `Apply-DesktopBranding.ps1`: required logo copy; ICO + PNG destinations; `stamp_app_icon` / `Copy-DragonAIAppIcon` assert private path.
4. **Installers** — `install.ps1` / `DragonAIAgentSetup.ps1` throw if SVG/PNG/ICO did not copy into `%LOCALAPPDATA%\DragonAIAgent\branding\`.
5. **Self-review + draft PR** against `main`. Do not merge.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-TrayIcon.py
python3 scripts/airmaze/Test-PrivateDesktop.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```

## How Cos tips UltraDragon (after James says resume)

1. Close `Hermes.exe` so `index.html` / `icon.ico` / `apple-touch-icon.png` are not locked.
2. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or re-run Setup). Confirm `branding\dragon-ai-agent-logo.svg`, `.png`, and `.ico` exist.
3. Open Start Menu **Dragon AI Agent** (or run `Apply-DesktopBranding.ps1 -ExePath` against the private exe). Apply must copy the pack + ICO/PNG before the window opens.
4. Sidebar lockup shows the navy Dragon SVG (not a broken image). Taskbar / tray uses the Dragon mark.
5. Confirm live files:
   - `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\resources\app.asar.unpacked\dist\dragon-ai-branding\dragon-ai-agent-logo.svg`
   - `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\resources\icon.ico`
   - `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\resources\app.asar.unpacked\dist\apple-touch-icon.png`
6. Do **not** apply against `%LOCALAPPDATA%\hermes\…`. If the taskbar is cached, sign out / restart Explorer (`docs/airmaze/TRAY_ICON.md`).

## Out of scope

- Electron rebuild / `app.asar` rewrite
- Opening Docker dashboard or `:9119`
- Merging
