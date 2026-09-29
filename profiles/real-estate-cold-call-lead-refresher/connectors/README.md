# Connectors (placeholders)

These JSON templates describe integrations for the Real Estate Cold Call Lead Refresher profile.
They are **not** live credentials. After install they are copied to:

`%LOCALAPPDATA%\DragonAIAgent\connectors\real-estate-cold-call-lead-refresher\`

| File | Purpose |
|------|---------|
| `crm.json` | Vtiger / CRM — leads, TCPA consent fields, Do Not Call |
| `email.json` | Email Warmer — SMTP/ESP or Dragon AI Agent email skill |
| `consent-form.json` | Hosted TCPA consent form endpoint |
| `dialer.json` | Outbound dialer after consent gate |
| `property-data.json` | Lead enrichment |
| `mcp-local-files.json` | Optional local CSV MCP |

Edit secrets locally. Wire MCP entries into your agent desktop client MCP settings when ready.
