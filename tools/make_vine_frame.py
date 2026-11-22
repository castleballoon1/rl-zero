"""Make the vined panel frame used for every text box and menu.

Usage:  python tools/make_vine_frame.py
Needs:  pip install pillow   (only for this tool; the game doesn't need it)

Reads  assets/Sprites/Blank Vined Pixel-Art HUD Frame.png
Writes assets/Sprites/UI/vine_frame.png

The painted frame has a lot of empty space around it and a solid dark
inside. This trims the empty space and makes the inside see-through, so the
game can draw the inside itself at any opacity and stretch the frame to any
size (ui.panel cuts it into 9 pieces). The stones, vines and moss are kept.
Run it again if the frame is re-exported.
"""
import os
from collections import deque

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "Sprites", "Blank Vined Pixel-Art HUD Frame.png")
DST = os.path.join(ROOT, "assets", "Sprites", "UI", "vine_frame.png")


def inside(p):
    """The dark purple of the frame's inside (and its faint noise)."""
    r, g, b, a = p
    return a > 200 and 9 <= r <= 34 and g <= 14 and 11 <= b <= 36


def main():
    image = Image.open(SRC).convert("RGBA")
    # trim the empty space (the file has faint noise, so ignore alpha below 20)
    alpha = image.split()[3].point(lambda a: 255 if a > 20 else 0)
    image = image.crop(alpha.getbbox())
    w, h = image.size
    px = image.load()
    # flood fill the inside from its middle, so nothing outside the stones is touched
    seen = set()
    queue = deque([(w // 2, h // 2)])
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h) or not inside(px[x, y]):
            continue
        seen.add((x, y))
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    for x, y in seen:
        px[x, y] = (0, 0, 0, 0)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    image.save(DST)
    print(f"wrote {DST} ({w} x {h}, {len(seen)} inside pixels cleared)")


if __name__ == "__main__":
    main()
