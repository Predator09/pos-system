"""Regenerate ``assets/smartstock.ico`` from ``assets/app_icon.png`` (requires Pillow).

Run from ``pos-system``::

    python tools/make_app_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    assets = root / "assets"
    png = assets / "app_icon.png"
    ico = assets / "smartstock.ico"
    if not png.is_file():
        raise SystemExit(f"Missing source image: {png}")
    img = Image.open(png).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico, format="ICO", sizes=sizes)
    print(f"Wrote {ico}")


if __name__ == "__main__":
    main()
