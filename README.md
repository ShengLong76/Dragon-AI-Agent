# Dragon AI Agent

**Version:** 0.1.0  
**Product:** Dragon AI Agent — Windows packaging that provisions an embedded Linux gateway (Bot Screen capable) via Docker Desktop, plus a **profile catalog** (import or select) with multi-bot business packs.

Compatible with the open-source agent desktop stack (separate desktop client). This tree ships compose, Windows bootstrap, docs, profile bundles, and connector placeholders — not a full upstream agent source fork.

---

## What v0.1.0 does

| Step | Behavior |
|------|----------|
| WSL2 | Best-effort check / enable (`wsl --install` if missing). **Reboot may be required.** |
| Docker Desktop | Detect; quiet install when possible; else open download page. Configured to **start minimized to the system tray** (no dashboard window on launch). |
| Embedded gateway | `docker compose` pull + `up -d` for the packaged embedded gateway image (see `THIRD_PARTY_NOTICES.md`). |
| Ports | `127.0.0.1:8650` (Desktop Remote / Bot Screen), `127.0.0.1:8642` (OpenAI API), `127.0.0.1:9119` (browser dashboard). Local credentials: see `docs/airmaze/EMBEDDED_GATEWAY.md`. |
| **Profiles** | First-run menu: **select** a built-in catalog profile **or import** a zip/folder/JSON bundle. Applies bots into the local agent profiles dir and installs connector placeholders. |
| **Onboarding** | First-run **Dragon AI Agent Setup** wizard (email / CRM / telephony + optional integrations). Secrets via Windows DPAPI. Markdown guide: `docs/airmaze/SETUP_GUIDE.md`. Real Estate bots stay `needs_setup` until required steps succeed. |
| Agent desktop | Discovers on-disk `Hermes.exe` (including `%LOCALAPPDATA%\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`) and shows it as **Dragon AI Agent**. Opening the shortcut starts the gateway then this window (or a blocking error if Docker/client is missing). Dashboard login: `dragon` / `dragon-local`. |

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

Desktop / Start Menu shortcuts: **Dragon AI Agent**, **Dragon AI Agent Profiles**, and **Dragon AI Agent Setup** (onboarding wizard).

Opening **Dragon AI Agent** uses a windowless host (`Start-DragonAI.vbs` / `wscript.exe`) — no PowerShell console. It starts the gateway **and** the Desktop-compatible Linux `hermes serve` (published at `http://127.0.0.1:8650`), writes the Remote connection, and opens the **desktop client** (not the :9119 dashboard). Docker must already be running (fail-closed; `-StartDocker` to opt in). Failures are a MessageBox. **This device** Screen is Linux-only by upstream design — use the Embedded Linux Remote. Dashboard: Start Menu **Dragon AI Agent Dashboard**. Debug: run `start-embedded.ps1` in a console. Launch log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`. Branding: [`docs/airmaze/BRANDING.md`](docs/airmaze/BRANDING.md).

```powershell
# Same path the shortcut uses (no secrets)
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\DragonAIAgent\scripts\airmaze\start-embedded.ps1"

# Offline contract check (repo checkout; Linux-safe)
python3 scripts/airmaze/Test-LaunchSmoke.py
```

---

## Profiles (select or import)

A **profile** is a packaged bundle with:

- a group of **bots** (each: name, description, `SOUL.md` / instructions, `bot.yaml`)
- a set of **connectors** (integration placeholders: API key templates, MCP server stubs) for a business type

### Built-in catalog (`profiles/catalog.json`)

| Id | Display name | Bots |
|----|--------------|------|
| `personal-assistant` | Personal Assistant | 1 — general PA |
| `real-estate-cold-call-lead-refresher` | Real Estate Cold Call Lead Refresher | 4 — Lead Sourcer, Email Warmer, Cold Call Script Writer, Follow-up Sequencer |

### First-run / Profiles menu

```text
[1] Personal Assistant
[2] Real Estate Cold Call Lead Refresher
[3] Import from file (zip or profile folder/JSON)
[Enter] default = Personal Assistant
```

Scripts:

```powershell
# Catalog select
.\scripts\airmaze\Select-Profile.ps1 -ProfileId real-estate-cold-call-lead-refresher

# Import
.\scripts\airmaze\Import-Profile.ps1 -SourcePath C:\path\to\my-profile.zip

