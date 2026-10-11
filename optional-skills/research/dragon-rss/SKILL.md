---
name: dragon-rss
description: "Read and summarize public RSS and Atom feeds."
version: 1.0.0
author: Dragon AI
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [RSS, Atom, Feeds, Research, Marketing]
    category: research
    related_skills: [dragon-youtube, dragon-web-reader]
---

# Dragon RSS Skill

Read a public RSS or Atom URL with the bundled `scripts/rss.py` helper
(feedparser) and turn the entries into a short digest. No login, cookies, or
browser profiles. Inspired by [Agent-Reach](https://github.com/Panniantong/Agent-Reach)
(MIT). Dragon wrote this helper; Agent-Reach is not bundled.

## When to Use

- "What's new on this blog / changelog / podcast / newsroom."
- Marketing: competitor posts, industry wires, launch notes.
- A recurring digest: persist the newest `published` value and pass a tighter
  `--limit` next time.

This skill lists entries. For full article bodies, hand a link to
`dragon-web-reader` or `web_extract`.

## Prerequisites

Python 3.11+ and the pinned helper env created when this skill is added from
Skills Hub (`feedparser>=6.0.11,<7`). The installer writes `.helper-python`
next to this file. If that file is missing, add the skill again from the hub —
do not fetch an install script from the internet.

## How to Run

`SKILL_DIR` is the folder that contains this SKILL.md. Run through `terminal`
with the helper interpreter (Windows: `py` or `python`, not bash):

```
HELPER=the path in SKILL_DIR/.helper-python
"%HELPER%" SKILL_DIR/scripts/rss.py read https://example.com/feed.xml --limit 10 --json
"%HELPER%" SKILL_DIR/scripts/rss.py digest https://hnrss.org/frontpage --limit 8
```

On POSIX the same commands work with `"$HELPER"` instead of `"%HELPER%"`.

## Quick Reference

| Task | Command |
|---|---|
| JSON entries | `rss.py read FEED_URL --limit 20 --json` |
| Text digest | `rss.py digest FEED_URL --limit 12` |
| GitHub releases | `https://github.com/OWNER/REPO/releases.atom` |
| YouTube channel | `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` |

Each entry: `title`, `link`, `published`, `author`, `summary` (HTML stripped).

## Procedure

① If the user gave a site URL, not a feed, try common paths (`/feed`, `/rss.xml`,
`/atom.xml`) or a `<link rel="alternate">` you already have. Do not scrape a
logged-in dashboard.

② Run `read --json` or `digest`. Bound `--limit`. Newest entries first as the
parser returns them.

③ Write a short summary for the user: headline, why it matters, and the entry
`link`. Use `read_file` if you saved the JSON.

## Pitfalls

- A 200 HTML page is not a feed; try another path rather than inventing entries.
- Feed summaries are often a teaser. Fetch the article only when the user needs
  the body.
- Do not send cookies or read a browser profile to bypass a paywall.

## Verification

`rss.py read` on a public feed returns `entries` with `title` and `link`.
`rss.py digest` prints a markdown-ish list the user can scan.
