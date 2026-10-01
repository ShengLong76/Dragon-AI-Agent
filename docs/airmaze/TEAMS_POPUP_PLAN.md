# Plan — Teams popup + marketplace v1 (same job)

After `docs/airmaze/TEAMS_POPUP.md` and `docs/airmaze/TEAMS_MARKETPLACE.md`. Tests first. No Electron rebuild. James: popup Launch/Import/Export and marketplace browse/install/export are **one PR**.

## Tasks

1. **Docs** — this file + `TEAMS_POPUP.md` + `TEAMS_MARKETPLACE.md`. Update `PRODUCT_BRANDING.md`, `BOT_GROUPS.md`, `DESIGN.md`, `desktop-client.md`, `CHANGELOG.md`, `README.md`.
2. **Tests first**
   - `Test-TeamsPicker.py`: roomy popup (not dropdown), checkbox rows, Launch / Export / Import, `apply_teams` files each pack into its own named section, export zip re-imports, PA still refused, close+reload after Launch. WinForms is CheckedListBox, not ComboBox.
   - `Test-TeamsMarketplace.py`: catalog parse (blurb/detail/seats/author/connectors), featured RE / Marketing / Trading, Install uses apply path, export/publish scrubs secrets, Marketing stays 6 seats.
   - `Test-BotGroups.py` UI contract: popup list, not ComboBox. Crimson / export / singular toggle stay.
   - `teams_picker.py --self-test` covers ids apply + export path.
3. **Helper** — `apply_teams(ids)`, scrubbed `export_teams`, `team_marketplace.py` list/detail/install/publish. HTTP: `GET /api/marketplace`, `POST /api/marketplace/install`, `POST /api/teams/export` (scrubbed).
4. **Overlay** — checkbox popup + marketplace cards (brief + Details + Install) + Launch / Export / Import / Close. Larger panel + backdrop in `dragon-ui.css`.
5. **WinForms** — CheckedListBox; Launch applies checked teams; Import + Export stay visible; rows show seats/author when present.
6. **Catalog** — seed `bot-groups/catalog.json` marketplace fields. No 7th Marketing seat. No parallel store tree.
7. **Self-review + update PR #14**. James merges.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-TeamsMarketplace.py
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```

## UltraDragon (after James says resume)

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install).
2. Open **Dragon AI Agent**. Sidebar **Teams** opens a popup (not a dropdown).
3. All loadable teams are listed with checkboxes. Personal Assistant is not a row.
4. Check Marketing + Trading (or Real Estate). **Launch** files each under its own section and reloads. Open **Details** for blurb/detail/seats/connectors, then **Install**. **Export** downloads a scrubbed catalog-ready zip. **Import** still takes a custom zip/JSON.
5. Bot Screen Remote still Embedded Linux `http://127.0.0.1:8650`.
