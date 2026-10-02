# Dragon AI Agent — Teams marketplace v1

James locked this as **the same job as the Teams popup** (`docs/airmaze/TEAMS_POPUP.md`). One surface: checkbox Launch / Import / Export **plus** a GitHub-hosted catalog browse → detail → Install, with PR #19’s **4-column seat cards** inside that popup. Recipe packs, not live logins. No payments. No cloning running bots.

Plan: `docs/airmaze/TEAMS_POPUP_PLAN.md` (marketplace tasks are in that same plan). James merges.

## What v1 is

A **public team pack** is a department roster (souls, tools, connector *placeholders*). It is not a Grok-style live bot clone and it does not ship secrets.

| Browse field | Meaning |
|--------------|---------|
| name / `displayName` | Pack title (Real Estate Lead Gen, Marketing Team, Trading Team) |
| blurb | One-line summary |
| detail | Longer what-it-does copy |
| seats | Bot count (Marketing stays **6** Cos seats) |
| author | Pack author (official packs: Dragon AI) |
| requiredConnectors | Connector / tool ids only — never keys, passwords, emails, or paths |

**Install** is the existing Marketing/Trading path: `apply_team` → `deploy_group` → named BOTS section (`sec-dragon-<id>`), not UNASSIGNED.

**Export / Publish** writes the same `bot-groups/<id>/` tree the repo stores, then **scrubs** API keys, passwords, personal emails, and local paths so the zip is catalog-ready.

Personal Assistant stays the default one-bot profile. It is not a marketplace row.

## Hosting (GitHub catalog)

v1 is **not** a commercial web store. The index is this repo:

```text
bot-groups/catalog.json
bot-groups/<pack-id>/bot-group.json
bot-groups/<pack-id>/bots/<bot-id>/SOUL.md
bot-groups/<pack-id>/bots/<bot-id>/bot.yaml
bot-groups/<pack-id>/connectors/*.json   # optional placeholders
```

The client already fetches `https://raw.githubusercontent.com/ShengLong76/airmaze-agent/main/bot-groups/catalog.json` (this tree). Adding a pack = catalog entry + folder. Do not invent a second `marketplace/` tree.

### `catalog.json` (additive, schemaVersion 1)

```json
{
  "kind": "bot-group-catalog",
  "schemaVersion": 1,
  "product": "Dragon AI Agent",
  "marketplace": {
    "version": 1,
    "kind": "teams-marketplace",
    "hosting": "github",
    "path": "bot-groups"
  },
  "repository": {
    "owner": "ShengLong76",
    "name": "airmaze-agent",
    "ref": "main",
    "path": "bot-groups"
  },
  "groups": [
    {
      "id": "marketing-team",
      "name": "Marketing Team",
      "displayName": "Marketing Team",
      "blurb": "Six Cos seats for a marketing desk.",
      "detail": "Content, SEO, social, paid, lifecycle, and measurement.",
      "author": "Dragon AI",
      "seats": 6,
      "featured": true,
      "requiredConnectors": [
        { "id": "computer-use", "displayName": "Computer use" },
        { "id": "browser", "displayName": "Browser" }
      ],
      "path": "marketing-team",
      "picker": true,
      "tags": ["marketing", "multi-bot", "featured"]
    }
  ]
}
```

Unknown extra keys are ignored. `picker: false` (Personal Assistant) stays out of the popup. Featured official packs: Real Estate Lead Gen (4), Marketing Team (6), Trading Team (4).

A published zip may include `catalog-entry.json` — a stub to paste into `groups[]` when adding a community pack to this repo. v1 does not open a PR for the user.

## In-app popup (one dialog)

Same overlay as the Teams Marketplace popup (`127.0.0.1:8653`, not Bot Screen `:8650`):

1. **Browse** — checkbox row per pack: name, blurb, seats, author, required connectors.
2. **4-column seat cards** under each pack (icons, briefs, hover/focus detail). Marketing wraps 4+2.
3. **Details** — full detail + seat list + connectors. **Install** applies that one pack (same as Launch of one id).
4. **Launch** — apply every checked pack into its **own** named section (no merged roster).
5. **Export** — download a scrubbed, re-importable zip (`POST /api/teams/export`).
6. **Import** — custom zip/JSON (`POST /api/teams/import`).

Helper additions (same process):

| Method | Path | Role |
|--------|------|------|
| GET | `/api/teams` | Browse list (now includes marketplace fields + seat briefs) |
| GET | `/api/marketplace` | Same packs, `kind: dragon-teams-marketplace`, featured first |
| GET | `/api/marketplace/<id>` | One pack detail |
| POST | `/api/marketplace/install` | `{id}` → existing apply path |
| POST | `/api/teams/apply` | `{id}` or `{ids:[…]}` (Launch) |
| POST | `/api/teams/export` | Scrubbed zip |
| POST | `/api/teams/publish` | Scrubbed zip + `catalog-entry.json` |

## Secret scrub

Export/publish removes:

- JSON values whose keys look like secrets (`api_key`, `password`, `token`, `client_secret`, …)
- Key-shaped tokens (`sk-…`, `ghp_…`, `xai-…`, `Bearer …`)
- Personal emails (keep `@example.com` / `@example.org` / `@example.net`)
- Local paths (`C:\Users\…`, `/Users/…`, `/home/…`, `%USERPROFILE%…`)
- Files named `.env`, `secrets.json`, `credentials.json`

Connector **ids and labels** stay. Empty placeholder fields stay empty.

## Out of scope

- Payments, ratings, a public web store
- Cloning live UltraDragon logins
- A 7th Marketing seat (SEO Specialist stays one of six; do not regress PR #18 if it lands)
- Changing Bot Screen `:8650` / `dragon-local`
- Merging (James merges)
