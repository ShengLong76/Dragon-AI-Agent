# Dragon AI Agent

**Version:** 0.1.0  
**Product:** Dragon AI Agent — Windows packaging that provisions an embedded Linux gateway (Bot Screen capable) via Docker Desktop, plus **bot groups** (department-level sets of bots) fetched from this GitHub repo.

Compatible with the open-source agent desktop stack (separate desktop client). This tree ships compose, Windows bootstrap, docs, bot groups, and connector placeholders — not a full upstream agent source fork. Bot groups are a customization layer; an upstream sync of the desktop agent must not wipe `bot-groups/`.

---

## What v0.1.0 does

| Step | Behavior |
|------|----------|
| WSL2 | Best-effort check / enable (`wsl --install` if missing). **Reboot may be required.** |
| Docker Desktop | Detect; quiet install when possible; else open download page. Configured to **start minimized to the system tray** (no dashboard window on launch). |
| Embedded gateway | `docker compose` pull + `up -d` for the packaged embedded gateway image (see `THIRD_PARTY_NOTICES.md`). |
| Ports | `127.0.0.1:8650` (Desktop Remote / Bot Screen), `127.0.0.1:8642` (OpenAI API), `127.0.0.1:9119` (browser dashboard). Local credentials: see `docs/airmaze/EMBEDDED_GATEWAY.md`. |
| **Bot groups / Teams** | In-app **Teams Marketplace** popup (sidebar + first-run) browses GitHub catalog packs (Real Estate Lead Gen, Marketing Team, Trading Team): brief, 4-column seat cards, author, required connectors. **Install** / **Launch** files bots under that name, not Unassigned. **Export** scrubs secrets. Import stays. Personal Assistant is already installed and is not a Teams row. |
| **Onboarding** | First-run **in-app Models UI** (chat + image LLM defaults via `Apply-GatewayModels`). Connector steps (email / CRM / telephony) stay in `docs/airmaze/SETUP_GUIDE.md`. The WinForms **Dragon AI Agent Setup** wizard is deprecated (no Desktop / Start Menu shortcut). Real Estate bots stay `needs_setup` until required connectors succeed. |
| Agent desktop | Copies standalone `Hermes.exe` into a **private** `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked` tree and sets `HERMES_DESKTOP_USER_DATA_DIR=%LOCALAPPDATA%\DragonAIAgent\electron-userdata`. Branding/window rename apply only there (refused outside `DragonAIAgent`). Standalone Hermes, including `%APPDATA%\Hermes\connections.json` primary=`local`, is not mutated. Overlay: empty state **DRAGON AI AGENT**, sidebar **Dragon AI**, **Give Dragon AI a task**, **Syne**, **Personal Assistant** only. Dashboard login: `dragon` / `dragon-local`. |

Be honest about limits: full silent WSL/Docker provision often needs a reboot and/or one-time UI clicks. This package does **not** embed the agent desktop client itself.

---

## Quick start (Windows)

1. Unzip `Dragon-AI-Agent-v0.1.0-windows.zip`.
2. Run `DragonAIAgentSetup.exe` (console; shows progress). It looks for `payload\install.ps1` beside itself.
3. Or run manually:

```powershell
cd Dragon-AI-Agent-v0.1.0-windows\payload
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Install log: `%LOCALAPPDATA%\DragonAIAgent\install.log`  
Package files land in: `%LOCALAPPDATA%\DragonAIAgent\`  
Gateway data: `%USERPROFILE%\.hermes-airmaze-embedded` (internal)

Desktop / Start Menu shortcuts: **Dragon AI Agent** only (the product launcher). There are no **Bot Groups**, **Dashboard**, **Profiles**, or **Setup** shortcuts. Leftover `.lnk` files from older installs are deleted on install and on the next launch.

Opening **Dragon AI Agent** uses a windowless host (`Start-DragonAI.vbs` / `wscript.exe`) — no PowerShell console. The VBS sets `HERMES_DESKTOP_USER_DATA_DIR` and `start-embedded.ps1` launches the **private** desktop client. If Docker is not running it starts **Docker Desktop in the system tray** (no Containers dashboard), then starts the gateway **and** the Desktop-compatible Linux `hermes serve` (published at `http://127.0.0.1:8650`), writes the Remote connection into Dragon `electron-userdata`, and opens the **private desktop client** (not the :9119 dashboard). Standalone Hermes primary stays local. Already-running Docker is a no-op. Failures after a bounded wait are a MessageBox. **This device** Screen is Linux-only by upstream design — use the Embedded Linux Remote. Optional dashboard: `start-embedded.ps1 -OpenDashboard`. Debug: run `start-embedded.ps1` in a console. Launch log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`. Branding: [`docs/airmaze/BRANDING.md`](docs/airmaze/BRANDING.md). Design: [`docs/airmaze/DESIGN.md`](docs/airmaze/DESIGN.md). Docker launch: [`docs/airmaze/DOCKER_LAUNCH.md`](docs/airmaze/DOCKER_LAUNCH.md).

