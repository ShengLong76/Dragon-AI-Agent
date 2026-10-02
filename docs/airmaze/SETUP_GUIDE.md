# Dragon AI Agent — Setup Guide

**Product:** Dragon AI Agent v0.1.0  
**Audience:** First-run users (especially the **Real Estate Cold Call Lead Refresher** bot group)

This guide mirrors the **Dragon AI Agent Setup** wizard (`scripts/airmaze/Onboard-Wizard.ps1`). Prefer the wizard when possible; use this doc if you configure connectors manually.

> **Not legal advice.** Dragon AI Agent is software for drafting and workflow automation. TCPA, CAN-SPAM, Do Not Call, and consent rules vary by jurisdiction. Consult your own counsel before outbound email or calling.

---

## Secure storage

- Passwords, API keys, and auth tokens are stored with **Windows DPAPI** (`CurrentUser`) as binary files under:
  - `%LOCALAPPDATA%\DragonAIAgent\onboarding\secrets\`
- Progress and bot readiness are non-secret JSON under:
  - `%LOCALAPPDATA%\DragonAIAgent\onboarding\progress.json`
  - `%LOCALAPPDATA%\DragonAIAgent\onboarding\bots-status.json`
- Connector placeholders under `%LOCALAPPDATA%\DragonAIAgent\connectors\<bot-group>\` hold **non-secret** fields only (URLs, from-address, SID display values). **Never** put secrets in those JSON files.

---

## Real Estate flow (business order)

1. **Lead Sourcer** — refresh / enrich outbound leads  
2. **Email Warmer** — CAN-SPAM email sequences that link to a **TCPA consent** form  
3. **Consent gate** — only dial-ready leads proceed after prior express written consent is recorded in CRM  
4. **Calling** — Cold Call Script Writer + Follow-up Sequencer / dialer / telephony  

Bots stay **`needs_setup`** until required wizard steps **email + CRM + telephony** succeed. Optional: property data, dialer.

---

## Step 1 — Welcome

- Launch **Dragon AI Agent Setup** from the Start Menu (or re-run `Onboard-Wizard.ps1`).
- You can **Skip wizard**; bots remain `needs_setup` until you complete required connections later. Skipping still writes Grok / Grok Imagine defaults if the gateway config has no chat or image model yet.

---

## Step 2 — Default chat LLM and default image LLM

Pick the models Dragon AI Agent should use. Product defaults (preselected):

| Picker | Default | Written keys |
|--------|---------|----------------|
| **Default chat LLM** | Grok (xAI) `grok-4.6` | `principal.provider: xai`, `principal.model` |
| **Default image LLM** | **Grok Imagine** `grok-imagine-image` | `image_gen.provider: xai`, `image_gen.model`, `image_gen.xai.model` |

Also listed: `grok-4.5`, `grok-4.3`, Imagine quality variants `grok-imagine-image-quality` / `grok-imagine-image-2.0`, plus popular cloud chats (**OpenAI** `gpt-4o`, **Anthropic** `claude-sonnet-4-6`, **Google Gemini**, **OpenRouter**) and **Self-hosted / custom endpoint** (OpenAI-compatible base URL + model id; optional API key stored via DPAPI, never in `config.yaml`).

Choices land in `%USERPROFILE%\.hermes-airmaze-embedded\config.yaml` (the Docker volume). Cloud picks reuse keys already on the PC (`XAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`). After a change, restart the gateway if Edit profile → Generate still says no image model.

The same xAI login is what **Grok voice** uses. Voice chat keeps **GPT** (needs `OPENAI_API_KEY` for GPT-Live) and adds **Grok** beside it (`XAI_API_KEY` / xAI OAuth). In the app, pick **GPT** or **Grok** on the composer; with Grok selected, **Talk with Grok** starts official full duplex. Details: [`VOICE.md`](VOICE.md).

---

## Step 3 — Connect email

Choose **Gmail**, **Outlook / Microsoft 365**, or **generic SMTP**.

| Field | Notes |
|-------|--------|
| From address / display name | Used as the sender for warming sequences |
| Username / password | Gmail usually needs an [App Password](https://myaccount.google.com/apppasswords) |
| SMTP host / port / SSL | Gmail: `smtp.gmail.com:587` TLS; Outlook: `smtp.office365.com:587` |

**Verify** sends a short test message to your from-address. On success, the password is saved via DPAPI (`email_password`).

---

## Step 4 — Connect CRM (Vtiger)

| Field | Notes |
|-------|--------|
| Vtiger URL | Instance base URL (e.g. `https://crm.example.com`) |
| Username | CRM user |
| Access key | From Vtiger My Preferences (or password if your deploy uses it) |

The wizard tries webservice **challenge + login**, then `listtypes` for Leads/Contacts. Access key is DPAPI-stored (`crm_access_key`). Email Warmer expects TCPA consent fields and Do Not Call on Leads/Contacts — see profile connector notes.

---

## Step 5 — Connect telephony

| Field | Notes |
|-------|--------|
| Twilio Account SID / Auth Token / From phone | Account validated via Twilio REST API |
| Bland **or** Vapi API key | At least one voice provider recommended |
| Optional test call | Place a call to a number you control |

Twilio must validate for the step to succeed; voice keys are stored even if you skip the test call (you may see a warning).

---

## Step 6 — Optional integrations

- **Property data** — API base URL + key (Lead Sourcer enrichment)  
- **Dialer** — API base URL + key + optional from-number  

Each step has **Skip for now**.

---

## Step 7 — Review & finish

The summary shows **connected / skipped / failed** only — no secret values. Finish writes connector placeholders and updates bot readiness:

- Required incomplete → all Real Estate bots = `needs_setup`  
- Required complete → bots = `ready`  
- **Personal Assistant** bot group → no critical connectors; bots marked ready  

---

## After setup — open the app

Desktop / Start Menu **Dragon AI Agent** starts the gateway with no PowerShell window and opens the **desktop client** (not the web dashboard). If Docker, the gateway API, or the client is missing you get a MessageBox. Optional dashboard: Start Menu **Dragon AI Agent Dashboard**. Launch log: `%LOCALAPPDATA%\DragonAIAgent\launch.log`.

## Re-run / resume

```powershell
cd %LOCALAPPDATA%\DragonAIAgent
powershell -STA -NoProfile -ExecutionPolicy Bypass -File .\scripts\airmaze\Onboard-Wizard.ps1
```

- Resume starts at the first incomplete step.  
- `-Force` restarts from Welcome.  
- Log: `%LOCALAPPDATA%\DragonAIAgent\onboarding\wizard.log`

---

## Related docs

- `ARCHITECTURE.md` — embedded gateway on Windows via Docker  
- `EMBEDDED_GATEWAY.md` — ports and desktop wiring  
- Bot group README under `bot-groups/real-estate-cold-call-lead-refresher/`
