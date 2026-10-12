#!/usr/bin/env python3
"""Public YouTube search and transcripts via yt-dlp. No login.

Works on Windows and POSIX. Never reads cookies, netrc, or browser profiles.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence

# Flags that would log in, send cookies, or read a browser profile.
FORBIDDEN_YTDLP_FLAGS = (
    "--cookies",
    "--cookies-from-browser",
    "--username",
    "--password",
    "--netrc",
    "--netrc-location",
    "--netrc-cmd",
    "--ap-mso",
    "--ap-username",
    "--ap-password",
)

VIDEO_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})|^([A-Za-z0-9_-]{11})$"
)
VTT_TS_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}"
)
_WS_RE = re.compile(r"\s+")

Runner = Callable[[Sequence[str], float], str]


def extract_video_id(url_or_id: str) -> str:
    """Return the 11-character video id, or the stripped input if unknown."""
    text = (url_or_id or "").strip()
    match = VIDEO_ID_RE.search(text)
    if not match:
        return text
    return match.group(1) or match.group(2)


def assert_safe_ytdlp_argv(argv: Sequence[str]) -> tuple[str, ...]:
    """Reject cookie, login, and browser-profile flags. Always ignore user config."""
    if not argv:
        raise ValueError("yt-dlp argv is empty")
    lowered = [part.lower() for part in argv]
    for flag in FORBIDDEN_YTDLP_FLAGS:
        if flag in lowered or any(part.startswith(f"{flag}=") for part in lowered):
            raise ValueError(f"refusing yt-dlp flag {flag}: public videos only, no login")
    out = list(argv)
    if "--ignore-config" not in out:
        out.append("--ignore-config")
    return tuple(out)


def build_search_argv(query: str, *, limit: int = 8, python: str | None = None) -> tuple[str, ...]:
    """yt-dlp search without download. Public index only."""
    q = (query or "").strip()
    if not q:
        raise ValueError("search query is empty")
    n = max(1, min(int(limit), 25))
    exe = [python, "-m", "yt_dlp"] if python else ["yt-dlp"]
    return assert_safe_ytdlp_argv(
        [
            *exe,
            "--ignore-config",
            "--skip-download",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            f"ytsearch{n}:{q}",
        ]
    )


def build_transcript_argv(
    url_or_id: str,
    *,
    languages: str = "en",
    output_dir: str,
    python: str | None = None,
) -> tuple[str, ...]:
    """Write public / auto captions next to output_dir. Never downloads the video."""
    target = (url_or_id or "").strip()
    if not target:
        raise ValueError("video url is empty")
    dest = Path(output_dir)
    exe = [python, "-m", "yt_dlp"] if python else ["yt-dlp"]
    return assert_safe_ytdlp_argv(
        [
            *exe,
            "--ignore-config",
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-langs",
            languages or "en",
            "--convert-subs",
            "vtt",
            "--output",
            str(dest / "%(id)s.%(ext)s"),
            "--no-warnings",
            target,
        ]
    )


def parse_search_jsonl(text: str) -> list[dict]:
    """Parse yt-dlp --dump-json playlist lines into a stable search shape."""
    rows: list[dict] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        video_id = raw.get("id") or ""
        url = raw.get("webpage_url") or raw.get("url") or ""
        if video_id and not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={video_id}"
        rows.append(
            {
                "id": video_id,
                "title": raw.get("title") or "",
                "url": url,
                "channel": raw.get("channel") or raw.get("uploader") or "",
                "duration": raw.get("duration"),
            }
        )
    return rows


def vtt_to_text(vtt: str) -> str:
    """Strip WebVTT chrome to plain transcript lines."""
    lines: list[str] = []
    seen: set[str] = set()
    for raw in (vtt or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or VTT_TS_RE.match(line):
            continue
        if line.isdigit():
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return _WS_RE.sub(" ", " ".join(lines)).strip()


def _run_text(argv: Sequence[str], timeout: float) -> str:
    completed = subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "yt-dlp failed").strip()
        raise RuntimeError(err)
    return (completed.stdout or "") + (completed.stderr or "")


def search_videos(
    query: str,
    *,
    limit: int = 8,
    python: str | None = None,
    run: Runner = _run_text,
) -> list[dict]:
    argv = build_search_argv(query, limit=limit, python=python)
    return parse_search_jsonl(run(argv, 90))


def fetch_transcript(
    url_or_id: str,
    *,
    languages: str = "en",
    python: str | None = None,
    run: Runner = _run_text,
    work_dir: Path | None = None,
) -> dict:
    import tempfile

    video_id = extract_video_id(url_or_id)
    dest = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="dragon-yt-"))
    dest.mkdir(parents=True, exist_ok=True)
    argv = build_transcript_argv(url_or_id, languages=languages, output_dir=str(dest), python=python)
    run(argv, 120)
    vtt_files = sorted(dest.glob("*.vtt"))
    if not vtt_files:
        raise RuntimeError("no public captions found for this video")
    text = vtt_to_text(vtt_files[0].read_text(encoding="utf-8-sig", errors="replace"))
    return {
        "video_id": video_id,
        "language": languages,
        "transcript": text,
        "caption_file": str(vtt_files[0]),
    }


def _emit(data: object, as_json: bool) -> None:
    if as_json:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return
    if isinstance(data, list):
        for row in data:
            print(f"{row.get('title', '')}\n  {row.get('url', '')}\n  {row.get('channel', '')}")
        return
    if isinstance(data, dict) and "transcript" in data:
        print(data["transcript"])
        return
    print(data)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Public YouTube search and transcripts (no login).")
    parser.add_argument("--python", default=sys.executable, help="Interpreter that has yt-dlp")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=8)
    transcript = sub.add_parser("transcript")
    transcript.add_argument("url")
    transcript.add_argument("--language", default="en")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.cmd == "search":
            _emit(search_videos(args.query, limit=args.limit, python=args.python), args.json)
        else:
            _emit(fetch_transcript(args.url, languages=args.language, python=args.python), args.json)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
