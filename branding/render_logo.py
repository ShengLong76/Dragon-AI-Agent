#!/usr/bin/env python3
"""Render the Dragon AI Agent mark James picked.

Front-facing navy low-poly dragon, coiled neck, horns the same navy,
red eyes. No gold, no copper ring, not a side profile.

PNG/ICO come from the attached reference (cropped to a square). SVG is
the same silhouette in a few large facets. Pillow for raster/ICO only.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REF_CANDIDATES = (
    Path("/home/ubuntu/.cursor/projects/workspace/assets/c8cebc9186040449d127430902e5c6ef25bad5102a743ea93cdebec19eb589d3.jpg"),
    HERE / "james-dragon-mark.jpg",
)

# Navy sampled from the attached mark (not bright #2563EB, not gold/copper).
BG = "#0A0A0A"
NAVY = "#314A73"
NAVY_DARK = "#132847"
NAVY_LIGHT = "#33547F"
EYE = "#C41E3A"

# Coiled neck + diamond head. Large facets only.
POLYS: list[tuple[str, list[tuple[int, int]]]] = [
    # neck ribbon: left, underside, tail, right
    (NAVY_DARK, [(46, 128), (78, 148), (58, 188), (28, 152)]),
    (NAVY, [(58, 188), (92, 228), (128, 214), (96, 176), (78, 148)]),
    (NAVY_LIGHT, [(92, 228), (118, 248), (148, 220), (128, 214)]),
    (NAVY, [(148, 220), (196, 176), (178, 148), (128, 214)]),
    (NAVY_DARK, [(196, 176), (228, 140), (200, 120), (178, 148)]),
    # horns — same navy
    (NAVY_LIGHT, [(78, 8), (108, 78), (72, 76)]),
    (NAVY_LIGHT, [(178, 8), (184, 76), (148, 78)]),
    # head (front, snout toward the viewer)
    (NAVY, [(88, 80), (128, 52), (168, 80), (184, 118), (164, 152), (92, 152), (72, 118)]),
    (NAVY_LIGHT, [(108, 78), (128, 52), (148, 78), (140, 108), (116, 108)]),
    (NAVY_DARK, [(92, 152), (164, 152), (148, 176), (108, 176)]),
    (NAVY_LIGHT, [(112, 148), (128, 178), (144, 148)]),
    # eyes — red, both toward the viewer
    (EYE, [(104, 100), (116, 108), (106, 116), (94, 108)]),
    (EYE, [(152, 100), (162, 108), (150, 116), (140, 108)]),
]


def _svg() -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="Dragon AI Agent">',
        f'  <rect width="256" height="256" rx="28" fill="{BG}"/>',
    ]
    for color, pts in POLYS:
        d = " ".join(f"{x},{y}" for x, y in pts)
        parts.append(f'  <polygon fill="{color}" points="{d}"/>')
    parts.append("</svg>")
    parts.append("")
    return "\n".join(parts)


def _find_ref() -> Path | None:
    for path in REF_CANDIDATES:
        if path.is_file():
            return path
    return None


def _crop_reference(src: Path, size: int) -> Image.Image:
    im = Image.open(src).convert("RGB")
    px = im.load()
    w, h = im.size
    xs: list[int] = []
    ys: list[int] = []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y][:3]
            if r + g + b > 36:
                xs.append(x)
                ys.append(y)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    pad = 36
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(w, right + pad)
    bottom = min(h, bottom + pad)
    crop = im.crop((left, top, right, bottom))
    side = max(crop.size)
    square = Image.new("RGB", (side, side), (10, 10, 10))
    ox = (side - crop.size[0]) // 2
    oy = (side - crop.size[1]) // 2
    square.paste(crop, (ox, oy))
    return square.resize((size, size), Image.Resampling.LANCZOS)


def _paint_svg(size: int) -> Image.Image:
    scale = max(4, 1024 // max(size, 1))
    src = 256 * scale
    im = Image.new("RGBA", (src, src), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rad = 28 * scale
    dr.rounded_rectangle((0, 0, src - 1, src - 1), radius=rad, fill=BG)
    for color, pts in POLYS:
        dr.polygon([(x * scale, y * scale) for x, y in pts], fill=color)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    (HERE / "dragon-ai-agent-logo.svg").write_text(_svg(), encoding="utf-8")
    ref = _find_ref()
    if ref is not None:
        big = _crop_reference(ref, 1024)
        mid = _crop_reference(ref, 256)
        print(f"rasters from {ref}")
    else:
        big = _paint_svg(1024).convert("RGB")
        mid = _paint_svg(256).convert("RGB")
        print("rasters from SVG facets (reference image not found)")
    big.save(HERE / "dragon-ai-agent-logo.png")
    mid.save(HERE / "dragon-ai-agent-logo-256.png")
    buf = io.BytesIO()
    mid.save(buf, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    (HERE / "dragon-ai-agent-logo.ico").write_bytes(buf.getvalue())
    # Keep a local copy so later rebuilds do not depend on the agent asset path.
    if ref is not None and ref.resolve() != (HERE / "james-dragon-mark.jpg").resolve():
        (HERE / "james-dragon-mark.jpg").write_bytes(ref.read_bytes())
    print(f"wrote SVG ({_svg().count('<polygon')} polys), PNG, 256 PNG, ICO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
