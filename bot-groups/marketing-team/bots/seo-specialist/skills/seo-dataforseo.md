# seo-dataforseo

Adapted from claude-seo `skills/seo-dataforseo` and the DataForSEO extension. Live data via the official MCP: `npx -y dataforseo-mcp-server`.

## Credentials

Operator-local only (`DATAFORSEO_USERNAME`, `DATAFORSEO_PASSWORD`). See `docs/airmaze/SEOAGENT.md`. If the MCP is missing, say so and use operator-supplied numbers — do not guess.

Enabled modules (same set as claude-seo’s DataForSEO extension): SERP, KEYWORDS_DATA, ONPAGE, DATAFORSEO_LABS, BACKLINKS, DOMAIN_ANALYTICS, BUSINESS_DATA, CONTENT_ANALYSIS, AI_OPTIMIZATION.

## Prefer these jobs

| Job | Use |
|-----|-----|
| SERP | Organic results for a query |
| Keywords | Ideas, suggestions, related |
| Volume / difficulty / intent / trends | Keyword metrics |
| Backlinks | Referring domains, spam notes |
| Competitors / ranked / intersection | Domain overlap |
| On-page / tech / whois | Page and stack |
| AI mentions | Only if the operator wants GEO visibility |

Credits cost real money. Ask before bulk crawls. Do not switch the default to SearchApi.
