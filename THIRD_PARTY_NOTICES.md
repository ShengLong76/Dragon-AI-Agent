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
- Gateway API key: `dragon-local` (`API_SERVER_KEY`; host publish is `127.0.0.1:8642` only)
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

## Bot Screen documentation

Upstream feature documentation (public):  
https://hermes-agent.nousresearch.com/docs/user-guide/features/bot-screen
