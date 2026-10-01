# Marketing Team connectors (placeholders)

Non-secret templates copied to `%LOCALAPPDATA%\DragonAIAgent\connectors\marketing-team\`.

| File | Seat | Purpose |
|------|------|---------|
| `seoagent.json` | SEO Specialist | seoagent.com CLI (`@seoagent-official/seoagent`) — `seoagent init`. Free Skill; Autopilot is paid/optional |
| `dataforseo.json` | SEO Specialist | DataForSEO MCP (`npx -y dataforseo-mcp-server`) — kept, separate from SEOagent |

Locked defaults **Buffer** (Social Media Manager) and **Brevo** (Lifecycle Marketer) are not wired in this folder. Edit secrets locally. Wire the MCP entry in the agent desktop client — this JSON is not auto-injected into Hermes `config.yaml`.
