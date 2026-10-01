#!/usr/bin/env python3
"""Offline tests for contain-max tray / taskbar dragon sizing.

Windows owns the slot. We must not pick a fixed display pixel size.
The dragon artwork scales uniformly to the largest size that fits the
cell (object-fit: contain at max scale). No crop, no stretch.

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / "branding"
SCRIPTS = ROOT / "scripts" / "airmaze"
WINRES_ICO = ROOT / "installer" / "winres" / "icon.ico"
BRAND_ICO = BRANDING / "dragon-ai-agent-logo.ico"
NOTE = ROOT / "docs" / "airmaze" / "TRAY_ICON.md"
LAUNCHER = ROOT / "scripts" / "airmaze" / "start-embedded.ps1"
TABLE = SCRIPTS / "desktop_branding.json"

# Slots Windows actually requests. Not a display-size bump.
REQUIRED_ICO_SIZES = {(16, 16), (24, 24), (32, 32), (48, 48), (256, 256)}
FORBIDDEN_FIXED_PX = (
    "TRAY_ICON_PX",
    "TASKBAR_ICON_PX",
    "trayIconSize = 48",
    "trayIconSize=48",
    "iconSize: 48",
    "width: 48px",
    "height: 48px",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def ico_sizes(path: Path) -> set[tuple[int, int]]:
    data = path.read_bytes()
    if data[:4] != b"\x00\x00\x01\x00":
        fail(f"{path.name} is not an ICO")
    count = struct.unpack_from("<H", data, 4)[0]
    sizes: set[tuple[int, int]] = set()
    for i in range(count):
        off = 6 + i * 16
        width, height = struct.unpack_from("<BB", data, off)
        sizes.add((256 if width == 0 else width, 256 if height == 0 else height))
    return sizes


def test_engine_contain_max() -> None:
    sys.path.insert(0, str(BRANDING))
    import tray_icon as tray  # noqa: WPS433

    try:
        from PIL import Image
    except ImportError:
        fail("Pillow is required to prove contain-max (pip install Pillow)")

    # Padded 64x64 canvas, 20x30 mark — same problem as a small dragon in a slot.
    src = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for y in range(17, 47):
        for x in range(22, 42):
            src.putpixel((x, y), (49, 74, 115, 255))
    fitted = tray.contain_fit_max(src, 64)
    if fitted.size != (64, 64):
        fail(f"contain-max must return the slot size, got {fitted.size}")
    bbox = tray.opaque_bbox(fitted)
    if bbox is None:
        fail("contain-max produced an empty image")
    l, t, r, b = bbox
    fw, fh = r - l, b - t
    # Larger axis fills the slot (contain at max scale).
    if max(fw, fh) < 62:
        fail(f"contain-max must fill the slot on the long axis, got {fw}x{fh}")
    if abs((fw / fh) - (20 / 30)) > 0.04:
        fail(f"contain-max must keep aspect ratio, got {fw}x{fh}")
    if fw > 64 or fh > 64:
        fail("contain-max must not overflow the slot")
    # No crop: every source opaque pixel has a counterpart (area ratio).
    src_area = 20 * 30
    out_area = fw * fh
    if out_area + 1 < src_area:
        fail("contain-max cropped the artwork")
    print("OK  contain_fit_max unit")


def test_shipped_icos_contain_max() -> None:
    sys.path.insert(0, str(BRANDING))
    import tray_icon as tray  # noqa: WPS433

    try:
        from PIL import Image
    except ImportError:
        fail("Pillow is required to inspect ICO frames")

    for path, label in ((WINRES_ICO, "taskbar/winres"), (BRAND_ICO, "shortcut/branding")):
        sizes = ico_sizes(path)
        missing = REQUIRED_ICO_SIZES - sizes
        if missing:
            fail(f"{label} ICO missing Windows slot frames {sorted(missing)} (have {sorted(sizes)})")
        im = Image.open(path).convert("RGBA")
        bbox = tray.opaque_bbox(im)
        if bbox is None:
            fail(f"{label} ICO has no opaque artwork")
        l, t, r, b = bbox
        fw, fh = r - l, b - t
        w, h = im.size
        fill = max(fw / w, fh / h)
        if fill < 0.92:
            fail(
                f"{label} dragon does not contain-max the slot "
                f"(long-axis fill {fill:.3f} on {fw}x{fh} in {w}x{h})"
            )
        if abs(fw / w - 1) < 0.001 and abs(fh / h - 1) < 0.001:
            # Full-bleed on both axes is fine (square art).
            pass
        elif min(fw / w, fh / h) < 0.05:
            fail(f"{label} ICO looks cropped or empty on one axis")
    print("OK  shipped ICO frames contain-max the slot")


def test_no_fixed_pixel_bump() -> None:
    engine = (BRANDING / "tray_icon.py").read_text(encoding="utf-8")
    for needle in FORBIDDEN_FIXED_PX:
        if needle in engine:
            fail(f"tray_icon.py must not hard-code a display size bump ({needle})")
    if "contain_fit_max" not in engine or "object-fit" not in engine.lower() and "contain" not in engine:
        fail("tray_icon.py must implement contain-max (CSS object-fit: contain equivalent)")
    note = NOTE.read_text(encoding="utf-8")
    if "contain-max" not in note.lower() and "contain max" not in note.lower():
        fail("docs/airmaze/TRAY_ICON.md must name contain-max")
    if "object-fit" not in note and "contain" not in note.lower():
        fail("design note must describe contain-fit")
    if "22rem" in engine or "sidebar" in engine and "32px" in engine:
        fail("tray sizer must not retune empty-state or sidebar chrome")
    table = TABLE.read_text(encoding="utf-8")
    if "contain-max" not in table and "containMax" not in table:
        fail("desktop_branding.json must record tray contain-max")
    print("OK  no fixed pixel bump")


def test_overlay_and_docker_untouched() -> None:
    branding_py = (SCRIPTS / "desktop_branding.py").read_text(encoding="utf-8")
    if "stamp_app_icon" not in branding_py or "icon.ico" not in branding_py:
        fail("overlay must still copy the Dragon ICO to resources/icon.ico")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    for token in (
        "openUIOnStartupDisabled",
        "Start-DockerIfNeeded",
        "Starting Docker Desktop (system tray)",
    ):
        if token not in launcher:
            fail(f"tray-icon work must not drop Docker tray-only launch ({token})")
    if "9119" in (BRANDING / "tray_icon.py").read_text(encoding="utf-8"):
        fail("tray_icon.py must not open the Dragon dashboard")
    print("OK  overlay copy + Docker tray-only unchanged")


def test_self() -> None:
    sys.path.insert(0, str(BRANDING))
    import tray_icon as tray  # noqa: WPS433

    if tray.self_test() != 0:
        fail("branding/tray_icon.py --self-test failed")
    print("OK  tray_icon self-test")


def main() -> int:
    test_engine_contain_max()
    test_shipped_icos_contain_max()
    test_no_fixed_pixel_bump()
    test_overlay_and_docker_untouched()
    test_self()
    print("SMOKE OK: tray/taskbar dragon contain-maxes the Windows slot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
