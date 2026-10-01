# Plan — product branding gaps

After `docs/airmaze/PRODUCT_BRANDING.md`. Tests first. No Electron rebuild.

## Tasks

1. **Docs** — this file + `PRODUCT_BRANDING.md`. Update `BRANDING.md`, `DESIGN.md`, `desktop-client.md`, `CHANGELOG.md`, `README.md`. Sidebar copy: exclude Hermes (not “hide only”).
2. **Tests first**
   - Extend `Test-DesktopBranding.py` / `desktop_branding.py --self-test`: sidebar header lockup (logo + “Dragon AI”), ICO copied to `resources/icon.ico`, Hermes exclude (not hide-only).
   - New `scripts/airmaze/exclude_hermes_bot.py` + tests in `Test-ExcludeHermesBot.py`: purge `default`/`hermes` folders; keep Personal Assistant; refuse recreate on deploy/sync; docs mention migration.
   - `Test-LaunchSmoke.py` / installer copy list: new scripts, icon stamp, exclude hook before launch.
3. **Exclude Hermes** — engine + launch/install/sync hooks. Catalog unchanged.
4. **Sidebar header** — `dragon-ui.css` + inject script/HTML in the overlay pack.
5. **App icon** — contain-max the dragon into the Windows tray/taskbar slot (no fixed pixel bump); copy that ICO to unpacked `resources/icon.ico`; stamp `Hermes.exe` when possible; keep `.lnk` IconLocation; set Client.lnk AppUserModelID. See `docs/airmaze/TRAY_ICON.md`.
6. **Named UI section on import** — deploy/import stamps `ui_meta.hermes-bots.sectionId` / `sectionName` so the BOTS pane files the pack under its display name, not UNASSIGNED. Re-apply updates the same `sec-dragon-<id>`. Cover Apply-Profile / Import-Profile shims (they already call Import-BotGroup).
7. **In-app Teams picker** — overlay dialog + `127.0.0.1:8653` helper. Catalog teams: Real Estate Lead Gen, Marketing Team, Trading Team. Personal Assistant is the default preinstall, not a team. Import from file stays. First-run **Choose a Team**.
8. **Self-review + PR** against `main`. James merges.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-ExcludeHermesBot.py
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```

## UltraDragon (after James says resume)

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install). Do not instruct a live reinstall until he says so.
2. Open Start Menu **Dragon AI Agent**.
3. Sidebar header above SESSIONS / BOTS shows the Dragon mark + **Dragon AI** + **Teams Marketplace**. If header/inner are missing, the body overlay sits in a clearance spacer above those tabs (they stay clickable). Sidebar bot names and middle session names match at 16px.
4. Taskbar / running window uses the Dragon ICO (not the purple Hermes square).
5. BOTS list has no Hermes row. If an old box still has one: delete `%LOCALAPPDATA%\hermes\profiles\hermes` and `...\default` plus the same names under `%USERPROFILE%\.hermes-airmaze-embedded\profiles\`, then relaunch.
6. Deploy or re-apply a bot group (e.g. Real Estate). Those bots sit under a named section matching the pack display name — not UNASSIGNED.
7. Sidebar **Teams Marketplace** lists Real Estate Lead Gen, Marketing Team, Trading Team. Personal Assistant is already installed. One click apply. Import from file still works.
8. Bot Screen Remote still Embedded Linux `http://127.0.0.1:8650`.
