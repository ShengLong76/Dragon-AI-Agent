# Dragon AI Agent — bot groups

Bot groups replace profiles. This file is the signed-off shape James asked for: data model, GitHub listing, import, export, the singular toggle, and where the overlay lives so an upstream sync of the desktop agent does not wipe it.

Do not call them templates. There is no second profiles UI.

## What changed from profiles

The v0.1.0 **profile catalog** was a packaged folder (`profiles/`, `profile.json`) selected from a numbered console menu or imported from a zip. That is gone as a product surface.

| Profiles (old) | Bot groups (this) |
|----------------|-------------------|
| A profile is a pack of bots + connectors | A bot group is a **department-level set of bots** |
| Catalog hard-read from the install tree | Dropdown **fetches** `bot-groups/catalog.json` from this GitHub repo |
| Import from a file was a first-class path | Deploy from the dropdown; no manual file handling on that path |
| No export | Export writes the same group file the repo stores |
| Singular bot create/import felt like Grokbot | No standalone create-a-bot path. Singular import/export is an **opt-in toggle, off by default** |

Bots exist because a group defines them, even when the group is small (Personal Assistant is a one-bot group).

**Compatibility (one-time load):** an old `profile.json` still loads. `displayName` maps to group `name` or bot `title`; `description` maps to `departmentJob` (group) or bot `description`. After load, the applied copy is written as `bot-group.json`. Do not keep offering a Profiles menu.

## Data model

Canonical file: `bot-groups/<id>/bot-group.json`.

```json
{
  "kind": "bot-group",
  "schemaVersion": 1,
  "id": "real-estate-cold-call-lead-refresher",
  "name": "Real Estate Cold Call Lead Refresher",
  "departmentJob": "Outbound real-estate team: refresh stale leads, warm them by email toward a consent form, write cold-call scripts, and sequence follow-ups.",
  "version": "1.1.0",
  "bots": [
    {
      "id": "email-warmer",
      "title": "Email Warmer",
      "description": "CAN-SPAM warming sequences that link to a TCPA consent form.",
      "tools": ["email", "crm", "consent-form"],
      "soul": "bots/email-warmer/SOUL.md",
      "config": "bots/email-warmer/bot.yaml"
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `name` | Bot group name (department pack) |
| `departmentJob` | The department-level job the group works toward |
| `bots[].title` | That bot's job title |
| `bots[].description` | What that bot does |
| `bots[].tools` | Tool ids the bot is allowed to use (email, CRM, computer-use, …) |

Optional `connectors[]` stay as non-secret placeholders the installer already copies. They are not a second product; they back the tools list.

Catalog (repo root of the overlay): `bot-groups/catalog.json`

```json
{
  "kind": "bot-group-catalog",
  "schemaVersion": 1,
  "product": "Dragon AI Agent",
  "repository": {
    "owner": "ShengLong76",
    "name": "airmaze-agent",
    "ref": "main",
    "path": "bot-groups"
  },
  "groups": [
    { "id": "personal-assistant", "name": "Personal Assistant", "departmentJob": "…", "path": "personal-assistant" }
  ]
}
```

The client does **not** hard-code that `groups` list. The file in GitHub is the list. The in-app Teams marketplace popup unions the bundled catalog so Real Estate Lead Gen, Marketing Team, and Trading Team stay visible when GitHub is stale. Catalog v1 listing fields (`blurb`, `detail`, `author`, `seats`, `requiredConnectors`, `featured`) are documented in `TEAMS_MARKETPLACE.md`. Personal Assistant stays the default one-bot profile (preinstalled); it is not listed as a team.

## How the client lists and deploys from GitHub

**Repo:** https://github.com/ShengLong76/airmaze-agent  
**Path:** `bot-groups/` on `main`  
**Engine:** `scripts/airmaze/bot_groups.py` (Dragon overlay; Linux-safe)  
**UI:** in-app **Teams** marketplace popup in the Dragon AI desktop (sidebar button, overlay + `teams_picker.py` on `127.0.0.1:8653`). Browse catalog fields + checkboxes + **Details / Install** + **Launch** / **Import** / **Export**. First-run wizard has **Choose a Team**. `Select-BotGroup.ps1` is the WinForms **popup list** (CheckedListBox) fallback, same crimson / dark chrome. Not a restyle. Design: `docs/airmaze/TEAMS_POPUP.md`, `docs/airmaze/TEAMS_MARKETPLACE.md`.

On open, the popup calls `list_groups` / `list_teams`:

1. `GET https://raw.githubusercontent.com/ShengLong76/airmaze-agent/main/bot-groups/catalog.json`
2. Write the response to `%LOCALAPPDATA%\DragonAIAgent\bot-groups\cache\catalog.json`
3. Fill the popup list from `groups[]` (name + department job). No baked-in ids in the client.