# Apply a folder that already has profile.json
.\scripts\airmaze\Apply-Profile.ps1 -ProfilePath C:\path\to\profile-folder
```

### Profile bundle format

```text
my-profile/
  profile.json          # manifest
  bots/
    <bot-id>/
      SOUL.md
      bot.yaml
  connectors/
    *.json              # optional placeholders
```

Minimal `profile.json`:

```json
{
  "id": "my-profile",
  "displayName": "My Profile",
  "description": "What this pack does",
  "version": "1.0.0",
  "bots": [
    {
      "id": "my-bot",
      "displayName": "My Bot",
      "description": "Short description",
      "soul": "bots/my-bot/SOUL.md",
      "config": "bots/my-bot/bot.yaml"
    }
  ],
  "connectors": [
    {
      "id": "crm",
      "type": "api_key",
      "displayName": "CRM",
      "description": "Optional",
      "configTemplate": "connectors/crm.json"
    }
  ]
}
```

**On apply:** each bot is copied to `%LOCALAPPDATA%\hermes\profiles\<bot-id>\` (path used by the agent desktop profile / Bot Screen picker). Connector JSON lands under `%LOCALAPPDATA%\DragonAIAgent\connectors\<profile-id>\`. Active selection is recorded in `%LOCALAPPDATA%\DragonAIAgent\active-profile.json`.

Zip the profile folder and import with `Import-Profile.ps1`, or place it under `profiles/` and add an entry to `catalog.json`.

---

## Onboarding wizard + setup guide

After profile selection, the installer launches **Dragon AI Agent Setup** (`Onboard-Wizard.ps1`):

1. Welcome  
2. Connect email (Gmail / Outlook / SMTP + verify)  
3. Connect CRM (Vtiger webservice)  
4. Connect telephony (Twilio + Bland/Vapi)  
5. Optional: property data, dialer  
6. Review & finish  

Secrets are stored with **Windows DPAPI** under `%LOCALAPPDATA%\DragonAIAgent\onboarding\secrets\` — never in plaintext JSON. Real Estate bots remain **`needs_setup`** until email + CRM + telephony succeed.

Re-run anytime from Start Menu **Dragon AI Agent Setup**, or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\DragonAIAgent\scripts\airmaze\Onboard-Wizard.ps1"
```

Human-readable steps: [`docs/airmaze/SETUP_GUIDE.md`](docs/airmaze/SETUP_GUIDE.md).

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

Also see `profiles/personal-assistant/` and legacy `templates/profiles/personal-assistant/`.

---

## Repo layout

```
README.md
LICENSE
THIRD_PARTY_NOTICES.md
CHANGELOG.md
PACKAGING.md
docs/airmaze/
docker-compose.embedded.yml
profiles/
  catalog.json
  personal-assistant/
  real-estate-cold-call-lead-refresher/
scripts/airmaze/
  install.ps1
  start-embedded.ps1
  Start-DragonAI.vbs
  Find-HermesDesktop.ps1
  Test-LaunchSmoke.py
  Test-DesktopServeAdapter.py
  desktop-loopback-proxy.py
  start-desktop-serve.sh
  start-desktop-proxy.sh
  embedded_desktop_connection.py
  Set-EmbeddedDesktopConnection.ps1
  apply-default-profile.ps1
  Apply-Profile.ps1
  Select-Profile.ps1
  Import-Profile.ps1
  Onboard-Wizard.ps1
  DragonAI-SecureStore.ps1
templates/profiles/personal-assistant/
installer/
  DragonAIAgentSetup.ps1
  build-exe.go
branding/   (release: dragon-ai-agent-logo.png / .ico)
```

---

## Docs

1. Bot Screen feature docs — see links in `docs/airmaze/UPSTREAM_NOTES.md` and `THIRD_PARTY_NOTICES.md`
2. `docs/airmaze/ARCHITECTURE.md` — embed Bot Screen on Windows via Docker
3. `docs/airmaze/EMBEDDED_GATEWAY.md` — ports (`:8650` Desktop serve), compose, UltraDragon re-smoke
4. `docs/airmaze/UPSTREAM_NOTES.md` — Linux-gateway-only + Desktop token/WS vs `gateway run`
5. `docs/airmaze/SETUP_GUIDE.md` — first-run onboarding (email / CRM / telephony) + Real Estate flow
6. `docs/airmaze/BRANDING.md` — Dragon AI Agent vs Hermes (packaging wrap vs Electron rebuild)
7. `PACKAGING.md` — how this release was built

---

## License

MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md` for upstream image/legal attribution.
