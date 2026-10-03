#!/usr/bin/env python3
"""Offline tests for contain-max tray / taskbar dragon sizing.

Windows owns the slot. We must not pick a fixed display pixel size.
The dragon artwork scales uniformly to the largest size that fits the
cell (object-fit: contain at max scale). No crop, no stretch.

The live ICO is the transparent sidebar mark (navy low-poly), not the
circular copper badge. Apply must copy that ICO onto Hermes resource
paths the running desktop client actually reads.

No secrets. Safe on Linux CI.
"""

from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / "branding"
SCRIPTS = ROOT / "scripts" / "airmaze"
WINRES_ICO = ROOT / "installer" / "winres" / "icon.ico"
DESKTOP_WINRES_ICO = ROOT / "desktop" / "winres" / "icon.ico"
PACKAGED_EXE = ROOT / "desktop" / "win-unpacked" / "DragonAIAgent.exe"
BRAND_ICO = BRANDING / "dragon-ai-agent-logo.ico"
SIDEBAR_PNG = BRANDING / "dragon-ai-agent-logo.png"
NOTE = ROOT / "docs" / "airmaze" / "TRAY_ICON.md"
LAUNCHER = ROOT / "scripts" / "airmaze" / "start-embedded.ps1"
APPLY = SCRIPTS / "Apply-DesktopBranding.ps1"
TABLE = SCRIPTS / "desktop_branding.json"
INSTALLERS = (
    ROOT / "scripts" / "airmaze" / "install.ps1",
    ROOT / "installer" / "DragonAIAgentSetup.ps1",
)

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

NAVY = (49, 74, 115)  # #314A73
COPPER_HINTS = (
    (196, 165, 116),  # #C4A574
    (232, 195, 106),  # #E8C36A
    (184, 134, 58),  # #B8863A
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


def iter_ico_frames(path: Path):
    try:
        from PIL import Image
    except ImportError:
        fail("Pillow is required to inspect ICO frames")
    sizes = ico_sizes(path)
    for size in sorted(sizes):
        im = Image.open(path)
        im.size = size
        im.load()
        yield size, im.convert("RGBA")


def _near(c: tuple[int, int, int], target: tuple[int, int, int], tol: int) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(c, target))


