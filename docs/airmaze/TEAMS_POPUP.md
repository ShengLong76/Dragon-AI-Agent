# Dragon AI Agent — Teams Marketplace popup (2026-10-01)

Short design after James’s Teams UI notes. Packaging overlay + WinForms fallback. No Electron rebuild. No `app.asar` rewrite. Bot Screen stays `127.0.0.1:8650` / `dragon-local`. Teams helper stays `127.0.0.1:8653`.

This note agrees the surface before code. Plan: `docs/airmaze/TEAMS_POPUP_PLAN.md`.

Restack: PR #14’s roomy marketplace popup on **current main**, folding in PR #19’s **4-column seat-card** polish. Do not invent a third UI. Sidebar chrome from main stays (logo + **Teams Marketplace** above Sessions/Bots; BOTS clickable; do not truncate the label).

## What James marked

1. **Teams Marketplace control opens a cramped sidebar dropdown.** Too tight. Seats need a **popup window** with a **4-column** card grid.
2. **Export is missing** on the in-app Teams surface (WinForms already had Export; overlay apply/import did not).
3. **Import UX:** the popup must list every loadable team, each with an **Install** button (applies that pack), a **Launch** button for batch apply, and **Import** sitting next to **Export**.

Keep: catalog / Cos rosters, Personal Assistant not a team, apply files a named section (not UNASSIGNED), close + reload after apply. Syne + crimson stay. Seat briefs + hover detail + left icons stay.

**Marketplace (same popup):** browse GitHub `bot-groups/catalog.json` with blurb, detail, seats, author, and required connectors. **Details → Install** applies one pack. **Export** strips secrets so the zip is catalog-ready. Design: `docs/airmaze/TEAMS_MARKETPLACE.md`. Not a second window.

## Popup, not dropdown

**Do:**

1. Overlay: roomier `role="dialog"` **modal** (centered, backdrop, scrollable). Not a `<select>`, not a left-rail dropdown, and not one-click cards that apply immediately.
2. Width is at least `min(72rem, calc(100vw - 48px))` so a **4-column** seat grid fits. Marketing lays out 4+2. Do not paint empty cells to force a 4×4 board.
3. WinForms fallback (`Select-BotGroup.ps1`): **CheckedListBox** popup. Not ComboBox.
4. List every picker team from the GitHub catalog (`GET /api/marketplace` with `GET /api/teams` fallback). Same `bot-groups/` source as today.
5. Each row is an **Install** button + name + blurb + seats + author + required connectors. Clicking **Install** applies that pack (same `apply_team` path as Details → Install). **Details** opens the longer pack copy.
6. Under each pack, seats are **cards** in `grid-template-columns: repeat(4, 1fr)` — shadows, 12px radius, left icon, brief, hover/focus detail (PR #19).

Do not restyle Bot Screen. Do not add a Hermes team. Do not pull PR #18 seoagent tools unless they are already on main.

## Launch, Import, Export

| Control | Behavior |
|---------|----------|
| **Launch** | Apply every checked team, then close the popup and reload the roster (same `finishApply` / `location.reload` as today). |
| **Export** | Write the existing repo-format group file (`bot-group.json` + `bots/`), **secrets scrubbed** (keys, passwords, personal emails, local paths). Overlay downloads a zip from `POST /api/teams/export`. |
| **Import** | Same custom zip/JSON path as today (`POST /api/teams/import` / Import file). Visible in the action row next to Export. |

Singular one-bot import/export stays the existing off-by-default toggle on the WinForms window. Not a create-a-bot path.

## Multi-select apply (choice)

The product already files **one bot group → one named BOTS section**:

- Section id `sec-dragon-<group-id>`
- Section label = pack `displayName` / `name`
- Membership on each bot (`profile.yaml` `ui_meta.hermes-bots`)
- Re-apply updates that same section; stale bots for **that** group are cleared; other groups are left alone

There is **no** combined multi-group section and no merge-roster API.

**Choice: Launch applies each selected roster into its own named section**, sequentially, through the existing `apply_team` → `deploy_group` path. Marketing + Trading therefore appear as two sections, not one pile. `active-bot-group.json` still records the last pack (existing single-apply contract). Personal Assistant stays refused if it appears in the id list.

Do not invent a merged “Teams” section.

## Overlay + helper

1. `desktop_branding.py` injects `teams-picker.js`. `dragon-ui.css` styles the modal (black `#000` panel, Syne 700, crimson `#C41E3A`, visible `:focus-visible`, fade + slight slide/scale). Honor `[hidden]` so `display:flex` cannot leave the dialog stuck open.
2. Sidebar lockup from main is unchanged: logo + **Teams Marketplace** above Sessions/Bots; fixed overlay clearance so BOTS stays clickable.
3. Helper `teams_picker.py` on `:8653`:
   - `GET /api/teams` and `GET /api/marketplace` — catalog browse (marketplace fields + seat briefs)
   - `GET /api/marketplace/<id>` — pack detail
   - `POST /api/marketplace/install` — `{id}` → existing apply path
   - `POST /api/teams/apply` — `{id}` as today, or `{ids:[…]}` for Launch
   - `POST /api/teams/import` — unchanged
   - `POST /api/teams/export` — `{id}` or `{ids:[…]}` → scrubbed zip
   - `POST /api/teams/publish` — scrubbed zip + `catalog-entry.json`
4. First-run **Teams Marketplace** still opens `Select-BotGroup.ps1` (now the popup).

## Out of scope

- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Changing ports, tokens, image names, or Cos roster contents
- A seventh Marketing seat / restacking PR #18
- Merging (James merges)
