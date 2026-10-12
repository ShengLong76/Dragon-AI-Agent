#!/usr/bin/env python3
"""Read a public web page as clean text. Jina Reader first, then plain fetch.

Works on Windows and POSIX. Never sends cookies or reads a browser profile.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Callable, Iterable
from urllib.parse import urlparse

JINA_PREFIX = "https://r.jina.ai/"
USER_AGENT = "Dragon-AI-Web-Reader/1.0 (+https://github.com/ShengLong76/Dragon-AI-Agent)"
TIMEOUT = 25
_WS_RE = re.compile(r"\s+")

Fetcher = Callable[[str], tuple[str, int]]


class _TextExtractor(HTMLParser):
    """Collect visible text; skip script/style/noscript."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return _WS_RE.sub(" ", " ".join(self._chunks)).strip()


def jina_reader_url(url: str) -> str:
    """r.jina.ai proxy for a fully-qualified page URL."""
    target = (url or "").strip()
    if not target:
        raise ValueError("page url is empty")
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("page url must be http(s) with a host")
    if target.startswith(JINA_PREFIX):
        return target
    return f"{JINA_PREFIX}{target}"


def strip_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html or "")
    parser.close()
    return parser.text()


def _headers() -> dict[str, str]:
    # Accept only. Never Cookie, Authorization, or a browser profile.
    return {"User-Agent": USER_AGENT, "Accept": "text/plain, text/html, */*"}


def _default_fetch(url: str) -> tuple[str, int]:
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace"), int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        return raw.decode("utf-8", errors="replace"), int(exc.code)


def read_page(url: str, *, fetch: Fetcher = _default_fetch) -> dict:
    """Jina Reader first; plain GET + HTML strip if that fails."""
    target = (url or "").strip()
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("page url must be http(s) with a host")

    jina = jina_reader_url(target)
    try:
        body, status = fetch(jina)
        if status == 200 and body.strip():
            return {"url": target, "source": "jina", "text": body.strip()}
    except (OSError, TimeoutError, urllib.error.URLError):
        body, status = "", 0

    html, status = fetch(target)
    if status != 200 or not html.strip():
        raise RuntimeError(f"could not read page (status {status})")
    text = strip_html(html)
    if not text:
        raise RuntimeError("page had no readable text")
    return {"url": target, "source": "plain", "text": text}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a public page as clean text (no login).")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = read_page(args.url)
        if args.json:
            json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(result["text"] + "\n")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
