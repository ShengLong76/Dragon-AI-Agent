# Changelog

All notable changes to Dragon AI Agent (packaging/distribution) are documented here.

## [Unreleased]

### Changed
- **Product mark is James’s navy low-poly dragon.** Front-facing, coiled neck, few large facets, horns the same navy as the body, red eyes. No gold horns, no copper ring, not a side profile. PNG cropped from the attached mark; overlay pins it on the empty-state intro. Syne 700 and Bot Screen `:8650` / `dragon-local` unchanged.
- **Desktop chrome follows a UI UX Pro Max design system.** The open-source Cursor skill is in-repo (`.cursor/skills/ui-ux-pro-max`). Generator note: `design-system/dragon-ai-agent/MASTER.md`; applied override: `pages/desktop-client.md` and `docs/airmaze/DESIGN.md`. Overlay CSS now ships AI-Native tokens (dark `#1C1C20`, crimson `#C41E3A`), a visible composer focus ring, and `prefers-reduced-motion`. **Syne 700** stays the wordmark. Catalog Inter / AI purple and paid brand/logo extras are not shipped. Bot Screen `:8650` / `dragon-local` unchanged.
- **Empty-state wordmark face is Syne** (SIL OFL 1.1, weight **700**), not upstream **Collapse-Bold**. The red-boxed `DRAGON AI AGENT` lettering uses `.wordmark { font-family: 'Collapse' }` (high-contrast display). The overlay rewrites that family, bundles the variable + 700 `woff2` files, and injects CSS so UltraDragon does not need a system font. Universal Sans / Gotham / Tesla faces are proprietary and are **not** shipped. Composer/settings chrome use the same family. `Hermes.exe` and Bot Screen `:8650` / `dragon-local` are unchanged. See `docs/airmaze/BRANDING.md`.
- **In-app Electron chrome is Dragon AI Agent.** This repo still launches upstream `Hermes.exe` (no `apps/desktop` source, no rebuild). A launch-time overlay rewrites unpacked renderer strings (`resources/app.asar.unpacked/dist`): empty-state **HERMES AGENT** → **DRAGON AI AGENT**, composer **Give Hermes a task** → **Give Dragon AI a task**, and settings/About **Hermes Agent** product copy. `app.asar` is left intact (integrity). Tray, exe name, AppUserModelID, Hermes Cloud, and license attribution still need an upstream Electron rebuild — see `docs/airmaze/BRANDING.md`. Check: `python3 scripts/airmaze/Test-DesktopBranding.py`.

