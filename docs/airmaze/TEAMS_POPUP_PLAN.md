# Plan — Teams popup + export + multi-select Launch

After `docs/airmaze/TEAMS_POPUP.md`. Tests first. No Electron rebuild.

## Tasks

1. **Docs** — this file + `TEAMS_POPUP.md`. Update `PRODUCT_BRANDING.md`, `BOT_GROUPS.md`, `DESIGN.md`, `desktop-client.md`, `CHANGELOG.md`, `README.md`.
2. **Tests first**
   - Extend `Test-TeamsPicker.py`: roomy popup (not dropdown), checkbox rows, Launch / Export / Import, `apply_teams` files each pack into its own named section, export zip re-imports, PA still refused, close+reload after Launch. WinForms is CheckedListBox, not ComboBox.
   - Extend `Test-BotGroups.py` UI contract: popup list, not ComboBox. Crimson / export / singular toggle stay.
   - `teams_picker.py --self-test` covers ids apply + export path.
3. **Helper** — `apply_teams(ids)`, `export_team` / `export_teams` wrapping `bot_groups.export_group`. HTTP `POST /api/teams/apply` accepts `ids`; add `POST /api/teams/export`.
4. **Overlay** — inject checkbox popup + Launch / Export / Import / Close. Larger panel + backdrop in `dragon-ui.css`.
5. **WinForms** — replace ComboBox with CheckedListBox; Launch applies checked teams; Import + Export stay visible.
6. **Self-review + PR** against `main`. James merges.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```

## UltraDragon (after James says resume)

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install).
2. Open **Dragon AI Agent**. Sidebar **Teams** opens a popup (not a dropdown).
3. All loadable teams are listed with checkboxes. Personal Assistant is not a row.
4. Check Marketing + Trading (or Real Estate). **Launch** files each under its own section and reloads. **Export** downloads a re-importable group zip. **Import** still takes a custom zip/JSON.
5. Bot Screen Remote still Embedded Linux `http://127.0.0.1:8650`.
