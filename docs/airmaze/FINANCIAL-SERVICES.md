# Trading Team — Financial Services on Market Researcher

James locked an **adapted** [anthropics/financial-services](https://github.com/anthropics/financial-services) skill/docs pack (Apache-2.0) on the existing **Market Researcher** seat. Not a fifth Trading bot. Not a Finance or Investment team.

The pack is local Hermes guidance (research notes, earnings/comps-style drafts). **Do not** require Claude Cowork or Anthropic Managed Agents. **Do not** ship the Cowork plugins wholesale.

Nothing here is investment advice. Trading Team stays a discretionary desk recipe pack. Not a broker: no orders, no brokerage credentials.

## Decision

| Keep | Change |
|------|--------|
| Four Cos Trading seats | Market Researcher `tools` includes `financial-services` (plus `computer-use` / `browser`) |
| Paper/read-only; not a broker | Local `skills/` + `connectors/financial-services.json` (`type: docs`) |
| Other seats’ tools (`computer-use`, `browser`) | Unchanged |

Seats stay:

1. Market Researcher
2. Trade Journal
3. Risk Analyst
4. News Scanner

## Task plan

1. Design this note (adapted skill/docs vs Cowork plugins left out).
2. Tests: four seats; `financial-services` on Market Researcher only; no FactSet/OpenBB wiring; no Cowork installer.
3. Hermes skill instructions + `connectors/financial-services.json`.
4. Re-apply Trading Team.

## How Trading bots declare tools today

Same contract as Marketing SEOagent (`docs/airmaze/SEOAGENT.md`, `docs/airmaze/BOT_GROUPS.md`):

- `bots[].tools` — ids the bot may use
- Optional `connectors[]` + `connectors/*.json` — non-secret placeholders
- Deploy writes tools into `%LOCALAPPDATA%\hermes\profiles\<bot-id>\bot.meta.json` and copies `bots/<id>/skills/` when present

## What Market Researcher runs (local skill/docs)

There is **no installable CLI or npm package**. The connector type is `docs`, not `cli`. Hermes reads `bots/market-researcher/skills/` (`INDEX.md`, `SKILL.md`).

Workflows (paper/read-only), from operator files and public pages the operator names:

- Sector / theme primer: overview, competitive landscape, peer comps, ideas shortlist as a **draft**
- Earnings-style note from a transcript or filing the operator provides
- Cite every number; mark `[UNSOURCED]`; stop for operator review

Useful after apply: re-apply Trading Team so `skills/` and the `financial-services` tool id land on the profile. Do not invent prices. Do not place orders.

## What was left out

- Claude Cowork / Claude Code **plugin marketplace** (`claude plugin marketplace add anthropics/financial-services`)
- Vendoring the full upstream agent plugins, vertical skills, and Managed Agent cookbooks
- Paid vendor MCPs from the upstream kit (FactSet, Morningstar, S&P, Daloopa, Moody’s, LSEG, PitchBook, and others) — optional later, not in this pack
- OpenBB (separate later)
- Live trading / broker APIs
- A new Finance or Investment team, or extra seats

## How UltraDragon picks up the change

Apply overwrites group-owned files (`SOUL.md`, `bot.yaml`, `profile.yaml`, `bot.meta.json`, `skills/`) and recopies connectors.

1. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or install a build of this branch). Restart **Dragon AI Agent**.
2. **Teams → Trading Team → Apply / Launch** (re-apply is fine).
3. BOTS **TRADING TEAM** still shows **exactly four** seats. No Financial Services row.
4. Market Researcher `bot.meta.json` `tools` includes `financial-services`. Profile has `skills/SKILL.md`.
5. Work from operator-supplied notes and public filings. Do not wire FactSet or OpenBB from this pack.

## Tests

```bash
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-LaunchSmoke.py
```
