"""Web reader: Jina URL, HTML strip, plain-fetch fallback, no cookies."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "optional-skills" / "research" / "dragon-web-reader" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import read_page  # noqa: E402


def test_jina_reader_url_prefixes_http_pages():
    assert read_page.jina_reader_url("https://example.com/post") == "https://r.jina.ai/https://example.com/post"
    already = "https://r.jina.ai/https://example.com/post"
    assert read_page.jina_reader_url(already) == already
    with pytest.raises(ValueError):
        read_page.jina_reader_url("file:///tmp/x")
    with pytest.raises(ValueError):
        read_page.jina_reader_url("/etc/passwd")


def test_strip_html_drops_script_and_keeps_visible_text():
    html = "<html><head><script>alert(1)</script><style>p{}</style></head><body><h1>Hi</h1><p>there</p></body></html>"
    assert read_page.strip_html(html) == "Hi there"


def test_read_page_prefers_jina_then_falls_back_to_plain():
    calls: list[str] = []

    def fetch_jina(url: str):
        calls.append(url)
        return "Clean article", 200

    result = read_page.read_page("https://example.com/post", fetch=fetch_jina)
    assert result["source"] == "jina"
    assert result["text"] == "Clean article"
    assert calls == ["https://r.jina.ai/https://example.com/post"]

    def fetch_fallback(url: str):
        if url.startswith(read_page.JINA_PREFIX):
            raise TimeoutError("jina down")
        return "<html><body><p>Plain body</p></body></html>", 200

    fallback = read_page.read_page("https://example.com/post", fetch=fetch_fallback)
    assert fallback["source"] == "plain"
    assert fallback["text"] == "Plain body"


def test_default_headers_never_send_cookies():
    headers = read_page._headers()
    assert "Cookie" not in headers
    assert "Authorization" not in headers
    assert headers["User-Agent"].startswith("Dragon-AI-Web-Reader/")
