---
name: dragon-web-reader
description: "Read a web page as clean text via Jina."
version: 1.0.0
author: Dragon AI
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Web, Reader, Jina, Research]
    category: research
    related_skills: [dragon-youtube, dragon-rss]
---

# Dragon Web Reader Skill

Turn a public page URL into readable text. The bundled `scripts/read_page.py`
helper tries Jina Reader (`r.jina.ai`) first, then a plain HTTP GET and HTML
strip. No login, cookies, or browser profiles. Inspired by
[Agent-Reach](https://github.com/Panniantong/Agent-Reach) (MIT). Dragon wrote
this helper; Agent-Reach is not bundled.

## When to Use

- "Read this article / docs page / blog post and summarize it."
- Cleaning a URL before quoting. Prefer this over pasting raw HTML.
- Follow-up after `dragon-rss` when an entry's `link` needs the full body.

Do not use this for pages behind a login. Do not read the user's browser
profile to obtain cookies.

## Prerequisites

Python 3.11+ (stdlib only: `urllib`, `html.parser`). Skills Hub still copies
the helper and writes `.helper-python` so the same run pattern works on
Windows. If that file is missing, add the skill again from the hub — do not
fetch an install script from the internet.

## How to Run

`SKILL_DIR` is the folder that contains this SKILL.md. Run through `terminal`
with the helper interpreter (Windows: `py` or `python`, not bash):

```
HELPER=the path in SKILL_DIR/.helper-python
"%HELPER%" SKILL_DIR/scripts/read_page.py "https://example.com/post" --json
```

On POSIX the same command works with `"$HELPER"` instead of `"%HELPER%"`.

## Quick Reference

| Field | Meaning |
|---|---|
| `url` | The page the user asked for |
| `source` | `jina` if Reader succeeded, else `plain` |
| `text` | Visible text, scripts and styles removed |

Jina URL shape (built by the helper): `https://r.jina.ai/` + the original URL.

## Procedure

① Confirm the URL is `http` or `https`. Reject `file:` and local paths.

② Run `read_page.py --json`. If `source` is `jina`, trust that text first. If
`source` is `plain`, expect leftover nav chrome — quote carefully.

③ Summarize with citations to the original URL, not the `r.jina.ai` prefix.
Use `read_file` if you saved the JSON.

## Pitfalls

- Sites that block datacenter IPs may fail both Jina and the plain fetch. Say
  so; do not open a logged-in browser profile.
- The helper never sends a `Cookie` header. Do not add one.
- Very large pages: take the helper output as-is. Do not paginate the skill
  file itself.

## Verification

`read_page.py https://example.com --json` returns `text` and `source` of `jina`
or `plain`. A non-http URL exits with an error.