```powershell
# Same path the shortcut uses (no secrets)
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\DragonAIAgent\scripts\airmaze\start-embedded.ps1"

# Offline contract check (repo checkout; Linux-safe)
python3 scripts/airmaze/Test-LaunchSmoke.py
```

---

## Bot groups (Teams Marketplace popup from this GitHub repo)

A **bot group** is a department-level set of bots (a security team, a research team, a real-estate team). Each bot has a **title**, **description**, and **tools**. Bots exist because a group defines them — there is no Grokbot-style create-a-bot path. Deploy and import file those bots into a **named BOTS section** labeled with the pack display name (not UNASSIGNED). Design: [`docs/airmaze/BOT_GROUPS.md`](docs/airmaze/BOT_GROUPS.md).

The Teams Marketplace popup fetches `bot-groups/catalog.json` from https://github.com/ShengLong76/airmaze-agent. It does not hard-code the list. Browse a pack and click **Install** to add that team's bots. **Launch**, **Export**, and **Import** stay. **Export** writes a scrubbed catalog-ready zip. When GitHub is unreachable, the last cache then the bundled catalog is used. Design: [`docs/airmaze/TEAMS_POPUP.md`](docs/airmaze/TEAMS_POPUP.md), [`docs/airmaze/TEAMS_MARKETPLACE.md`](docs/airmaze/TEAMS_MARKETPLACE.md).

### Catalog (`bot-groups/catalog.json`)

| Id | Name | Bots |
|----|------|------|
| `personal-assistant` | Personal Assistant | 1 — general PA (sidebar default; not a Teams row) |
| `real-estate-cold-call-lead-refresher` | Real Estate Lead Gen | 4 — Lead Sourcer, Email Warmer, Cold Call Script Writer, Follow-up Sequencer |
| `marketing-team` | Marketing Team | 6 — Cos marketing roster (SEO Specialist: seoagent.com CLI + Skill; DataForSEO connector kept) |
| `trading-team` | Trading Team | 4 — Cos trading roster |

### Scripts

```powershell
# Teams Marketplace popup (lists from GitHub)
.\scripts\airmaze\Select-BotGroup.ps1

# Deploy one group with no manual file handling
.\scripts\airmaze\Deploy-BotGroup.ps1 -BotGroupId real-estate-cold-call-lead-refresher

# Export (same format the repo stores; re-importable)
.\scripts\airmaze\Export-BotGroup.ps1 -BotGroupId real-estate-cold-call-lead-refresher -Destination C:\export\re

# Re-import an exported group file
.\scripts\airmaze\Import-BotGroup.ps1 -SourcePath C:\export\re.zip
```

```bash
python3 scripts/airmaze/Test-BotGroups.py
```

**On deploy:** each bot is copied to `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` (upstream desktop / Bot Screen picker path — not renamed). Connector JSON lands under `%LOCALAPPDATA%\DragonAIAgent\connectors\<group-id>\`. Active selection is `%LOCALAPPDATA%\DragonAIAgent\active-bot-group.json`.

An old `profile.json` still loads once (`displayName` → name/title). There is no Profiles UI.

Singular import/export of one bot is an optional toggle (`allowSingularBotImportExport`), **off by default**.

---

## First-run models + setup guide

Open **Dragon AI Agent** (Desktop / Start Menu launcher). First-run chat + image LLM defaults are written by `Apply-GatewayModels.ps1` (`Grok` / **Grok Imagine**) when those keys are missing. Change them in the **in-app Models UI**. There is no **Dragon AI Agent Setup** Desktop / Start Menu shortcut; the WinForms `Onboard-Wizard.ps1` path is deprecated.

Connector steps (email / CRM / telephony) for Real Estate packs are documented in [`docs/airmaze/SETUP_GUIDE.md`](docs/airmaze/SETUP_GUIDE.md). Secrets, when used, stay in **Windows DPAPI** under `%LOCALAPPDATA%\DragonAIAgent\onboarding\secrets\` — never in plaintext JSON. Real Estate bots remain **`needs_setup`** until email + CRM + telephony succeed.

Voice chat: Settings → Voice → Voice conversation mode lists **Chained**, **Gpt-live**, and **Grok Voice**. **GPT** stays (`gpt-live`); **Grok Voice** writes `grok-live` (xAI realtime, not OpenAI) and keeps overlay full duplex via `grok-voice-latest`. [`docs/airmaze/VOICE.md`](docs/airmaze/VOICE.md).

---

## Docker Desktop: tray only (no dashboard popup)

The installer patches Docker Desktop settings (when present) so the app opens **without** showing the dashboard window:

- `%APPDATA%\Docker\settings.json` and/or `settings-store.json`
- Keys such as `openUIOnStartupDisabled: true` (and related open-at-login / tray preferences)

It starts the Docker engine in a headless-friendly way (service / `Docker Desktop.exe` without forcing the UI). You can still open the dashboard later from the tray icon if needed.

---

## Personal Assistant (minimal catalog entry)

| Field | Value |
|-------|--------|
| Display name | Personal Assistant |
| Slug | `personal-assistant` |
| Role | General-purpose PA: research, drafting, scheduling, reminders, computer-use on a virtualized desktop. Neutral; no business-specific instructions. |

Also see `bot-groups/personal-assistant/`. The leftover `templates/profiles/personal-assistant/` files are not a UI.

---

## Repo layout

```
README.md
LICENSE
THIRD_PARTY_NOTICES.md
CHANGELOG.md
PACKAGING.md
.cursor/skills/ui-ux-pro-max/
.cursor/skills/understand-anything/
.cursor-plugin/plugin.json
docs/airmaze/
docker-compose.embedded.yml
bot-groups/
  catalog.json
  personal-assistant/
  real-estate-cold-call-lead-refresher/
