# Marketing Team — SEOagent on SEO Specialist

James locked **[AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo)** (MIT) as the SEO source. SEOagent is a **tool + thin skill pack on the existing SEO Specialist seat**. Not a seventh Marketing bot. Not a Claude Code plugin install.

## Decision

| Keep | Change |
|------|--------|
| Six Cos Marketing seats | SEO Specialist `tools` gains `seoagent` and `dataforseo` |
| Buffer / Brevo / DataForSEO as locked Marketing defaults | DataForSEO is the live SERP/keyword/backlink MCP. Buffer / Brevo stay on Social / Lifecycle (unchanged this PR) |
| Other seats’ tools (`computer-use`, `browser`) | Unchanged |

Seats stay:

1. Content Strategist
2. SEO Specialist
3. Social Media Manager
4. Paid Media Specialist
5. Lifecycle Marketer
6. Marketing Analyst

## Task plan

1. Design this note (adapted vs Claude-Code-only).
2. Failing tests: six seats; SEO Specialist has `seoagent` + `dataforseo` + `skills/`; others unchanged; deploy copies skills + connector.
3. Thin Dragon skill pack + DataForSEO connector + SOUL pointers.
4. Deploy copies `bots/<id>/skills/` when present.
5. Docs: DataForSEO setup, UltraDragon re-apply Marketing Team.

## How Marketing bots declare tools today

Same contract as Real Estate (`docs/airmaze/BOT_GROUPS.md`):

- `bots[].tools` — ids the bot may use
- Optional `connectors[]` + `connectors/*.json` — non-secret placeholders
- Deploy writes tools into `%LOCALAPPDATA%\hermes\profiles\<bot-id>\bot.meta.json`

Hermes built-ins already on every Marketing seat: `computer-use`, `browser`.

## What was adapted (Hermes / Dragon)

From claude-seo **skill prompts only**, rewritten as short Hermes-facing notes under `bot-groups/marketing-team/bots/seo-specialist/skills/`:

| Adapted file | Upstream leaf |
|--------------|---------------|
| `INDEX.md` | Hub `skills/seo` (workflow map, not `/seo` slash router) |
| `seo-audit.md` | `skills/seo-audit` |
| `seo-page.md` | `skills/seo-page` |
| `seo-technical.md` | `skills/seo-technical` |
| `seo-content-brief.md` | `skills/seo-content-brief` |
| `seo-dataforseo.md` | `skills/seo-dataforseo` + DataForSEO extension |

Live data prefers **DataForSEO** (`npx -y dataforseo-mcp-server`, env `DATAFORSEO_USERNAME` / `DATAFORSEO_PASSWORD`). SearchApi / Anthropic-only paths are not the default.

Tool ids on SEO Specialist: `computer-use`, `browser`, `seoagent`, `dataforseo`.

## Claude-Code-only (not vendored)

Do **not** copy these into Dragon:

- `.claude-plugin/` marketplace + `/plugin install claude-seo@…`
- `install.sh` / `install.ps1` isolated Python + Playwright Chromium
- 19 parallel Claude Code **agents** (`agents/*.md`) as Teams seats
- `/seo` slash commands, `/seo setup`, `/seo doctor`
- Extensions: Firecrawl, Ahrefs, Banana / image-gen, Profound, Matomo, Bing, SE Ranking, Unlighthouse
- SQLite drift DB, FLOW prompt dump, maps geo-grid runners

Operators who want the full Claude Code plugin install it from AgriciDaniel/claude-seo themselves. Dragon only needs the thin pack + DataForSEO MCP.

## DataForSEO setup (UltraDragon)

1. Account at [app.dataforseo.com/register](https://app.dataforseo.com/register). API Access → username (email) + API password.
2. After apply, placeholder is `%LOCALAPPDATA%\DragonAIAgent\connectors\marketing-team\dataforseo.json`.
3. Add the MCP server in the agent desktop / Hermes MCP settings (not Bot Screen `:8650`):

```json
{
  "mcpServers": {
    "dataforseo": {
      "command": "npx",
      "args": ["-y", "dataforseo-mcp-server"],
      "env": {
        "DATAFORSEO_USERNAME": "<account-email>",
        "DATAFORSEO_PASSWORD": "<api-password>",
        "ENABLED_MODULES": "SERP,KEYWORDS_DATA,ONPAGE,DATAFORSEO_LABS,BACKLINKS,DOMAIN_ANALYTICS,BUSINESS_DATA,CONTENT_ANALYSIS,AI_OPTIMIZATION"
      }
    }
  }
}
```

4. Node.js ≥ 20 on the machine that runs `npx`. Never commit credentials.

## What is still missing

- Auto-inject of `mcpServers` into embedded Hermes `config.yaml` (same gap as Real Estate MCP stubs).
- Buffer / Brevo connectors on the other seats (locked defaults; out of scope).
- Full claude-seo leaf set and parallel agents.

## How UltraDragon picks up the change

Apply overwrites group-owned files (`SOUL.md`, `bot.yaml`, `profile.yaml`, `bot.meta.json`, `skills/`) and recopies connectors.

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install a build of this branch). Restart **Dragon AI Agent**.
2. **Teams → Marketing Team → Apply / Launch** (re-apply is fine). Or `Deploy-BotGroup.ps1 -BotGroupId marketing-team`.
3. BOTS **MARKETING TEAM** still shows **exactly six** seats. No SEOagent row.
4. SEO Specialist `bot.meta.json` `tools` includes `seoagent` and `dataforseo`. Profile folder has `skills/INDEX.md`.
5. Wire DataForSEO MCP as above.

## Tests

```bash
python3 scripts/airmaze/Test-BotGroups.py
```
