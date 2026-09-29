# Dragon AI Agent status

Updated: 2026-09-29 (Bot Screen Desktop serve adapter)

## v0.1.0 packaging (this repo)

- Distribution package built under Cos box `/workspace/airmaze-agent-dist/`
- Product name: **Dragon AI Agent** (`DragonAIAgentSetup.exe`, install dir `%LOCALAPPDATA%\DragonAIAgent`)
- Windows installer provisions WSL2 (best-effort), Docker Desktop (tray-minimized, no dashboard popup), embedded gateway, **profile select/import**
- Catalog includes Personal Assistant and Real Estate Cold Call Lead Refresher
- Agent desktop client remains a separate installer when not already present
- Does **not** clone upstream agent source onto Cos; does **not** push remotes in this packaging step

## Honesty

Silent full provision of WSL + Docker may still need reboot / user clicks. Docker UI is suppressed on startup by settings patch + headless-friendly launch; tray icon remains available. Connector templates are placeholders only.

**Bot Screen (2026-09-29):** Local / This device Screen still fails by upstream design on Windows. Desktop Remote against `:8642` or gated `:9119` also fails (no Desktop `/api/ws` token path). This revision adds loopback `hermes serve` + `:8650` proxy and auto-wires `connections.json`. End-to-end live preview still needs UltraDragon re-smoke after deploy — this box cannot open Hermes.exe. If the image lacks `serve`/`dashboard`, say so from `docker logs hermes-airmaze-desktop`; next repo is a `hermes-agent` image fork, not another nginx health fake.
