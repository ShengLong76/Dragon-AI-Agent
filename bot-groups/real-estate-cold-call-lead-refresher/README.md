# Real Estate Cold Call Lead Refresher

Four-bot outbound **bot group** for Dragon AI Agent. Department-level job: refresh stale leads, warm them, write scripts, follow up.

## Flow

1. **Lead Sourcer** — refresh / enrich / prioritize leads from CRM, lists, and property data.
2. **Email Warmer** — for leads past the ~18-month EBR window (or lacking phone consent), send a short CAN-SPAM commercial email sequence that links to a hosted TCPA consent form.
3. **Consent gate** — on form submit, write Vtiger fields (`TCPA Consent`, date, method=`email form`, source URL, consented phone) plus disclosure evidence; suppress unsubscribe / STOP / bounces across email and calling.
4. **Calling path** — **Cold Call Script Writer** + **dialer** / **Follow-up Sequencer** only for dial-ready leads (consent fields pass **and** Do Not Call is false).

```text
Lead Sourcer → Email Warmer → consent gate → calling bot (script + dialer)
```

## Bots

| Id | Role |
|----|------|
| `lead-sourcer` | Lists, enrichment, prioritization |
| `email-warmer` | CAN-SPAM warming → consent form |
| `cold-call-script-writer` | Talk tracks for dial-ready leads |
| `follow-up-sequencer` | Post-outreach multi-touch plans |

## Connectors (placeholders)

| Id | Used by |
|----|---------|
| `crm` | All bots — Vtiger TCPA + DNC fields |
| `email` | Email Warmer — send commercial mail |
| `consent-form` | Email Warmer — form URL + disclosure version |
| `dialer` | Calling path after consent gate |
| `property-data` | Lead Sourcer enrichment |
| `mcp-local-files` | Optional CSV imports |

No live API keys ship in this package. This documentation is operational guidance, not legal advice.
