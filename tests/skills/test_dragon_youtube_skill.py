"""Public YouTube helper: search/transcript argv, no cookies or browser profiles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "optional-skills" / "research" / "dragon-youtube" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import youtube  # noqa: E402


def test_extract_video_id_from_common_urls():
    assert youtube.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube.extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_search_and_transcript_argv_never_request_cookies_or_login():
    search = youtube.build_search_argv("launch recap", limit=5, python="/opt/helper/python")
    transcript = youtube.build_transcript_argv(
        "https://youtu.be/dQw4w9WgXcQ", output_dir="/tmp/out", python="/opt/helper/python"
    )
    for argv in (search, transcript):
        joined = " ".join(argv)
        assert "--ignore-config" in argv
        assert "--skip-download" in argv
        for flag in youtube.FORBIDDEN_YTDLP_FLAGS:
            assert flag not in argv
            assert f"{flag}=" not in joined
        assert "cookies-from-browser" not in joined
        assert "chrome" not in joined.lower() or "chromium" not in joined.lower()

    assert "ytsearch5:launch recap" in search
    assert "-m" in search and "yt_dlp" in search


def test_assert_safe_ytdlp_argv_rejects_cookie_flags():
    with pytest.raises(ValueError, match="no login"):
        youtube.assert_safe_ytdlp_argv(["yt-dlp", "--cookies-from-browser", "chrome"])
    with pytest.raises(ValueError, match="no login"):
        youtube.assert_safe_ytdlp_argv(["yt-dlp", "--cookies", "cookies.txt"])


def test_parse_search_jsonl_and_vtt():
    raw = "\n".join(
        [
            json.dumps({"id": "aaaaaaaaaaa", "title": "One", "channel": "A", "duration": 12}),
            "not json",
            json.dumps({"id": "bbbbbbbbbbb", "title": "Two", "webpage_url": "https://youtu.be/bbbbbbbbbbb"}),
        ]
    )
    rows = youtube.parse_search_jsonl(raw)
    assert [row["id"] for row in rows] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    assert rows[0]["url"] == "https://www.youtube.com/watch?v=aaaaaaaaaaa"

    vtt = """WEBVTT

00:00:00.000 --> 00:00:01.000
Hello
00:00:01.000 --> 00:00:02.000
Hello
00:00:02.000 --> 00:00:03.000
world
"""
    assert youtube.vtt_to_text(vtt) == "Hello world"


def test_search_uses_injected_runner():
    def run(argv, _timeout):
        assert "--cookies" not in argv
        return json.dumps({"id": "ccccccccccc", "title": "Hit", "channel": "C"}) + "\n"

    rows = youtube.search_videos("topic", limit=1, python="python", run=run)
    assert rows[0]["title"] == "Hit"
