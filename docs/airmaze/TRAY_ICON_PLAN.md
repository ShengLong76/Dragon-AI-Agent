# Tray icon live apply — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native, this session). Tests first. Draft PR only. Do not merge.

**Goal:** The Windows tray / taskbar / shortcut dragon is the contain-maxed transparent sidebar mark, and launch actually copies that ICO onto the live Hermes client.

**Architecture:** One ICO, two filenames. Rebuild `installer/winres/icon.ico` and `branding/dragon-ai-agent-logo.ico` from `branding/dragon-ai-agent-logo.png` (object-fit contain at max). Apply copies that file onto every Hermes `icon.ico` next to `Hermes.exe`. Shortcuts keep `IconLocation` on the same ICO.

**Tech Stack:** Pillow ICO writer, `desktop_branding.py` / `Apply-DesktopBranding.ps1`, existing `Test-TrayIcon.py`.

**Spec:** `docs/airmaze/TRAY_ICON.md`

## Global Constraints

- No fixed display pixel size (`TRAY_ICON_PX`, `iconSize: 48`, `width: 48px`).
- Docker tray-only launch (`openUIOnStartupDisabled`, `Start-DockerIfNeeded`) stays.
- Bot Screen `:8650` / `dragon-local` / empty-state `22rem` / sidebar `32px` stay.
- Python is optional on UltraDragon; PowerShell apply must copy the ICO.
- Draft PR. James merges.

## Review Focus

- Live install has branding ICO but no `installer\winres` — apply must still copy.
- Extra `resources\app.asar.unpacked\icon.ico` must be overwritten, not only `resources\icon.ico`.
- Existing wscript shortcuts must get a fresh `IconLocation` (do not `continue` before the icon write).
- Shipped frames stay navy / no copper rim leftover from the circular badge.
- Icon-cache note is documentation only; do not shell-out `ie4uinit` from launch.

## Tests first

Extend `scripts/airmaze/Test-TrayIcon.py` (and installer string checks) **before** changing engines:

1. Fill ratio: every required ICO frame’s opaque box fills the slot on the long axis (≥0.92). No crop / stretch.
2. Source: winres + branding ICOs are the same artwork; navy `#314A73` present; copper-badge remnant (`#C4A574` / isolated rim) absent.
3. `tray_icon.py` rebuilds from `dragon-ai-agent-logo.png`, not `isolate_dragon_artwork`.
4. `stamp_app_icon` / PowerShell copy the ICO to `resources\icon.ico`, beside the exe, and existing unpacked `icon.ico` paths. Branding ICO is preferred when winres is missing.
5. `install.ps1` and `DragonAIAgentSetup.ps1` copy `installer\winres\icon.ico` into the install root.
6. `Repair-DragonAIProductShortcuts` refreshes `IconLocation` on an already-wscript shortcut.
7. No `trayIconSize = 48` / `width: 48px` bump. Docker tray-only tokens remain. `TRAY_ICON.md` names contain-max, sidebar mark, relaunch, and icon cache.

Run: `python3 scripts/airmaze/Test-TrayIcon.py` — must fail on current main, then pass after the implementation.

## Implementation

1. `branding/tray_icon.py` — `load_sidebar_mark()` → `write_ico` for both destinations. Keep `contain_fit_max`. Leave badge isolate unused.
2. Rebuild both ICOs (`python3 branding/tray_icon.py`).
3. `desktop_branding.py` — `icon_source()` prefers branding ICO; `icon_destinations(exe)` + `stamp_app_icon` copy to all Hermes paths; best-effort `rcedit`.
4. `Apply-DesktopBranding.ps1` — same prefer + destination list (PowerShell path when Python is missing).
5. Installers copy `installer\winres\icon.ico`. Shortcut repair always sets `IconLocation`.
6. Docs: this plan, `TRAY_ICON.md`, `BRANDING.md`, `PRODUCT_BRANDING.md`, `DESIGN.md`, `CHANGELOG.md`.

## Verify

```bash
python3 scripts/airmaze/Test-TrayIcon.py
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```

## Out of scope

- Electron rebuild / `app.asar` rewrite
- Opening Docker dashboard or `:9119`
- Merging
