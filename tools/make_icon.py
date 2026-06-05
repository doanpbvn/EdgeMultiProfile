"""Convert assets/icon.png into a square multi-size assets/icon.ico.

Run once before building the exe:
    python tools/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "icon.png"
DST = ROOT / "assets" / "icon.ico"
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def make_square(img: Image.Image) -> Image.Image:
    """Pad the image with transparency so it becomes a centered square."""
    img = img.convert("RGBA")
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset = ((side - img.width) // 2, (side - img.height) // 2)
    canvas.paste(img, offset, img)
    return canvas


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Source icon not found: {SRC}")
    square = make_square(Image.open(SRC))
    square.save(DST, format="ICO", sizes=ICO_SIZES)
    print(f"Created {DST}")


if __name__ == "__main__":
    main()
