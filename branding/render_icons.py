"""Render every Dragon AI icon from the canonical low-poly dragon artwork.

The artwork (branding/dragon-logo.png) is used as-is: it is only cropped to its
visible bounds, centered on a transparent square and resampled.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "branding" / "dragon-logo.png"
DESKTOP = ROOT / "apps" / "desktop"


def square(size: int, padding: float = 0.06) -> Image.Image:
    art = Image.open(SOURCE).convert("RGBA")
    art = art.crop(art.getchannel("A").getbbox())
    inner = round(size * (1 - 2 * padding))
    scale = inner / max(art.size)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(art, ((size - art.width) // 2, (size - art.height) // 2), art)
    return canvas


def main() -> None:
    assets = DESKTOP / "assets"
    public = DESKTOP / "public"
    big = square(1024)
    for name in ("icon.png", "icon-dark.png", "icon-mac.png"):
        big.save(assets / name)
    ico_sizes = [(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)]
    for name in ("icon.ico", "icon-dark.ico"):
        square(256, 0.02).save(assets / name, sizes=ico_sizes)
    for name in ("icon.icns", "icon-dark.icns"):
        big.save(assets / name)
    composer = assets / "icon.icon" / "Assets"
    for png in composer.glob("*.png"):
        square(1024, 0.12).save(png)
    square(180, 0.04).save(public / "apple-touch-icon.png")
    square(512, 0.02).save(public / "dragon-logo.png")
    square(256, 0.02).save(ROOT / "branding" / "dragon-logo-256.png")
    square(256, 0.02).save(ROOT / "branding" / "dragon-logo.ico", sizes=ico_sizes)


if __name__ == "__main__":
    main()