To stay current, every open refetches. A successful fetch replaces the cache. Adding a group in this repo (catalog entry + folder) shows up the next time the UI opens. The client does not ship a second list.

**When GitHub is unreachable:**

1. Use the last cache under `bot-groups/cache/`
2. Else use the bundled `bot-groups/catalog.json` that shipped with the package
3. Status line: `GitHub unreachable — using cached catalog` or `… bundled catalog`
4. Deploy still works from cache/bundle. The user is not asked to download a zip by hand.

**Deploy (no manual file handling):**

1. User checks one or more teams in the popup and clicks **Launch**
2. Client fetches that group's `bot-group.json` and each bot's `SOUL.md` / `bot.yaml` from the same GitHub tree (or cache/bundle)
3. Each bot is written to the **existing desktop picker path** `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` (title, description, tools in `bot.meta.json`; soul + yaml as today)
4. File every bot in that pack into a **named BOTS section** labeled with the group display name (see below). They must not land under UNASSIGNED.
5. Mirror into `%USERPROFILE%\.hermes-airmaze-embedded\profiles\` so Bot Screen / Remote serve still sees them
6. Record `%LOCALAPPDATA%\DragonAIAgent\active-bot-group.json`

That destination folder name (`hermes\profiles\<bot-id>`) is the upstream desktop / Bot Screen picker. It is **not** renamed. Only Dragon's catalog and UI say "bot group".

### If those bots already exist

Deploy is idempotent. Group-owned files (`SOUL.md`, `bot.yaml`, `profile.yaml`, `bot.meta.json`) are overwritten from the group. Extra files the user added in that bot folder are left alone. The result reports `created` vs `updated`. Onboarding secrets and `bots-status.json` are not wiped. Re-apply also re-stamps the named UI section so an older install that left those bots under UNASSIGNED is corrected.

## Named UI section (not UNASSIGNED)

The Dragon AI BOTS pane is the upstream user-section chrome (`user-sections.ts`). Membership is **on the bot**: `profile.yaml` `ui_meta.hermes-bots.sectionId` + `sectionName`. Bots missing those fields, or pointing at a section the desktop does not know, draw last under **UNASSIGNED**.

Import (`Import-BotGroup`, and the Apply-Profile / Import-Profile shims) and deploy do this:

1. Stable id `sec-dragon-<group-id>` so a second apply updates the same folder
2. Label = group `name` (or leftover profile `displayName`) — e.g. "Marketing Team", "Real Estate Cold Call Lead Refresher"
3. Write `sectionId` and `sectionName` on every bot in the pack (`profile.yaml` + `bot.meta.json`)
4. The desktop's `adoptBotSectionsFromMeta` rebuilds the section from those two fields. Dragon does not click "New section" in the UI.

Singular one-bot import (toggle on) does not invent a department section.

## Export

**Export** writes a folder (or zip of that folder) in the **same format the repository stores**:

```text
<group-id>/
  bot-group.json
  bots/<bot-id>/SOUL.md
  bots/<bot-id>/bot.yaml
  connectors/*.json    # optional placeholders
```

That file can be re-imported (`Import-BotGroup`) or dropped back into `bot-groups/` on this repo. Export is always available for a **group**. It is not a Grokbot "save this one bot as a product" path.

## Singular toggle (off by default)

Lives in the bot group window as a checkbox: **Allow import or export of one bot**. Backing file:

`%LOCALAPPDATA%\DragonAIAgent\bot-group-settings.json`

```json
{ "allowSingularBotImportExport": false }
```

Default is **false**. The UI loads that value; the checkbox is unchecked unless the user turns it on.

A one-bot file is **not** a group file:

```json
{
  "kind": "bot",
  "schemaVersion": 1,
  "id": "email-warmer",
  "title": "Email Warmer",
  "description": "…",
  "tools": ["email", "crm", "consent-form"],
  "soul": "# Email Warmer\n…",
  "config": "slug: email-warmer\n…"
}
```

| | Group file | One-bot file |
|--|------------|--------------|
| `kind` | `bot-group` | `bot` |
| Shape | name + department job + `bots[]` | one title, description, tools |
| Default path | always allowed | refused unless the toggle is on |

Turning the toggle on does **not** add a create-a-bot wizard. It only unlocks import/export of an existing bot definition. Off remains the product default.

## Customization paths (survive an upstream sync)

This repo's base is the Dragon AI **desktop agent** packaging (gateway, Bot Screen `:8650`, branding overlay, `Hermes.exe` launch). Bot groups are a layer on that base, not a rewrite of it.

| Path | Role | Sync |
|------|------|------|
| `bot-groups/` | Catalog + group files (the GitHub list) | **Customization.** Upstream desktop/hermes-agent has no `bot-groups/`. A sync of the base does not contain this tree; keep it. |
| `scripts/airmaze/bot_groups.py` | List / deploy / export / toggle | **Customization.** New file. |
| `scripts/airmaze/team_marketplace.py` | Marketplace listing + secret scrub + publish | **Customization.** New file. |
| `scripts/airmaze/Select-BotGroup.ps1` | Teams popup UI | **Customization.** New file. |
| `scripts/airmaze/Deploy-BotGroup.ps1` | Deploy wrapper | **Customization.** New file. |
| `scripts/airmaze/Export-BotGroup.ps1` | Export wrapper | **Customization.** New file. |
| `scripts/airmaze/Import-BotGroup.ps1` | Re-import exported group (or one bot if toggled) | **Customization.** New file. |
| `scripts/airmaze/apply-default-bot-group.ps1` | Default Personal Assistant group | **Customization.** New file. |
| `scripts/airmaze/Test-BotGroups.py` | Tests | **Customization.** New file. |
| `docs/airmaze/BOT_GROUPS.md` | This design | **Customization.** New file. |

**Do not treat as bot-group overlay** (an upstream sync of the desktop agent owns these; bot groups must not replace them):

- `docker-compose.embedded.yml`, `:8650`, `dragon-local`, `hermes-airmaze-gw`, `hermes-airmaze-desktop`
- Launch / branding: `start-embedded.ps1`, `desktop_branding.*`, `branding/` (Syne, crimson `#C41E3A`, navy dragon mark)
- On-disk destination `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` and the embedded volume `.hermes-airmaze-embedded/profiles\`

**How a sync keeps the overlay:** merge the base desktop-agent tree; leave `bot-groups/` and the files in the table above in place. Thin shims (`Select-Profile.ps1` → `Select-BotGroup.ps1`) stay so old shortcuts do not open a Profiles UI — they open bot groups.

## Desktop agent and sidebar

- Gateway, Bot Screen, and the desktop client keep working. Bot groups only add catalog/deploy/export.
- Sidebar keeps **Personal Assistant** (the default group). Do not add a Hermes bot back. Deployed packs appear under a named section, not UNASSIGNED.
- No restyle: Syne 700, crimson `#C41E3A`, navy dragon mark stay as they are.

## Tests

```bash
python3 scripts/airmaze/Test-BotGroups.py
```

Covers: rename (no Profiles UI), dropdown reads the repo, deploy one group, export re-imports, singular toggle off by default, old `profile.json` still loads once, imported bots file into a named UI section (not UNASSIGNED), Bot Screen tokens untouched.