scripts/airmaze/
  install.ps1
  start-embedded.ps1
  Start-DragonAI.vbs
  Find-HermesDesktop.ps1
  private_desktop.py
  Test-PrivateDesktop.py
  Apply-DesktopBranding.ps1
  desktop_branding.py
  desktop_branding.json
  Test-DesktopBranding.py
  Test-LaunchSmoke.py
  Test-WindowsLaunchParse.py
  Test-DesktopServeAdapter.py
  Test-GatewayVolumeHeal.py
  Test-UnderstandAnything.py
  Test-BotGroups.py
  bot_groups.py
  Select-BotGroup.ps1
  Deploy-BotGroup.ps1
  Export-BotGroup.ps1
  Import-BotGroup.ps1
  apply-default-bot-group.ps1
  desktop-loopback-proxy.py
  start-desktop-serve.sh
  start-desktop-proxy.sh
  start-gateway.sh
  embedded_desktop_connection.py
  Set-EmbeddedDesktopConnection.ps1
  Onboard-Wizard.ps1
  DragonAI-SecureStore.ps1
templates/profiles/personal-assistant/
installer/
  DragonAIAgentSetup.ps1
  build-exe.go
branding/   (release: dragon-ai-agent-logo.png / .svg / .ico — James’s navy coiled mark; fonts/syne — OFL wordmark face)
design-system/dragon-ai-agent/   (UI UX Pro Max MASTER + desktop-client override)
```

---

## Docs

1. Bot Screen feature docs — see links in `docs/airmaze/UPSTREAM_NOTES.md` and `THIRD_PARTY_NOTICES.md`
2. `docs/airmaze/ARCHITECTURE.md` — embed Bot Screen on Windows via Docker
3. `docs/airmaze/EMBEDDED_GATEWAY.md` — ports (`:8650` Desktop serve), compose, UltraDragon re-smoke
4. `docs/airmaze/PRIVATE_DESKTOP.md` — Dragon private `win-unpacked` + userdata; standalone Hermes untouched
5. `docs/airmaze/UPSTREAM_NOTES.md` — Linux-gateway-only + Desktop token/WS vs `gateway run`
6. `docs/airmaze/SETUP_GUIDE.md` — first-run onboarding (email / CRM / telephony) + Real Estate flow
7. `docs/airmaze/BOT_GROUPS.md` — bot groups (data model, GitHub list, export, singular toggle)
8. `docs/airmaze/TEAMS_POPUP.md` — Teams Marketplace popup (per-team Install, 4-column seats, Launch, Import, Export)
9. `docs/airmaze/BRANDING.md` — Dragon AI Agent vs Hermes (window wrap + unpacked UI overlay vs Electron rebuild)
10. `docs/airmaze/DESIGN.md` — UI UX Pro Max design system applied to overlay chrome (Syne, dark + crimson)
11. `docs/airmaze/UNDERSTAND_ANYTHING.md` — MIT Understand-Anything skill (`/understand`, `/understand-dashboard`); first scan later; `.ua/` gitignored
12. `PACKAGING.md` — how this release was built

---

## License

MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md` for upstream image/legal attribution.
