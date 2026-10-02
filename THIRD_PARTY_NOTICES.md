# Third-party notices

Dragon AI Agent is a packaging/distribution product. Runtime pulls an upstream Docker image and may interact with a separately installed agent desktop client.

## Upstream agent image (technical)

| Item | Value |
|------|--------|
| Image | `nousresearch/hermes-agent:latest-desktop` |
| Project | https://github.com/NousResearch/hermes-agent |
| License | MIT © 2025 Nous Research |

This packaging repo is **not** a full source fork. Retain upstream copyright notices when redistributing upstream-derived materials.

## Local dashboard credentials (compose defaults)

Configured in `docker-compose.embedded.yml` for **loopback-only** use (upstream env names):

- Dashboard user: `dragon` (`HERMES_DASHBOARD_BASIC_AUTH_USERNAME`)
- Dashboard password: `dragon-local`
- Gateway API key: `dragon-local-key` (`API_SERVER_KEY`, ≥16 chars so current `-desktop` images bind `:8642`; host publish is `127.0.0.1:8642` only)
- Desktop serve session token: `dragon-local` (`HERMES_DASHBOARD_SESSION_TOKEN`; host publish is `127.0.0.1:8650` only)

Change these before exposing anything beyond `127.0.0.1`.

## Internal identifiers (unchanged)

Container name `hermes-airmaze-gw`, compose project/env vars (`HERMES_*`), and data dir `%USERPROFILE%\.hermes-airmaze-embedded` are technical identifiers kept for compatibility. User-facing product name is **Dragon AI Agent**; install dir is `%LOCALAPPDATA%\DragonAIAgent`.

## Syne (in-window wordmark font)

Bundled under `branding/fonts/syne/` and copied into the unpacked Electron renderer by the launch overlay.

| Item | Value |
|------|--------|
| Family | Syne |
| License | SIL Open Font License 1.1 |
| Authors | The Syne Project Authors |
| Upstream | https://gitlab.com/bonjour-monde/fonderie/syne-typeface |

This is **not** Universal Sans, Gotham, or any proprietary Tesla face. Syne (weight 700 on the wordmark) replaces the upstream Hermes **Collapse** display face.

## UI UX Pro Max (design skill, open-source)

Installed for Cursor at `.cursor/skills/ui-ux-pro-max` via `npx ui-ux-pro-max-cli init --ai cursor`. Used to generate the Dragon AI Agent design system. Paid brand/logo extras from the CLI are **not** vendored.

| Item | Value |
|------|--------|
| Project | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill |
| License | MIT |
| Package | `ui-ux-pro-max-cli` |

## Bot Screen documentation

Upstream feature documentation (public):  
https://hermes-agent.nousresearch.com/docs/user-guide/features/bot-screen

## Understand Anything (Cursor skill / plugin pointer)

Vendored under `.cursor/skills/understand-anything/` and `.cursor-plugin/plugin.json` so Cursor and cloud agents can map this repo later. This packaging tree does **not** ship a generated knowledge graph (`.ua/` is gitignored) and does not vendor paid extras.

| Item | Value |
|------|--------|
| Project | https://github.com/Egonex-AI/Understand-Anything |
| License | MIT © 2026 Yuxiang Lin and Infinite Universe, Inc. |
| Commands | `/understand`, `/understand-dashboard` |
| Graph dir | `.ua/` (gitignored) |

How to run the first scan later: `docs/airmaze/UNDERSTAND_ANYTHING.md`.

## SEOAgent (seoagent.com) on SEO Specialist

Marketing Team **SEO Specialist** ships Hermes instructions for the official SEOAgent CLI/Skill. The Claude Code plugin marketplace and Autopilot cloud runtime are **not** vendored. DataForSEO MCP stays a separate connector.

| Item | Value |
|------|--------|
| Product | https://seoagent.com |
| Project | https://github.com/Baxter-Inc/seoagent-npm |
| Package | `@seoagent-official/seoagent` |
| License | MIT © 2026 Baxter Inc |
| Adapted path | `bot-groups/marketing-team/bots/seo-specialist/skills/` |
| Design | `docs/airmaze/SEOAGENT.md` |

| Item | Value |
|------|--------|
| DataForSEO MCP | https://github.com/dataforseo/mcp-server-typescript |
| Package | `dataforseo-mcp-server` |
