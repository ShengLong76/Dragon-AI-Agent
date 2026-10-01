# Dragon AI Agent status

Updated: 2026-09-29 (Electron UI product overlay)

## v0.1.0 packaging (this repo)

- Distribution package built under Cos box `/workspace/airmaze-agent-dist/`
- Product name: **Dragon AI Agent** (`DragonAIAgentSetup.exe`, install dir `%LOCALAPPDATA%\DragonAIAgent`)
- Windows installer provisions WSL2 (best-effort), Docker Desktop (tray-minimized, no dashboard popup), embedded gateway, **bot group dropdown / deploy**
- Catalog includes Personal Assistant and Real Estate Cold Call Lead Refresher bot groups
- Agent desktop client remains a separate installer when not already present
- Does **not** clone upstream agent source onto Cos; does **not** push remotes in this packaging step

## Honesty

Silent full provision of WSL + Docker may still need reboot / user clicks. Docker UI is suppressed on startup by settings patch + headless-friendly launch; tray icon remains available. Connector templates are placeholders only.

**Bot Screen (2026-09-29):** Local / This device Screen still fails by upstream design on Windows. Desktop Remote against `:8642` or gated `:9119` also fails (no Desktop `/api/ws` token path). This revision adds loopback `hermes serve` + `:8650` proxy and auto-wires `connections.json`. End-to-end live preview still needs UltraDragon re-smoke after deploy — this box cannot open Hermes.exe. If the image lacks `serve`/`dashboard`, say so from `docker logs hermes-airmaze-desktop`; next repo is a `hermes-agent` image fork, not another nginx health fake.

**In-app branding (2026-09-30):** Empty state, composer placeholder, and settings product copy are overlaid on the unpacked Electron renderer at launch (`Apply-DesktopBranding.ps1`). The empty-state wordmark is **Syne** 700 in front of a larger unboxed navy dragon (no black plate). The Bots rail hides the built-in default Hermes agent so **Personal Assistant** is the user-facing bot. `Hermes.exe` / tray / AppUserModelID / `app.asar` still need a rebuilt desktop binary. Bot Screen ports and tokens are unchanged.

**Voice chat (2026-10-01):** Composer overlay adds **Grok** beside existing **GPT** voice. GPT-Live is not replaced. **Talk with Grok** hosts official xAI full duplex (`wss://api.x.ai/v1/realtime?model=grok-voice-latest` + `POST /v1/realtime/client_secrets`). Hermes still rejects `grok-live`, so Grok writes `chained` while the overlay owns duplex. Helper `127.0.0.1:8654`. See `docs/airmaze/VOICE.md`.
