"""RSS helper: feedparser-shaped input, digest, public http(s) only."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "optional-skills" / "research" / "dragon-rss" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rss  # noqa: E402


class _Obj(types.SimpleNamespace):
    pass


def _parsed():
    return _Obj(
        feed=_Obj(title="Blog & Notes"),
        entries=[
            _Obj(
                title="Older",
                link="https://ex.com/a",
                published="Mon, 01 Sep 2026 10:00:00 GMT",
                author="Ann",
                summary="<p>Hello <b>world</b></p>",
            ),
            _Obj(
                title="Newer",
                link="https://ex.com/b",
                published="2026-09-04T06:30:00+00:00",
                author="",
                summary="Just text",
            ),
        ],
    )


def test_normalize_feed_strips_html_and_bounds_limit():
    feed = rss.normalize_feed(_parsed(), limit=1)
    assert feed["title"] == "Blog & Notes"
    assert len(feed["entries"]) == 1
    assert feed["entries"][0]["summary"] == "Hello world"
    assert feed["entries"][0]["link"] == "https://ex.com/a"


def test_read_feed_uses_injected_parser_and_rejects_non_http():
    feed = rss.read_feed("https://ex.com/feed.xml", limit=10, parse=lambda url: _parsed())
    assert [e["title"] for e in feed["entries"]] == ["Older", "Newer"]
    digest = rss.digest_text(feed)
    assert "Blog & Notes" in digest
    assert "https://ex.com/b" in digest
    with pytest.raises(ValueError, match="http"):
        rss.read_feed("file:///etc/passwd")
    with pytest.raises(ValueError, match="empty"):
        rss.read_feed("  ")


def test_user_agent_is_dragon_not_a_browser_profile():
    assert rss.USER_AGENT.startswith("Dragon-AI-RSS/")
    assert "cookie" not in rss.USER_AGENT.lower()
    assert "chrome" not in rss.USER_AGENT.lower()
