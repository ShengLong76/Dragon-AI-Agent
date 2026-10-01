#!/usr/bin/env python3
"""Generate low-poly Teams seat icons (Dragon navy + crimson).

Writes transparent SVGs next to this file. Re-run after adding a seat id.
Not a runtime LLM call — Cos ships the files with the overlay pack.
"""

from __future__ import annotations

from pathlib import Path

NAVY = "#314A73"
DEEP = "#132847"
MID = "#33547F"
RED = "#C41E3A"
GOLD = "#C4A574"

HERE = Path(__file__).resolve().parent

ICONS: dict[str, str] = {
    "content-strategist": f"""
  <polygon fill="{DEEP}" points="14,8 42,8 50,16 50,56 14,56"/>
  <polygon fill="{NAVY}" points="14,8 42,8 42,20 14,20"/>
  <polygon fill="{MID}" points="42,8 50,16 42,16"/>
  <polygon fill="{RED}" points="20,28 44,28 42,32 18,32"/>
  <polygon fill="{GOLD}" points="20,38 36,38 35,42 19,42"/>
  <polygon fill="{MID}" points="20,48 32,48 31,52 19,52"/>
""",
    "seo-specialist": f"""
  <polygon fill="{NAVY}" points="10,14 30,8 46,18 40,38 20,42 8,28"/>
  <polygon fill="{MID}" points="16,18 30,14 40,22 36,34 22,36 14,26"/>
  <polygon fill="{RED}" points="24,22 32,20 34,28 26,30"/>
  <polygon fill="{DEEP}" points="38,36 56,52 50,56 34,40"/>
  <polygon fill="{GOLD}" points="12,48 16,40 20,48 18,56 14,56"/>
""",
    "social-media-manager": f"""
  <polygon fill="{NAVY}" points="8,16 28,10 38,20 30,34 10,36"/>
  <polygon fill="{MID}" points="14,18 26,15 32,22 26,30 14,31"/>
  <polygon fill="{DEEP}" points="26,34 34,30 38,40 28,44"/>
  <polygon fill="{NAVY}" points="30,28 54,22 58,36 46,50 28,46"/>
  <polygon fill="{RED}" points="38,32 48,30 50,38 40,40"/>
  <polygon fill="{GOLD}" points="18,22 22,22 22,26 18,26"/>
""",
    "paid-media-specialist": f"""
  <polygon fill="{DEEP}" points="32,6 54,18 48,42 32,58 16,42 10,18"/>
  <polygon fill="{NAVY}" points="32,12 48,20 44,38 32,50 20,38 16,20"/>
  <polygon fill="{MID}" points="32,20 40,26 38,36 32,42 26,36 24,26"/>
  <polygon fill="{RED}" points="32,26 36,30 32,36 28,30"/>
  <polygon fill="{GOLD}" points="30,4 34,4 36,10 28,10"/>
""",
    "lifecycle-marketer": f"""
  <polygon fill="{NAVY}" points="18,10 40,8 50,20 42,22 34,14 20,16"/>
  <polygon fill="{MID}" points="42,14 54,18 56,34 48,36 46,22"/>
  <polygon fill="{DEEP}" points="46,32 56,38 44,54 32,56 34,46 46,40"/>
  <polygon fill="{NAVY}" points="14,36 24,38 28,50 16,56 8,46"/>
  <polygon fill="{RED}" points="10,20 20,16 22,26 12,30"/>
  <polygon fill="{GOLD}" points="36,28 44,30 40,38 32,34"/>
""",
    "marketing-analyst": f"""
  <polygon fill="{DEEP}" points="8,8 14,8 14,56 8,56"/>
  <polygon fill="{NAVY}" points="18,36 30,36 30,56 18,56"/>
  <polygon fill="{MID}" points="34,24 46,24 46,56 34,56"/>
  <polygon fill="{RED}" points="50,12 60,12 60,56 50,56"/>
  <polygon fill="{GOLD}" points="18,20 28,14 46,18 58,8 54,16 44,22 28,18"/>
""",
    "lead-sourcer": f"""
  <polygon fill="{DEEP}" points="32,8 52,24 46,24 46,52 18,52 18,24 12,24"/>
  <polygon fill="{NAVY}" points="32,12 44,24 20,24"/>
  <polygon fill="{MID}" points="22,28 42,28 42,48 22,48"/>
  <polygon fill="{RED}" points="28,34 36,34 36,48 28,48"/>
  <polygon fill="{GOLD}" points="30,18 34,18 34,22 30,22"/>
""",
    "email-warmer": f"""
  <polygon fill="{NAVY}" points="8,16 56,16 56,48 8,48"/>
  <polygon fill="{DEEP}" points="8,16 32,32 56,16 56,22 32,38 8,22"/>
  <polygon fill="{MID}" points="8,22 32,38 8,48"/>
  <polygon fill="{MID}" points="56,22 56,48 32,38"/>
  <polygon fill="{RED}" points="24,20 40,20 38,24 26,24"/>
  <polygon fill="{GOLD}" points="48,40 54,40 54,46 48,46"/>
""",
    "cold-call-script-writer": f"""
  <polygon fill="{NAVY}" points="20,6 36,6 40,14 40,34 16,34 16,14"/>
  <polygon fill="{MID}" points="22,12 34,12 34,16 22,16"/>
  <polygon fill="{DEEP}" points="22,20 32,20 32,24 22,24"/>
  <polygon fill="{NAVY}" points="28,34 38,46 32,56 18,48 20,38"/>
  <polygon fill="{RED}" points="30,38 36,46 32,50 26,42"/>
  <polygon fill="{GOLD}" points="42,18 54,26 48,34 38,26"/>
""",
    "follow-up-sequencer": f"""
  <polygon fill="{NAVY}" points="6,36 18,28 26,36 18,48 6,44"/>
  <polygon fill="{MID}" points="24,24 38,16 48,26 38,38 26,32"/>
  <polygon fill="{DEEP}" points="46,12 58,8 62,20 52,28 44,22"/>
  <polygon fill="{RED}" points="38,16 48,14 46,22 36,22"/>
  <polygon fill="{GOLD}" points="14,30 20,28 20,34 14,34"/>
""",
    "market-researcher": f"""
  <polygon fill="{DEEP}" points="8,44 20,20 28,28 22,44"/>
  <polygon fill="{NAVY}" points="24,40 34,12 44,22 36,44"/>
  <polygon fill="{MID}" points="40,40 50,16 60,28 52,48"/>
  <polygon fill="{RED}" points="18,16 26,10 30,18 22,22"/>
  <polygon fill="{GOLD}" points="8,50 60,50 60,56 8,56"/>
""",
    "trade-journal": f"""
  <polygon fill="{DEEP}" points="10,10 32,16 32,56 10,50"/>
  <polygon fill="{NAVY}" points="54,10 32,16 32,56 54,50"/>
  <polygon fill="{MID}" points="14,16 28,20 28,48 14,44"/>
  <polygon fill="{MID}" points="50,16 36,20 36,48 50,44"/>
  <polygon fill="{RED}" points="30,14 34,14 34,54 30,54"/>
  <polygon fill="{GOLD}" points="18,24 26,26 26,30 18,28"/>
""",
    "risk-analyst": f"""
  <polygon fill="{NAVY}" points="32,6 54,16 50,36 32,58 14,36 10,16"/>
  <polygon fill="{MID}" points="32,12 48,20 44,36 32,50 20,36 16,20"/>
  <polygon fill="{DEEP}" points="28,24 36,24 36,34 28,34"/>
  <polygon fill="{RED}" points="30,38 34,38 34,44 30,44"/>
  <polygon fill="{GOLD}" points="24,20 32,16 40,20 36,24 28,24"/>
""",
    "news-scanner": f"""
  <polygon fill="{DEEP}" points="32,8 36,32 32,36 28,32"/>
  <polygon fill="{NAVY}" points="16,18 24,14 28,22 22,28 14,24"/>
  <polygon fill="{NAVY}" points="48,18 40,14 36,22 42,28 50,24"/>
  <polygon fill="{MID}" points="12,36 22,32 26,42 16,48 8,42"/>
  <polygon fill="{MID}" points="52,36 42,32 38,42 48,48 56,42"/>
  <polygon fill="{RED}" points="28,28 36,28 36,36 28,36"/>
  <polygon fill="{GOLD}" points="30,44 34,44 38,56 26,56"/>
""",
    "seat": f"""
  <polygon fill="{NAVY}" points="20,12 44,12 52,28 32,54 12,28"/>
  <polygon fill="{MID}" points="24,16 40,16 44,28 32,46 20,28"/>
  <polygon fill="{RED}" points="28,24 36,24 36,32 28,32"/>
  <polygon fill="{GOLD}" points="30,18 34,18 34,22 30,22"/>
""",
}


def write_icons(dest: Path = HERE) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for seat_id, body in ICONS.items():
        path = dest / f"{seat_id}.svg"
        path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img">\n'
            f"{body.rstrip()}\n"
            "</svg>\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> int:
    paths = write_icons()
    print(f"wrote {len(paths)} seat icons under {HERE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
