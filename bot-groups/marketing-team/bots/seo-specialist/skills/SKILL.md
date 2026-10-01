# SEOAgent — Hermes skill (seoagent.com)

Adapted onboarding for Dragon AI Agent from the official Skill at [Baxter-Inc/seoagent-npm](https://github.com/Baxter-Inc/seoagent-npm). Full protocols land in the **operator’s site repo** after `init`. Do not vendor the Claude Code plugin here.

## When

The operator wants SEO help (audit, keywords, briefs, on-page notes) and you are **SEO Specialist**.

## Install / run (free Skill)

From the site repository root (Node.js ≥ 20):

```bash
npm install -g @seoagent-official/seoagent
seoagent init
```

Or one-shot: `npx -y @seoagent-official/seoagent@latest init`

CI / no prompts: `seoagent init --yes --domain example.com`

`init` creates `.seoagent/` (audit, strategy, briefs, content, roadmap) and installs the project-local skill. Work persists there. Use the agent’s own model — no seoagent.com account for this tier.

After init: `seoagent status`, `seoagent keywords --peek "query"`, `seoagent okf scaffold`, `seoagent menu`. Read `.seoagent/audit/latest.md` and hand briefs to Content Strategist.

Do not invent rankings or traffic. Do not edit production or commit `.seoagent/` secrets without the operator.

## Autopilot (paid, optional)

Autopilot is **$49 per site per month** (7-day no-card trial, then paid). It is **not** included with the free Skill. It adds cloud research, GSC analysis, and an inbox (`seoagent login`, `sync`, `process`). Only if the operator asks. `seoagent upgrade` opens pricing.

## DataForSEO

A separate Marketing connector (`dataforseo`) may already be attached for live SERP/keyword MCP. That is not this CLI. Prefer operator-supplied or DataForSEO MCP numbers when the CLI peek is unavailable.
