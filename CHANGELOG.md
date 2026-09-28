# Changelog

All notable changes to Dragon AI Agent (packaging/distribution) are documented here.

## [0.1.0] — 2026-09-28

### Added
- First distribution package for Windows amd64 under product name **Dragon AI Agent**.
- Embedded gateway via Docker Compose (image documented in `THIRD_PARTY_NOTICES.md`).
- Loopback-only ports: gateway `127.0.0.1:8642`, dashboard `127.0.0.1:9119`.
- **Profile catalog** with select/import:
  - `profiles/catalog.json`
  - Personal Assistant (minimal single-bot)
  - **Real Estate Cold Call Lead Refresher** (Lead Sourcer, Cold Call Script Writer, Follow-up Sequencer + CRM/dialer/property-data/MCP placeholders)
  - Scripts: `Apply-Profile.ps1`, `Select-Profile.ps1`, `Import-Profile.ps1`
- Windows bootstrap installer (`scripts/airmaze/install.ps1` / `installer/DragonAIAgentSetup.ps1`):
  - Best-effort WSL2 enable / `wsl --install`
  - Best-effort Docker Desktop detect / install / download-page fallback
  - Docker Desktop **tray-only** (no dashboard on startup)
  - Compose pull + `up -d`
  - First-run profile menu
  - Desktop + Start Menu shortcuts (“Dragon AI Agent”, “Dragon AI Agent Profiles”)
  - Install log at `%LOCALAPPDATA%\DragonAIAgent\install.log`
- Console `DragonAIAgentSetup.exe` (Go, branded icon when embedded) that runs sibling `payload\install.ps1`.
- Logo assets: `dragon-ai-agent-logo.png` / `.ico`
- Docs under `docs/airmaze/` (architecture, embedded gateway, upstream notes, status).

### Notes / limitations
- Agent desktop client is a separate installer when not already present.
- Full silent WSL/Docker provision may require reboot and/or user UI clicks.
- Connector JSON files are placeholders — no live API keys ship in the package.
- v0.1.0 provisions the embedded gateway + profiles only; it does not ship upstream agent source.
