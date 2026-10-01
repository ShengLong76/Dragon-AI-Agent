# seo-audit

Adapted from claude-seo `skills/seo-audit`. Full-site review only. One URL → `seo-page`. Technical-only → `seo-technical`.

## Do

1. Confirm the operator named a site. Use browser / computer-use to fetch public pages the operator allows.
2. Pull live SERP, keyword, on-page, and backlink numbers through **DataForSEO** when the MCP is connected (`seo-dataforseo`). Otherwise mark figures as operator-supplied or unknown.
3. Score and prioritize: crawl/index blockers, titles/meta, thin or duplicate content, schema gaps, Core Web Vitals (LCP, INP, CLS — not FID), citability notes.
4. Every recommendation: observation, dependency, “how would we know this failed?”, leading indicator.
5. Do not invent traffic or rankings. Do not publish or edit production without the operator.

## Out

Parallel Claude Code sub-agents, Playwright `install.sh`, Firecrawl site dumps.
