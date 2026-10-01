#!/usr/bin/env python3
"""Contain-max the sidebar Dragon mark into the Windows tray / taskbar slot.

Windows owns the cell size. Do not pick a fixed display pixel size.
Scale the transparent navy low-poly dragon uniformly to the largest
width and height that fit the slot (CSS object-fit: contain at max
scale). No crop, no stretch. Same ICO for taskbar and shortcuts.

Rebuild:
  python3 branding/tray_icon.py
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BADGE_SOURCE = ROOT / "installer" / "winres" / "icon-source.png"
WINRES_ICO = ROOT / "installer" / "winres" / "icon.ico"
NAVY_PNG = HERE / "dragon-ai-agent-logo.png"
BRAND_ICO = HERE / "dragon-ai-agent-logo.ico"
SIDEBAR_MARK = NAVY_PNG

# Frames Windows may request for tray / taskbar / shortcuts.
# These are slot sizes, not a "draw the icon at 48px" bump.
ICO_SLOT_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)

ALPHA_MIN = 8


def opaque_bbox(im: Image.Image, alpha_min: int = ALPHA_MIN) -> tuple[int, int, int, int] | None:
    """Inclusive-exclusive bbox of pixels with alpha > alpha_min."""
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    mask = alpha.point(lambda a: 255 if a > alpha_min else 0)
    box = mask.getbbox()
    return box


def contain_fit_max(im: Image.Image, size: int) -> Image.Image:
    """Scale artwork uniformly to the largest size that fits a size×size slot.

    Equivalent to width/height 100% + object-fit: contain. Centers the result.
    Transparent padding only on the unused axis when the mark is not square.
    """
    if size < 1:
        raise ValueError("slot size must be positive")
    src = im.convert("RGBA")
    box = opaque_bbox(src)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if box is None:
        return canvas
    cropped = src.crop(box)
    cw, ch = cropped.size
    if cw < 1 or ch < 1:
        return canvas
    scale = min(size / cw, size / ch)
    nw = max(1, min(size, int(round(cw * scale))))
    nh = max(1, min(size, int(round(ch * scale))))
    fitted = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = (size - nw) // 2
    oy = (size - nh) // 2
    canvas.paste(fitted, (ox, oy), fitted)
    return canvas


def _near_black(r: int, g: int, b: int, a: int) -> bool:
    return a <= ALPHA_MIN or (max(r, g, b) <= 55 and max(abs(r - g), abs(g - b), abs(r - b)) <= 32)


def isolate_dragon_artwork(im: Image.Image) -> Image.Image:
    """Treat plate + outer ring as empty container; keep the dragon.

    The circular badge fills the ICO canvas. The dragon inside does not.
    Punch near-black field and the outer copper shell so contain-max can
    enlarge the dragon to the slot. Does not stretch or crop the dragon.
    """
    src = im.convert("RGBA")
    w, h = src.size
    px = src.load()
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    colorful_r = 0.0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if _near_black(r, g, b, a):
                continue
            colorful_r = max(colorful_r, math.hypot(x - cx, y - cy))
    # ~12px shell at 256; enough to drop the copper rim, not horn tips.
    shell = max(3.0, (12.0 / 256.0) * max(w, h))
    keep_r = max(0.0, colorful_r - shell)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dest = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if _near_black(r, g, b, a):
                continue
            if math.hypot(x - cx, y - cy) > keep_r:
                continue
            dest[x, y] = (r, g, b, a)
    return out


def write_ico(im: Image.Image, dest: Path, sizes: tuple[int, ...] = ICO_SLOT_SIZES) -> Path:
    """Write a multi-size ICO. Each frame is contain-maxed into that slot."""
    master = contain_fit_max(im, max(sizes))
    buf = io.BytesIO()
    # Pillow downscales `master` for `sizes`. master is already contain-maxed,
    # so every frame stays contain-maxed (no extra plate padding).
    master.save(buf, format="ICO", sizes=[(s, s) for s in sizes])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(buf.getvalue())
    return dest


def load_sidebar_mark() -> Image.Image:
    """Transparent navy low-poly dragon used in the sidebar lockup.

    Reads larger in the Windows tray/taskbar slot than the circular
    copper badge (no plate, no leftover rim).
    """
    if SIDEBAR_MARK.is_file():
        return Image.open(SIDEBAR_MARK).convert("RGBA")
    if BRAND_ICO.is_file():
        return Image.open(BRAND_ICO).convert("RGBA")
    raise FileNotFoundError("sidebar mark missing (dragon-ai-agent-logo.png / .ico)")


def _load_badge_source() -> Image.Image:
    if BADGE_SOURCE.is_file():
        return Image.open(BADGE_SOURCE).convert("RGBA")
    if WINRES_ICO.is_file():
        return Image.open(WINRES_ICO).convert("RGBA")
    raise FileNotFoundError("circular badge source missing (icon-source.png / icon.ico)")


def rebuild() -> dict[str, str]:
    dragon = load_sidebar_mark()
    write_ico(dragon, WINRES_ICO)
    write_ico(dragon, BRAND_ICO)
    return {
        "taskbar": str(WINRES_ICO.relative_to(ROOT)),
        "shortcuts": str(BRAND_ICO.relative_to(ROOT)),
        "source": "sidebar-mark",
        "fit": "contain-max",
    }


def self_test() -> int:
    src = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for y in range(8, 24):
        for x in range(10, 18):
            src.putpixel((x, y), (196, 30, 58, 255))
    out = contain_fit_max(src, 32)
    box = opaque_bbox(out)
    if box is None:
        print("FAIL: self-test empty", file=sys.stderr)
        return 1
    l, t, r, b = box
    fw, fh = r - l, b - t
    if max(fw, fh) < 30:
        print(f"FAIL: self-test did not fill slot ({fw}x{fh})", file=sys.stderr)
        return 1
    if abs((fw / fh) - (8 / 16)) > 0.08:
        print(f"FAIL: self-test aspect {fw}x{fh}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Contain-max Dragon tray/taskbar ICO")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    summary = rebuild()
    print("contain-max tray/taskbar ICO:", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
