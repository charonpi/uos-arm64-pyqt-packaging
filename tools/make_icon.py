#!/usr/bin/env python3
"""Generate the 512x512 PNG icon used for the WorkBuddy skill marketplace.

Only requires Pillow. Output: assets/icon-512.png (kept under 500 KB).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "uos-arm64-pyqt-packaging" / "assets" / "icon-512.png"
SIZE = 512


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def main():
    img = Image.new("RGB", (SIZE, SIZE), "#0b1220")
    d = ImageDraw.Draw(img)
    # vertical gradient
    for y in range(SIZE):
        t = y / (SIZE - 1)
        r = int(0x0b + (0x16 - 0x0b) * t)
        g = int(0x12 + (0x3a - 0x12) * t)
        b = int(0x20 + (0x64 - 0x20) * t)
        d.line([(0, y), (SIZE, y)], fill=(r, g, b))

    # soft card
    d.rounded_rectangle([40, 40, 472, 472], radius=48, fill="#10233c", outline="#2f6fb5", width=3)

    # chip body + pins (aarch64 / packaging motif)
    cx, cy, half = 256, 218, 78
    for i in range(5):
        off = -56 + i * 28
        d.line([(cx + off, cy - half - 34), (cx + off, cy - half)], fill="#63b3ff", width=8)
        d.line([(cx + off, cy + half), (cx + off, cy + half + 34)], fill="#63b3ff", width=8)
        d.line([(cx - half - 34, cy + off), (cx - half, cy + off)], fill="#63b3ff", width=8)
        d.line([(cx + half, cy + off), (cx + half + 34, cy + off)], fill="#63b3ff", width=8)
    d.rounded_rectangle([cx - half, cy - half, cx + half, cy + half], radius=18,
                        fill="#1d4a7d", outline="#8fd0ff", width=5)
    d.rounded_rectangle([cx - 42, cy - 42, cx + 42, cy + 42], radius=10, fill="#0d2a4c")
    d.text((cx, cy - 6), "UOS", font=font(30, True), fill="#e8f4ff", anchor="mm")

    # captions
    d.text((256, 350), "arm64  /  glibc 2.28", font=font(26, True), fill="#eaf4ff", anchor="mm")
    d.text((256, 394), "PyQt5  ->  .deb", font=font(24), fill="#8fc7ff", anchor="mm")
    d.rounded_rectangle([120, 424, 392, 452], radius=14, fill="#1b4a7a")
    d.text((256, 438), "ARCH: ALL", font=font(20, True), fill="#ffffff", anchor="mm")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print("wrote %s (%d bytes, %dx%d)" % (OUT, OUT.stat().st_size, *img.size))


if __name__ == "__main__":
    main()
