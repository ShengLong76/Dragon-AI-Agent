#!/usr/bin/env python3
"""Render the Dragon AI Agent low-poly mark (SVG + PNG + ICO).

Same facing as the existing product logo: front-facing head, both eyes
to the viewer, red facets, gold horns, copper ring. The neck is a
separate coil around the head (dark gap), not a side profile.
Few facets so 16–32px still reads. Pillow for raster/ICO only.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent

BG = "#1C1C20"
RING = "#C4A574"
RED = "#C41E3A"
RED_DARK = "#8E1528"
RED_LIGHT = "#E23A54"
GOLD = "#E8C36A"
GOLD_DARK = "#B8863A"
EYE = "#F5C14A"

CX, CY = 128.0, 128.0


def _pt(angle_deg: float, radius: float) -> tuple[int, int]:
    rad = math.radians(angle_deg)
    return (int(round(CX + radius * math.cos(rad))), int(round(CY + radius * math.sin(rad))))


def _ring_seg(a0: float, a1: float, r_out: float, r_in: float) -> list[tuple[int, int]]:
    return [_pt(a0, r_out), _pt(a1, r_out), _pt(a1, r_in), _pt(a0, r_in)]


def _neck() -> list[tuple[str, list[tuple[int, int]]]]:
    # Horseshoe coil around the head. 0° is east, 90° south. Skip the top (~240–300°)
    # so gold horns stay in the dark gap, like the existing product logo.
    stops = [300, 340, 20, 70, 115, 160, 200, 235]
    colors = [RED_DARK, RED, RED_LIGHT, RED, RED_DARK, RED, RED_LIGHT]
    out: list[tuple[str, list[tuple[int, int]]]] = []
    for i, color in enumerate(colors):
        out.append((color, _ring_seg(stops[i], stops[i + 1], 116, 76)))
    return out


POLYS: list[tuple[str, list[tuple[int, int]]]] = _neck() + [
    # gold horns — swept out from the crown, facing the viewer
    (GOLD, [(54, 28), (96, 84), (50, 80)]),
    (GOLD_DARK, [(50, 80), (96, 84), (74, 96)]),
    (GOLD, [(86, 14), (118, 80), (78, 82)]),
    (GOLD_DARK, [(78, 82), (118, 80), (102, 94)]),
    (GOLD, [(170, 14), (178, 82), (138, 80)]),
    (GOLD_DARK, [(138, 80), (178, 82), (154, 94)]),
    (GOLD, [(202, 28), (206, 80), (160, 84)]),
    (GOLD_DARK, [(160, 84), (206, 80), (182, 96)]),
    # cranium (island inside the coil)
    (RED, [(84, 88), (118, 76), (138, 76), (172, 88), (182, 118), (168, 150), (88, 150), (74, 118)]),
    (RED_LIGHT, [(118, 76), (128, 68), (138, 76), (146, 108), (110, 108)]),
    (RED_DARK, [(88, 150), (168, 150), (154, 172), (102, 172)]),
    # snout toward the viewer
    (RED_LIGHT, [(108, 142), (128, 178), (148, 142)]),
    (RED_DARK, [(108, 142), (128, 156), (148, 142)]),
    # cheeks
    (RED_DARK, [(74, 118), (88, 150), (98, 140), (82, 108)]),
    (RED_DARK, [(182, 118), (174, 108), (158, 140), (168, 150)]),
    # brows
    (RED_DARK, [(90, 98), (118, 106), (100, 116), (80, 106)]),
    (RED_DARK, [(166, 98), (176, 106), (156, 116), (138, 106)]),
    # eyes — both toward the viewer
    (EYE, [(96, 110), (114, 120), (98, 130), (82, 120)]),
    (EYE, [(160, 110), (174, 120), (158, 130), (142, 120)]),
]


def _svg() -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="Dragon AI Agent">',
        f'  <circle cx="128" cy="128" r="124" fill="{BG}"/>',
        f'  <circle cx="128" cy="128" r="120" fill="none" stroke="{RING}" stroke-width="6"/>',
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
    r_outer = 124 * scale
    r_inner = 120 * scale
    dr.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), fill=BG)
    dr.ellipse(
        (
            cx - r_inner - 3 * scale,
            cy - r_inner - 3 * scale,
            cx + r_inner + 3 * scale,
            cy + r_inner + 3 * scale,
        ),
        outline=RING,
        width=6 * scale,
    )
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
    print("wrote SVG, PNG, 256 PNG, ICO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