def count_navy_and_copper(im) -> tuple[int, int]:
    navy = 0
    copper = 0
    px = im.load()
    w, h = im.size
    step = max(1, min(w, h) // 64)
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b, a = px[x, y]
            if a <= 32:
                continue
            if _near((r, g, b), NAVY, 28):
                navy += 1
            if any(_near((r, g, b), hint, 36) for hint in COPPER_HINTS):
                copper += 1
    return navy, copper


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

    for path, label in ((WINRES_ICO, "taskbar/winres"), (BRAND_ICO, "shortcut/branding")):
        sizes = ico_sizes(path)
        missing = REQUIRED_ICO_SIZES - sizes
        if missing:
            fail(f"{label} ICO missing Windows slot frames {sorted(missing)} (have {sorted(sizes)})")
        for size, im in iter_ico_frames(path):
            bbox = tray.opaque_bbox(im)
            if bbox is None:
                fail(f"{label} ICO {size} has no opaque artwork")
            l, t, r, b = bbox
            fw, fh = r - l, b - t
            w, h = im.size
            fill = max(fw / w, fh / h)
            if fill < 0.92:
                fail(
                    f"{label} {size} dragon does not contain-max the slot "
                    f"(long-axis fill {fill:.3f} on {fw}x{fh} in {w}x{h})"
                )
            if fw > w or fh > h:
                fail(f"{label} {size} overflowed the slot")
            if min(fw / w, fh / h) < 0.05:
                fail(f"{label} {size} looks cropped or empty on one axis")
    if WINRES_ICO.read_bytes() != BRAND_ICO.read_bytes():
        fail("taskbar winres ICO and shortcut branding ICO must be the same enlarged sidebar mark")
    if not DESKTOP_WINRES_ICO.is_file() or DESKTOP_WINRES_ICO.read_bytes() != BRAND_ICO.read_bytes():
        fail("desktop/winres/icon.ico must be the current branding ICO (embedded in DragonAIAgent.exe)")
    print("OK  shipped ICO frames contain-max the slot")


def test_sidebar_mark_is_source() -> None:
    sys.path.insert(0, str(BRANDING))
    import tray_icon as tray  # noqa: WPS433

    engine = (BRANDING / "tray_icon.py").read_text(encoding="utf-8")
    if "load_sidebar_mark" not in engine and "dragon-ai-agent-logo.png" not in engine:
        fail("tray_icon.py must load the transparent sidebar PNG as the ICO source")
    if "def rebuild" in engine:
        rebuild_src = engine.split("def rebuild", 1)[-1].split("def ", 1)[0]
        if "isolate_dragon_artwork" in rebuild_src:
            fail("rebuild() must not isolate the circular copper badge for the shipped ICO")
        if "dragon-ai-agent-logo.png" not in rebuild_src and "load_sidebar_mark" not in rebuild_src:
            fail("rebuild() must write ICOs from the sidebar mark")
    if not SIDEBAR_PNG.is_file():
        fail("branding/dragon-ai-agent-logo.png (sidebar mark) is missing")

    for path, label in ((WINRES_ICO, "taskbar/winres"), (BRAND_ICO, "shortcut/branding")):
        navy = copper = 0
        for _size, im in iter_ico_frames(path):
            n, c = count_navy_and_copper(im)
            navy += n
            copper += c
        if navy < 8:
            fail(f"{label} ICO is not the navy sidebar mark (navy samples={navy})")
        if copper > 2:
            fail(f"{label} ICO still has circular-badge copper remnant (copper samples={copper})")
    print("OK  shipped ICOs are the navy sidebar mark")


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
    if "sidebar" not in note.lower():
        fail("design note must name the transparent sidebar mark as the ICO source")
    if "iconcache" not in note.lower() and "icon cache" not in note.lower():
        fail("design note must tell Cos how to refresh the Windows icon cache")
    if "relaunch" not in note.lower() and "close" not in note.lower():
        fail("design note must tell Cos to close Hermes.exe and relaunch")
    if "22rem" in engine or "sidebar" in engine and "32px" in engine:
        fail("tray sizer must not retune empty-state or sidebar chrome")
    table = TABLE.read_text(encoding="utf-8")
    if "contain-max" not in table and "containMax" not in table:
        fail("desktop_branding.json must record tray contain-max")
    if "sidebar" not in table.lower() and "sidebar-mark" not in table.lower():
        fail("desktop_branding.json must record the sidebar mark as the tray source")
    print("OK  no fixed pixel bump")


def test_apply_copies_hermes_icon_paths() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import desktop_branding as db  # noqa: WPS433

    src = db.icon_source()
    if src is None or src.name != "dragon-ai-agent-logo.ico":
        fail("icon_source() must prefer branding/dragon-ai-agent-logo.ico (installer already ships it)")
    png_src = SIDEBAR_PNG
    if not png_src.is_file() or png_src.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        fail("branding/dragon-ai-agent-logo.png must exist for Electron PNG / apple-touch-icon")

    stale = b"\x00\x00\x01\x00STALE-HERMES-ICON"
    stale_png = b"\x89PNG\r\n\x1a\nSTALE-HERMES-PNG"
    with tempfile.TemporaryDirectory(prefix="dragon-ico-apply-") as tmp:
        unpacked = Path(tmp) / "DragonAIAgent" / "desktop" / "win-unpacked"
        resources = unpacked / "resources"
        asar_unpacked = resources / "app.asar.unpacked"
        dist = asar_unpacked / "dist"
        app_dir = resources / "app"
        dist.mkdir(parents=True)
        app_dir.mkdir(parents=True)
        exe = unpacked / "Hermes.exe"
        exe.write_bytes(b"MZ")
        (asar_unpacked / "icon.ico").write_bytes(stale)
        (app_dir / "icon.ico").write_bytes(stale)
        (resources / "icon.ico").write_bytes(stale)
        (dist / "apple-touch-icon.png").write_bytes(stale_png)
        (resources / "icon.png").write_bytes(stale_png)

        summary = db.stamp_app_icon(exe)
        if summary.get("copied") is not True:
            fail(f"stamp_app_icon did not copy: {summary}")

        dests = [
            resources / "icon.ico",
            unpacked / "icon.ico",
            asar_unpacked / "icon.ico",
            app_dir / "icon.ico",
        ]
        src_bytes = src.read_bytes()
        png_bytes = png_src.read_bytes()
        for dest in dests:
            if not dest.is_file():
                fail(f"apply must copy the Dragon ICO to {dest.relative_to(unpacked)}")
            got = dest.read_bytes()
            if got == stale:
                fail(f"apply left a stale icon at {dest.relative_to(unpacked)}")
            if got[:4] != b"\x00\x00\x01\x00" or got != src_bytes:
                fail(f"apply did not install the sidebar ICO at {dest.relative_to(unpacked)}")

        png_dests = [
            resources / "icon.png",
            unpacked / "icon.png",
            dist / "apple-touch-icon.png",
        ]
        for dest in png_dests:
            if not dest.is_file():
                fail(f"apply must copy the Dragon PNG to {dest.relative_to(unpacked)}")
            got = dest.read_bytes()
            if got == stale_png:
                fail(f"apply left a stale Hermes PNG at {dest.relative_to(unpacked)}")
            if got != png_bytes:
                fail(f"tray/taskbar PNG must be the Dragon sidebar mark at {dest.relative_to(unpacked)}")

        dest_fn = getattr(db, "icon_destinations", None)
        if dest_fn is None:
            fail("desktop_branding.py must expose icon_destinations(exe_path)")
        named = {p.name for p in dest_fn(exe)}
        if "icon.ico" not in named:
            fail("icon_destinations must include icon.ico paths")

        standalone = Path(tmp) / "hermes" / "win-unpacked" / "Hermes.exe"
        standalone.parent.mkdir(parents=True, exist_ok=True)
        standalone.write_bytes(b"MZ")
        (standalone.parent / "resources").mkdir(parents=True, exist_ok=True)
        (standalone.parent / "resources" / "icon.ico").write_bytes(stale)
        try:
            db.stamp_app_icon(standalone)
            fail("stamp_app_icon must refuse branding outside DragonAIAgent")
        except ValueError as exc:
            if "Refuse branding outside DragonAIAgent" not in str(exc):
                fail(f"standalone refuse message unclear: {exc}")
        if (standalone.parent / "resources" / "icon.ico").read_bytes() != stale:
            fail("stamp_app_icon must not mutate standalone Hermes icon.ico")

    apply_ps = APPLY.read_text(encoding="utf-8")
    if "dragon-ai-agent-logo.ico" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy branding/dragon-ai-agent-logo.ico")
    brand_at = apply_ps.find("dragon-ai-agent-logo.ico")
    winres_at = apply_ps.find("installer\\winres\\icon.ico")
    if winres_at >= 0 and brand_at > winres_at:
        fail("Apply-DesktopBranding.ps1 must prefer the sidebar branding ICO over winres")
    if "app.asar.unpacked" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy the ICO onto app.asar.unpacked when that folder exists")
    if "icon.ico" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy icon.ico")
    if 'Join-Path $resourcesDir "icon.ico"' not in apply_ps and "resources\\icon.ico" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy the ICO to Hermes resources\\icon.ico")
    if "apple-touch-icon.png" not in apply_ps or "icon.png" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must copy Dragon PNG onto icon.png and apple-touch-icon.png")
    if "Refuse branding outside DragonAIAgent" not in apply_ps:
        fail("Apply-DesktopBranding.ps1 must refuse branding outside DragonAIAgent")
    print("OK  apply copies ICO+PNG onto Hermes resource paths (DragonAIAgent only)")


def test_installer_and_shortcuts() -> None:
    for path in INSTALLERS:
        text = path.read_text(encoding="utf-8")
        if "installer\\winres\\icon.ico" not in text and "installer/winres/icon.ico" not in text:
            fail(f"{path.name} must copy installer\\winres\\icon.ico into the install root")
        if "dragon-ai-agent-logo.ico" not in text:
            fail(f"{path.name} must still ship branding\\dragon-ai-agent-logo.ico for shortcuts")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    fn = launcher.split("function Repair-DragonAIProductShortcuts", 1)[-1]
    skip = fn.split("function ", 1)[0]
    if "continue" in skip:
        before, after = skip.split("continue", 1)
        if "IconLocation" not in before:
            fail(
                "Repair-DragonAIProductShortcuts must refresh IconLocation "
                "on an already-wscript shortcut (do not continue first)"
            )
    if "IconLocation" not in skip:
        fail("Repair-DragonAIProductShortcuts must set shortcut IconLocation")
    print("OK  installer ships winres ICO; shortcuts refresh IconLocation")


def test_overlay_and_docker_untouched() -> None:
    branding_py = (SCRIPTS / "desktop_branding.py").read_text(encoding="utf-8")
    if "stamp_app_icon" not in branding_py or "icon.ico" not in branding_py:
        fail("overlay must still copy the Dragon ICO to resources/icon.ico")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    for token in (
        "openUIOnStartupDisabled",
        "Start-DockerIfNeeded",
        "Set-DockerHeadlessSettings",
        "Hide-DockerDesktopUi",
    ):
        if token not in launcher:
            fail(f"tray-icon work must not drop invisible Docker engine start ({token})")
    if "9119" in (BRANDING / "tray_icon.py").read_text(encoding="utf-8"):
        fail("tray_icon.py must not open the Dragon dashboard")
    print("OK  overlay copy + invisible Docker engine start unchanged")


def test_self() -> None:
    sys.path.insert(0, str(BRANDING))
    import tray_icon as tray  # noqa: WPS433

    if tray.self_test() != 0:
        fail("branding/tray_icon.py --self-test failed")
    print("OK  tray_icon self-test")


def main() -> int:
    test_engine_contain_max()
    test_shipped_icos_contain_max()
    test_sidebar_mark_is_source()
    test_no_fixed_pixel_bump()
    test_apply_copies_hermes_icon_paths()
    test_installer_and_shortcuts()
    test_overlay_and_docker_untouched()
    test_self()
    print("SMOKE OK: tray/taskbar dragon contain-maxes the Windows slot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