### Fixed
- **Bot Screen on UltraDragon (Remote vs Grok Bot parity).** Local / This device Screen still correctly says Linux-gateway-only. Adding Desktop Remote → `http://127.0.0.1:8642` + `API_SERVER_KEY` failed: that port is the OpenAI API (`/health`, Bearer), not Desktop `hermes serve` (`/api/health`, `X-Hermes-Session-Token`, `/api/ws?token=`, display ticket). Gated dashboard `:9119` can look ready after a header translator, then dies with **WebSocket error before open** (upstream [hermes-agent#106685](https://github.com/NousResearch/hermes-agent/issues/106685): token-mode WS is refused on a non-loopback bind).
  - Compose now runs a sidecar `hermes serve --host 127.0.0.1 --port 8651` (token auth stays on) plus a TCP proxy published at `127.0.0.1:8650`.
  - Launcher waits for `/api/health` on `:8650`, mirrors applied bots into `.hermes-airmaze-embedded/profiles`, and upserts `%APPDATA%\Hermes\connections.json` Remote **Embedded Linux** (rewrites a leftover `:8642` Remote).
  - Docs no longer tell operators to point Desktop Remote at `:8642` for Screen. Offline check: `python3 scripts/airmaze/Test-DesktopServeAdapter.py`.
  - If the official image has no `serve`/`dashboard` WebSocket surface, `docker logs hermes-airmaze-desktop` will say so — next step is a `hermes-agent` image fork, not another fake `/api/health`.
- **Windows launch showed no UI (UltraDragon repro).** The Desktop / Start Menu shortcut ran `start-embedded.ps1` only (`docker compose pull && up -d`, no `-NoExit`). Compose connect/pipe errors were not fatal (exit 0 + success URLs). `Start-AgentDesktop` missed the real client at `%LOCALAPPDATA%\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`. Dashboard `9119` crash-looped (wrong basic-auth env names). Gateway `8642` was healthy inside the container but connection-closed from Windows (`API_SERVER_HOST` default loopback). Setup wizard WinForms died on `OrderedDictionary.ContainsKey` and `[Drawing.Color]` before `Add-Type`.
  - Launcher starts Docker, treats compose/pipe/container failures as **fatal** (dialog + exit 1), waits for host HTTP on `127.0.0.1:8642`, then launches **Hermes.exe** (or a blocking “client not found” dialog).
  - Discovery includes the unpacked Electron path; writes `%LOCALAPPDATA%\DragonAIAgent\desktop-client.json` + `Dragon AI Agent Client.lnk` (do not copy the exe out of `win-unpacked`).
  - Compose: `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` + password/secret; `API_SERVER_ENABLED=true`, `API_SERVER_HOST=0.0.0.0`, local-only `API_SERVER_KEY=dragon-local` (host publish stays `127.0.0.1`).
  - Wizard: load System.Drawing first; IDictionary uses `.Contains()`.
  - Shortcuts: PowerShell `-STA`. Daily start skips image pull (`-Pull` to update). Log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`.
  - Smoke: `python3 scripts/airmaze/Test-LaunchSmoke.py` or `start-embedded.ps1 -Smoke`.
- **Customer-facing branding is Dragon AI Agent** (not Hermes/AirMaze as the product). Shortcuts, wizard, installer resources, dashboard login (`dragon` / `dragon-local`), and profile labels updated. Window title is wrapped after launch. Tray / About / `productName` still need a rebuilt Electron binary — see `docs/airmaze/BRANDING.md`. Logo: `branding/dragon-ai-agent-logo.*`.
- **Clean launch (no PowerShell console).** Desktop / Start Menu **Dragon AI Agent** targets `wscript.exe` + `Start-DragonAI.vbs`, which runs `start-embedded.ps1` hidden (`-NoLogo -NonInteractive -WindowStyle Hidden -SilentHost`). Failures are MessageBox / WinForms only — never `Read-Host` on a hidden console. The :9119 dashboard is not opened on start (Start Menu **Dragon AI Agent Dashboard** is optional). `start-embedded.ps1` remains for debug (`-DebugConsole`). Old powershell.exe product shortcuts are rewritten to the windowless host on the next launch.
- **Healthy compose no longer exits 1.** Docker CLI progress on stderr (`Container … Running`) was treated as terminating under `$ErrorActionPreference=Stop`. `Invoke-NativeDocker` sets Continue and stringifies stderr for compose / inspect / info.
- **UltraDragon re-smoke.** Normal start does **not** open `:9119` (only `-OpenDashboard` or Start Menu Dashboard). Docker engine down is **fail-closed** (dialog + exit 1); `-StartDocker` is opt-in auto-start. Product `.lnk` is rewritten by `Start-DragonAI.vbs` to `wscript.exe` so the console never appears. Window title wrap enumerates Hermes windows.

## [0.1.0] — 2026-09-28

### Added
- First distribution package for Windows amd64 under product name **Dragon AI Agent**.
- Embedded gateway via Docker Compose (image documented in `THIRD_PARTY_NOTICES.md`).
- Loopback-only ports: gateway `127.0.0.1:8642`, dashboard `127.0.0.1:9119`.
- **Profile catalog** with select/import:
  - `profiles/catalog.json`
  - Personal Assistant (minimal single-bot)
  - **Real Estate Cold Call Lead Refresher** (Lead Sourcer, **Email Warmer**, Cold Call Script Writer, Follow-up Sequencer + CRM/email/consent-form/dialer/property-data/MCP placeholders)
  - Scripts: `Apply-Profile.ps1`, `Select-Profile.ps1`, `Import-Profile.ps1`
- Windows bootstrap installer (`scripts/airmaze/install.ps1` / `installer/DragonAIAgentSetup.ps1`):
  - Best-effort WSL2 enable / `wsl --install`
  - Best-effort Docker Desktop detect / install / download-page fallback
  - Docker Desktop **tray-only** (no dashboard on startup)
  - Compose pull + `up -d`
  - First-run profile menu
  - Desktop + Start Menu shortcuts (“Dragon AI Agent”, “Dragon AI Agent Profiles”, “Dragon AI Agent Setup”)
  - Install log at `%LOCALAPPDATA%\DragonAIAgent\install.log`
- Console `DragonAIAgentSetup.exe` (Go, branded icon when embedded) that runs sibling `payload\install.ps1`.
- Logo assets: `dragon-ai-agent-logo.png` / `.ico`
- **Email Warmer** bot in Real Estate pack: CAN-SPAM warming → hosted TCPA consent form → Vtiger consent fields → dial-ready handoff only
- Docs under `docs/airmaze/` (architecture, embedded gateway, upstream notes, status).
- **First-run onboarding wizard** (`scripts/airmaze/Onboard-Wizard.ps1`) + DPAPI secure store (`DragonAI-SecureStore.ps1`):
  - Steps: Welcome → Email → CRM (Vtiger) → Telephony (Twilio + Bland/Vapi) → optional property-data/dialer → Review
  - Secrets only as DPAPI binary files under `%LOCALAPPDATA%\DragonAIAgent\onboarding\secrets\`
  - Bot readiness (`bots-status.json`): Real Estate bots stay `needs_setup` until email+crm+telephony succeed
  - Installer invokes wizard after profile setup; Start Menu / Desktop **Dragon AI Agent Setup** shortcut
- `docs/airmaze/SETUP_GUIDE.md` — markdown mirror of wizard steps + Real Estate Lead Sourcer → Email Warmer → consent gate → calling

### Notes / limitations
- Agent desktop client is a separate installer when not already present.
- Full silent WSL/Docker provision may require reboot and/or user UI clicks.
- Connector JSON files are placeholders — no live API keys ship in the package.
- v0.1.0 provisions the embedded gateway + profiles only; it does not ship upstream agent source.
