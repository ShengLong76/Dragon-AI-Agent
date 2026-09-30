#!/usr/bin/env python3
"""Render the Dragon AI Agent low-poly mark (SVG + PNG + ICO).

Front-facing head, both eyes to the viewer. Large flat blue facets;
horns the same blue as the body; red eyes. No gold, no copper ring,
not a side profile. Pillow for raster/ICO only.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent

BG = "#1C1C20"
BLUE = "#2563EB"
BLUE_DARK = "#1E3A8A"
BLUE_LIGHT = "#3B82F6"
EYE = "#C41E3A"

# Few large facets. Front-facing coiled dragon.
POLYS: list[tuple[str, list[tuple[int, int]]]] = [
    # neck coil — three slabs, dark gap under the head
    (BLUE_DARK, [(28, 96), (84, 156), (56, 212), (16, 152)]),
    (BLUE, [(56, 212), (128, 236), (200, 212), (172, 156), (84, 156)]),
    (BLUE_DARK, [(228, 96), (240, 152), (200, 212), (172, 156)]),
    # horns — same blue as the body
    (BLUE_LIGHT, [(58, 18), (108, 88), (52, 84)]),
    (BLUE_LIGHT, [(198, 18), (204, 84), (148, 88)]),
    # head
    (BLUE, [(80, 86), (128, 70), (176, 86), (188, 128), (168, 164), (88, 164), (68, 128)]),
    (BLUE_LIGHT, [(108, 86), (128, 70), (148, 86), (140, 120), (116, 120)]),
    (BLUE_DARK, [(88, 164), (168, 164), (152, 188), (104, 188)]),
    # snout toward the viewer
    (BLUE_LIGHT, [(108, 148), (128, 186), (148, 148)]),
    # eyes — red, both toward the viewer
    (EYE, [(92, 112), (114, 124), (96, 136), (78, 122)]),
    (EYE, [(164, 112), (178, 122), (160, 136), (142, 124)]),
]


def _svg() -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="Dragon AI Agent">',
        f'  <circle cx="128" cy="128" r="124" fill="{BG}"/>',
    ]
    for color, pts in POLYS:
        d = " ".join(f"{x},{y}" for x, y in pts)
        parts.append(f'  <polygon fill="{color}" points="{d}"/>')
    parts.append("</svg>")
    parts.append("")
    return "\n".join(parts)


def _paint(size: int) -> Image.Image:
    scale = max(4, 1024 // max(size, 1))
    src = 256 * scale
    im = Image.new("RGBA", (src, src), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    cx = cy = src / 2
    r = 124 * scale
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BG)
    for color, pts in POLYS:
        dr.polygon([(x * scale, y * scale) for x, y in pts], fill=color)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    (HERE / "dragon-ai-agent-logo.svg").write_text(_svg(), encoding="utf-8")
    big = _paint(1024)
    big.save(HERE / "dragon-ai-agent-logo.png")
    mid = big.resize((256, 256), Image.Resampling.LANCZOS)
    mid.save(HERE / "dragon-ai-agent-logo-256.png")
    buf = io.BytesIO()
    mid.save(buf, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    (HERE / "dragon-ai-agent-logo.ico").write_bytes(buf.getvalue())
    print(f"wrote SVG ({_svg().count('<polygon')} polys), PNG, 256 PNG, ICO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
