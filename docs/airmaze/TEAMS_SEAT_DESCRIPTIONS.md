# Teams picker — seat brief + hover detail

James: under each bot/seat name in the **Teams** dialog, show a **brief** line; on **hover** (and keyboard focus), show a **detailed** write-up. SEO Specialist copy is the seoagent.com seat, not a seventh teammate.

This is packaging overlay only. No `Hermes.exe` rebuild. Bot Screen stays `127.0.0.1:8650` / `dragon-local`. Marketing stays **six** Cos seats.

## Product

| Surface | Copy |
|---------|------|
| Under the seat name | `bots[].description` (brief) |
| Hover / focus popover | `bots[].descriptionDetail` (optional; skip the popover when empty) |

Apply is still the **team** row. Seats are informational. Clicking a seat must not apply a one-bot pack.

The Teams helper (`GET /api/teams` on `127.0.0.1:8653`) already listed team `displayName` + `departmentJob`. It did **not** ship seat rows or a hover field. `description` existed on the group file for deploy/`bot.meta.json`. There was no `descriptionDetail` and no seat list in the overlay. This change extends that schema + UI; it does not invent a second Teams product.

## SEO Specialist (seoagent.com)

**Brief:** `Runs seoagent.com Skill/CLI audits and optional DataForSEO research.`

**Detail** (hover / focus) — Cos’s seat write-up, updated off claude-seo:

- Not a new teammate. Apply Marketing Team still yields six bots. Only this seat gets extra SEO tooling.
- Tools: `seoagent` (seoagent.com free Skill/CLI: `npm i -g @seoagent-official/seoagent` then `seoagent init` / npx), `dataforseo` (MCP), plus `computer-use` and `browser`.
- Optional Autopilot is $49/site/month for GSC/cloud. Not required.
- After install: re-apply Marketing; run `seoagent init` on the site repo; add DataForSEO MCP credentials in desktop MCP settings if using that tool.
- Buffer stays on Social Media Manager. Brevo stays on Lifecycle Marketer.

PR #18 wires those tools on the same seat. This branch starts from **current main** (copy + picker UI only). It does not restack #18.

## Other Marketing seats

Same brief + hover fields. Briefs stay Cos’s one-liners. Hover restates charter, handoff, and (where it matters) Buffer / Brevo. Real Estate and Trading keep `description` as the brief under the name; they omit `descriptionDetail` until someone writes one.

## UX

- Brief is always visible (do not clamp the seat name or the one-liner into an ellipsis-only card).
- Detail is extra: CSS `:hover` / `:focus` / `:focus-within` on a `role="tooltip"` popover. Keyboard users can tab to a seat that has detail.
- Do not nest seat controls inside the Apply button.
- Visible focus ring on the team Apply control and on seats that open a tooltip.
- Do not rely on the native `title` attribute for Cos’s long SEO write-up.

## Out of scope

- A seventh Marketing bot
- Moving Buffer / Brevo onto SEO Specialist
- Vendoring Autopilot or claiming it is free
- Restyling Bot Screen / rebuilding Electron
