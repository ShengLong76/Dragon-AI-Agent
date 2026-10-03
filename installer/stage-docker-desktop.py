#!/usr/bin/env python3
"""Stage the official Docker Desktop installer into vendor/docker/.

Used when building the Windows zip so a clean PC can quiet-install Docker
from the package. The exe is gitignored (~500MB). Setup still downloads
this same URL when the slot is empty.

No secrets. Safe to skip in CI. Does not run the installer.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST_DIR = ROOT / "vendor" / "docker"
DEST = DEST_DIR / "Docker Desktop Installer.exe"
URL = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing Docker Desktop Installer.exe",
    )
    parser.add_argument(
        "--url",
        default=URL,
        help="official Docker Desktop installer URL",
    )
    args = parser.parse_args()

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    if DEST.is_file() and not args.force:
        print(f"OK  already staged: {DEST} ({DEST.stat().st_size} bytes)")
        print("    pass --force to download again")
        return 0

    print(f"GET {args.url}")
    print(f" -> {DEST}")
    try:
        with urllib.request.urlopen(args.url) as resp, DEST.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as exc:  # noqa: BLE001 — stage script prints and exits
        if DEST.exists() and DEST.stat().st_size == 0:
            DEST.unlink()
        fail(f"download failed: {exc}")

    size = DEST.stat().st_size
    if size < 1_000_000:
        DEST.unlink(missing_ok=True)
        fail(f"downloaded file is too small to be the Docker installer ({size} bytes)")
    print(f"OK  staged {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
