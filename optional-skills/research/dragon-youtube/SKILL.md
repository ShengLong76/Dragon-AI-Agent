---
name: dragon-youtube
description: "Fetch YouTube transcripts and search via yt-dlp."
version: 1.0.0
author: Dragon AI
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Transcripts, Search, Media, Marketing]
    category: research
    related_skills: [dragon-rss, dragon-web-reader]
---

# Dragon YouTube Skill

Search public YouTube videos and pull captions with the bundled `scripts/youtube.py`
helper. Public videos only — no login, cookies, or browser profiles. Inspired by
[Agent-Reach](https://github.com/Panniantong/Agent-Reach) (MIT). Dragon wrote this
helper; Agent-Reach is not bundled.

## When to Use

- The user shares a YouTube URL and wants a transcript, summary, or quotes.
- "Search YouTube for …" / "what are people saying in videos about …".
- Marketing research: competitor clips, launch recaps, interview soundbites.

Do not use this for private, members-only, or age-gated videos. Do not pass
cookies or a browser profile to yt-dlp.

## Prerequisites

Python 3.11+ and the pinned helper env created when this skill is added from
Skills Hub (`yt-dlp>=2025.1.26,<2027`). The installer writes `.helper-python`
next to this file. If that file is missing, add the skill again from the hub —
do not fetch an install script from the internet.

## How to Run

`SKILL_DIR` is the folder that contains this SKILL.md. Run through `terminal`
with the helper interpreter (Windows: `py` or `python`, not bash):

```
HELPER=the path in SKILL_DIR/.helper-python
"%HELPER%" SKILL_DIR/scripts/youtube.py search "brand launch recap" --limit 5 --json
"%HELPER%" SKILL_DIR/scripts/youtube.py transcript "https://www.youtube.com/watch?v=VIDEO_ID" --json
```

On POSIX the same commands work with `"$HELPER"` instead of `"%HELPER%"`.

## Quick Reference

| Task | Command |
|---|---|
| Search | `youtube.py search QUERY --limit 8 --json` |
| Transcript | `youtube.py transcript URL --language en --json` |
| Video id | `watch?v=`, `youtu.be/`, `shorts/`, or a raw 11-char id |

Search rows: `id`, `title`, `url`, `channel`, `duration`. Transcript: `video_id`,
`language`, `transcript`.

## Procedure

① If the user gave a topic, not a URL, run `search` and pick the matching public
video. Cite the watch URL.

② Run `transcript` for that URL. If captions are missing, say so — do not try
`--cookies`, `--cookies-from-browser`, or a login.

③ Summarize, quote, or chapterize from the transcript text. Use `read_file` on
the helper JSON if you redirected it to a file.

## Pitfalls

- Age-gated or private videos have no public captions. Report that and stop.
- yt-dlp user config can inject cookies; the helper always passes `--ignore-config`.
- Do not download the video file. The helper is `--skip-download` only.

## Verification

`youtube.py search "test" --limit 1 --json` prints a JSON list (needs network).
`youtube.py transcript` on a known public video returns non-empty `transcript`.
The helper argv never includes cookie or login flags.
