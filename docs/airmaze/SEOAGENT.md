# Marketing Team — SEOagent on SEO Specialist

James locked **[seoagent.com](https://seoagent.com)** / npm **`@seoagent-official/seoagent`** (MIT, [Baxter-Inc/seoagent-npm](https://github.com/Baxter-Inc/seoagent-npm)) as the SEOagent tool. It lives on the existing **SEO Specialist** seat. Not a seventh Marketing bot.

The free **Skill** tier ships first (local CLI + agent’s own model/keys). **Autopilot is not free** ($49/site/month after a 7-day no-card trial). Do not pretend Autopilot is free.

## Decision

| Keep | Change |
|------|--------|
| Six Cos Marketing seats | SEO Specialist `tools` includes `seoagent` (plus `computer-use` / `browser`) |
| Buffer / Brevo / DataForSEO as locked Marketing defaults | DataForSEO connector **stays**. SEOagent identity is seoagent.com, not claude-seo `/seo` commands |
| Other seats’ tools (`computer-use`, `browser`) | Unchanged |

Seats stay:

1. Content Strategist
2. SEO Specialist
3. Social Media Manager
4. Paid Media Specialist
5. Lifecycle Marketer
6. Marketing Analyst

## Task plan

1. Design this note (free Skill vs paid Autopilot; adapted vs left out).
2. Tests: six seats; `seoagent` on SEO Specialist only; `seoagent init` docs; DataForSEO connector kept; no claude-seo leaves.
3. Hermes skill instructions + `connectors/seoagent.json` + keep `connectors/dataforseo.json`.
4. UltraDragon: re-apply Marketing Team.

## How Marketing bots declare tools today

Same contract as Real Estate (`docs/airmaze/BOT_GROUPS.md`):

- `bots[].tools` — ids the bot may use
- Optional `connectors[]` + `connectors/*.json` — non-secret placeholders
- Deploy writes tools into `%LOCALAPPDATA%\hermes\profiles\<bot-id>\bot.meta.json` and copies `bots/<id>/skills/` when present

## What SEO Specialist runs (free Skill)

Install path (Node.js ≥ 20), official docs:

```bash
npm install -g @seoagent-official/seoagent
seoagent init
```

One-shot without a global install:

```bash
npx -y @seoagent-official/seoagent@latest init
```

Non-interactive: `seoagent init --yes --domain example.com`.

`init` scaffolds `.seoagent/` (audits, strategy, briefs, content, roadmap) and installs the project-local Skill. The agent uses **its own model/keys**. No seoagent.com account is required for that tier.

Useful local commands after init: `seoagent status`, `seoagent keywords --peek "…"`, `seoagent okf scaffold`, `seoagent menu`. Do not invent rankings. Do not publish without the operator.

Hermes notes: `bot-groups/marketing-team/bots/seo-specialist/skills/` (`INDEX.md`, `SKILL.md`).

## Autopilot (optional, paid)

| | Free Skill | Autopilot |
|--|------------|-----------|
| Price | $0 | **$49 / site / month** (7-day trial, no card; then paid) |
| Where | Local CLI + `.seoagent/` | seoagent.com cloud + inbox |
| Needs | Node + `init` + the agent’s model | `seoagent login`, often GSC |
| What | Audit, strategy, briefs, drafts, OKF in-repo | Cloud research, GSC analysis, queued actions, `seoagent process` / `sync` |

`seoagent upgrade` opens pricing. Dragon does **not** require Autopilot to ship. Do not run `seoagent login` unless the operator asks.

## DataForSEO (kept, separate)

`connectors/dataforseo.json` remains the James-locked SERP/keyword MCP (`npx -y dataforseo-mcp-server`). It is **not** the SEOagent tool identity. Autopilot’s cloud keyword feed also uses DataForSEO on their side; UltraDragon can still attach the MCP for live numbers without buying Autopilot.

## What was left out

- AgriciDaniel/claude-seo slash commands (`/seo audit`, 26 leaves, 19 agents) — replaced as SEOagent identity
- Claude Code / Codex **plugin marketplace** (`/plugin marketplace add Baxter-Inc/seoagent-npm`)
- Vendoring the full upstream SKILL bundle + `references/` library (hundreds of lines); `init` installs that into the **operator’s site repo**
- Treating `seoagent process` (Claude Agent SDK) as the default Hermes path
- CMS auto-publish, Firecrawl deep crawl, cloud image autopilot
- Shipping Autopilot as if it were included

## How UltraDragon picks up the change

Apply overwrites group-owned files (`SOUL.md`, `bot.yaml`, `profile.yaml`, `bot.meta.json`, `skills/`) and recopies connectors.

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install a build of this branch). Restart **Dragon AI Agent**.
2. **Teams → Marketing Team → Apply / Launch** (re-apply is fine).
3. BOTS **MARKETING TEAM** still shows **exactly six** seats. No SEOagent row.
4. SEO Specialist `bot.meta.json` `tools` includes `seoagent`. Profile has `skills/SKILL.md`.
5. On the site repo the operator wants audited: `npm install -g @seoagent-official/seoagent` then `seoagent init` (or npx). Optional: wire DataForSEO MCP from `connectors/marketing-team/dataforseo.json`.

## Tests

```bash
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```
