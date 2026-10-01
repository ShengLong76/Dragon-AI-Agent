# Dragon AI Agent — Teams popup (2026-10-01)

Short design after James’s Teams UI notes. Packaging overlay + WinForms fallback. No Electron rebuild. No `app.asar` rewrite. Bot Screen stays `127.0.0.1:8650` / `dragon-local`. Teams helper stays `127.0.0.1:8653`.

This note agrees the surface before code. Plan: `docs/airmaze/TEAMS_POPUP_PLAN.md`.

## What James marked

1. **Teams control is a dropdown.** Too tight. More team groups need to show.
2. **Export is missing** on the in-app Teams surface (WinForms already had Export; overlay apply/import did not).
3. **Import UX:** the popup must list every loadable team, each with a **checkbox** (multi-select), a **Launch** button that loads the checked teams, and **Import** sitting next to **Export**.

Keep: catalog / Cos rosters, Personal Assistant not a team, apply files a named section (not UNASSIGNED), close + reload after apply. Syne + crimson stay.

**Marketplace (same popup):** browse GitHub `bot-groups/catalog.json` with blurb, detail, seats, author, and required connectors. **Details → Install** applies one pack. **Export** strips secrets so the zip is catalog-ready. Design: `docs/airmaze/TEAMS_MARKETPLACE.md`. Not a second window.

## Popup, not dropdown

**Do:**

1. Overlay: roomier `role="dialog"` popup (centered, backdrop, scrollable list). Not a `<select>` and not one-click cards that apply immediately.
2. WinForms fallback (`Select-BotGroup.ps1`): **CheckedListBox** popup. Not ComboBox.
3. List every picker team from the GitHub catalog (`GET /api/marketplace` with `GET /api/teams` fallback). Same `bot-groups/` source as today.
4. Each row is a native checkbox + name + blurb + seats + author + required connectors. **Details** opens the longer pack copy; **Install** applies that one pack.

Do not restyle Bot Screen. Do not add a Hermes team.

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

1. `desktop_branding.py` injects the popup script. `dragon-ui.css` styles it (Syne 700, dark `#1C1C20`, crimson `#C41E3A`, visible `:focus-visible`).
2. Helper `teams_picker.py` on `:8653`:
   - `GET /api/teams` and `GET /api/marketplace` — catalog browse (marketplace fields)
   - `GET /api/marketplace/<id>` — pack detail
   - `POST /api/marketplace/install` — `{id}` → existing apply path
   - `POST /api/teams/apply` — `{id}` as today, or `{ids:[…]}` for Launch
   - `POST /api/teams/import` — unchanged
   - `POST /api/teams/export` — `{id}` or `{ids:[…]}` → scrubbed zip
   - `POST /api/teams/publish` — scrubbed zip + `catalog-entry.json`
3. First-run **Choose a Team** still opens `Select-BotGroup.ps1` (now the popup).

## Out of scope

- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Changing ports, tokens, image names, or Cos roster contents
- Merging (James merges)
