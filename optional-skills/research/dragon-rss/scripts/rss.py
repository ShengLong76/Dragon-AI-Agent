#!/usr/bin/env python3
"""Read public RSS / Atom feeds with feedparser. No login.

Works on Windows and POSIX. Never sends cookies or reads a browser profile.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Callable, Iterable

USER_AGENT = "Dragon-AI-RSS/1.0 (+https://github.com/ShengLong76/Dragon-AI-Agent)"
_WS_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")

ParseFn = Callable[[str], Any]


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


def _entry_link(entry: Any) -> str:
    link = getattr(entry, "link", "") or ""
    if link:
        return str(link)
    links = getattr(entry, "links", None) or []
    for item in links:
        href = item.get("href") if isinstance(item, dict) else getattr(item, "href", "")
        if href:
            return str(href)
    return ""


def normalize_feed(parsed: Any, *, limit: int = 20) -> dict:
    """Map a feedparser result onto a stable JSON shape."""
    feed = getattr(parsed, "feed", parsed) or {}
    title = getattr(feed, "title", None) or (feed.get("title") if isinstance(feed, dict) else "") or ""
    entries_out: list[dict] = []
    for raw in list(getattr(parsed, "entries", []) or [])[: max(1, int(limit))]:
        summary = getattr(raw, "summary", None) or getattr(raw, "description", None) or ""
        entries_out.append(
            {
                "title": str(getattr(raw, "title", "") or ""),
                "link": _entry_link(raw),
                "published": str(getattr(raw, "published", None) or getattr(raw, "updated", None) or ""),
                "author": str(getattr(raw, "author", "") or ""),
                "summary": strip_html(str(summary)),
            }
        )
    return {"title": str(title), "entries": entries_out}


def digest_text(feed: dict) -> str:
    """Compact listing the agent can summarize for the user."""
    lines = [f"# {feed.get('title') or 'Feed'}", ""]
    for entry in feed.get("entries") or []:
        lines.append(f"- {entry.get('title') or '(untitled)'}")
        if entry.get("published"):
            lines.append(f"  {entry['published']}")
        if entry.get("link"):
            lines.append(f"  {entry['link']}")
        if entry.get("summary"):
            snippet = entry["summary"][:280]
            lines.append(f"  {snippet}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _default_parse(url: str) -> Any:
    try:
        import feedparser
    except ImportError as exc:
        raise RuntimeError(
            "feedparser is not installed. Re-run Add on this skill so the pinned helper env is created."
        ) from exc
    parsed = feedparser.parse(url, agent=USER_AGENT)
    bozo = getattr(parsed, "bozo", 0)
    if bozo and not getattr(parsed, "entries", None):
        err = getattr(parsed, "bozo_exception", None)
        raise RuntimeError(f"could not parse feed: {err or url}")
    return parsed


def read_feed(url: str, *, limit: int = 20, parse: ParseFn = _default_parse) -> dict:
    target = (url or "").strip()
    if not target:
        raise ValueError("feed url is empty")
    if not target.startswith(("http://", "https://")):
        raise ValueError("feed url must be http(s)")
    return normalize_feed(parse(target), limit=limit)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read public RSS/Atom feeds (no login).")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    read = sub.add_parser("read")
    read.add_argument("url")
    read.add_argument("--limit", type=int, default=20)
    digest = sub.add_parser("digest")
    digest.add_argument("url")
    digest.add_argument("--limit", type=int, default=12)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        feed = read_feed(args.url, limit=args.limit)
        if args.cmd == "digest" and not args.json:
            sys.stdout.write(digest_text(feed))
        else:
            json.dump(feed, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
