# Plan — Teams Marketplace roomy popup + 4-column seat grid

After `docs/airmaze/TEAMS_POPUP.md` and `docs/airmaze/TEAMS_MARKETPLACE.md`. Tests first. No Electron rebuild.

James: the live overlay still opens the PR #19 **dropdown panel**. Tip #14 (roomy popup + Launch / Import / Export / marketplace Install) never landed on UltraDragon. This job restacks that popup onto **current main** and keeps #19’s seat-card grid **inside** the modal.

## Design (locked)

| Surface | Behavior |
|---------|----------|
| Sidebar control | **Teams Marketplace** under the 32px logo, above Sessions/Bots. Do not truncate the label. BOTS stays clickable. |
| Click | Opens a **centered modal/popup** with backdrop — not a left-rail dropdown. |
| Packs | Real Estate Lead Gen (4), Marketing Team (6 Cos), Trading Team (4). Personal Assistant is not a row. |
| Actions | Checkbox + **Launch** (each pack → its own named section), **Import**, **Export** (scrubbed), **Details → Install**. |
| Seats | `grid-template-columns: repeat(4, 1fr)`; Marketing wraps 4+2. Shadows, 12px radius, left icons, brief + hover/focus. |

Do not merge. Do not pull PR #18 seoagent tools unless already on main.

## Tasks

1. **Docs** — this file + `TEAMS_POPUP.md` + `TEAMS_MARKETPLACE.md`. Update `TEAMS_SEAT_DESCRIPTIONS.md`, `PRODUCT_BRANDING.md`, `BOT_GROUPS.md`, `DESIGN.md`, `desktop-client.md`, `CHANGELOG.md`, `README.md`.
2. **Tests first**
   - `Test-TeamsPicker.py`: roomy popup (not dropdown), checkbox rows, Launch / Export / Import, `apply_teams` files each pack into its own named section, export zip re-imports, PA still refused, close+reload after Launch. Keep #19 seat-grid / icon / chrome contracts. WinForms is CheckedListBox, not ComboBox.
   - `Test-TeamsMarketplace.py`: catalog parse (blurb/detail/seats/author/connectors), featured RE / Marketing / Trading, Install uses apply path, export/publish scrubs secrets, Marketing stays 6 seats. Overlay lives in `teams-picker.js`.
   - `Test-BotGroups.py` UI contract: popup list, not ComboBox.
   - `teams_picker.py --self-test` covers ids apply + export path.
3. **Helper** — `apply_teams(ids)`, scrubbed `export_teams`, `team_marketplace.py` list/detail/install/publish. Keep `present_seat` / `descriptionDetail`. HTTP: `GET /api/marketplace`, `POST /api/marketplace/install`, `POST /api/teams/export` (scrubbed).
4. **Overlay** — keep main sidebar chrome in `teams-picker.js`. Replace the dropdown host with checkbox popup + marketplace cards + 4-column seat grid + Launch / Export / Import / Close. Larger centered panel + backdrop in `dragon-ui.css`. Black `#000`. Honor `[hidden]`.
5. **WinForms** — CheckedListBox; Launch applies checked teams; Import + Export stay visible; rows show seats/author when present.
6. **Catalog** — seed `bot-groups/catalog.json` marketplace fields. No 7th Marketing seat. No parallel store tree. Keep Marketing seat briefs from main.
7. **Self-review + draft PR**. James merges. Cos applies the tip to UltraDragon.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-TeamsMarketplace.py
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-DesktopBranding.py
```

## UltraDragon (after James says resume)

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install). Restart **Dragon AI Agent** so `:8653` and the overlay refresh.
2. Sidebar **Teams Marketplace** opens a roomy popup (not a dropdown).
3. Confirm three marketplace rows + 4-column seat cards. Marketing is 4+2. Personal Assistant is not a row.
4. Open **Details** on Marketing — blurb + detail + connectors. **Install**. Dialog closes; BOTS **MARKETING TEAM** shows exactly 6 Cos seats.
5. Check Trading + Real Estate, **Launch**. Each files under its own section.
6. **Export** a checked pack. The zip must re-import and must not contain API keys / personal emails / `C:\Users\…` paths.
7. Bot Screen stays `127.0.0.1:8650` / `dragon-local`.
