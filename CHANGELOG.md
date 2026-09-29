# Changelog

All notable changes to Dragon AI Agent (packaging/distribution) are documented here.

## [Unreleased]

### Fixed
- **Windows launch showed no UI.** The Desktop / Start Menu **Dragon AI Agent** shortcut ran `start-embedded.ps1`, which only did `docker compose pull && up -d` and then exited. PowerShell `-File` closes that console, Docker is tray-only by design, and the dashboard / agent desktop were never opened — so a normal open looked like nothing happened.
  - Launcher now shows a status window (or a MessageBox / popup on failure).
  - After the gateway is reachable it opens `http://127.0.0.1:9119/` and the agent desktop client when installed.
  - Missing Docker / compose / a dead gateway is an explicit dialog, not a silent exit.
  - Shortcuts start PowerShell `-STA` (needed for WinForms). First-run wizard still opens when welcome is pending.
  - Daily start skips an image pull (`-Pull` to update). Log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`.
  - Smoke: `python3 scripts/airmaze/Test-LaunchSmoke.py` or `start-embedded.ps1 -Smoke`.

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
