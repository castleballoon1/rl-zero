"""Paint the grimoire out of the calm row of the child's sheet (columns 0-2).

Writes a full-size copy of the sheet; only row 0, columns 0-2 change.
"""
import sys
from PIL import Image, ImageDraw

SRC, DST = sys.argv[1], sys.argv[2]
CW = 256          # one picture is 256 x 341 (the sheet is 6 x 3)
CH = 341

# per frame: book corners (TL, TR, BR, BL), the near hand's box (kept),
# the line where his belly ends (x at y=140, x at y=232)
FRAMES = {
    0: dict(book=[(125, 144), (199, 153), (173, 233), (119, 222)], hand=(118, 198, 156, 228),
            belly=((160, 140), (169, 232))),
    1: dict(book=[(105, 143), (178, 152), (162, 233), (105, 224)], hand=(106, 198, 140, 228),
            belly=((148, 140), (155, 232))),
    2: dict(book=[(108, 146), (179, 155), (161, 234), (106, 226)], hand=(102, 198, 141, 228),
            belly=((150, 142), (157, 232))),
}
OUTLINE = (28, 20, 34, 255)


def shirtish(p):
    r, g, b, a = p
    return a > 200 and (b > r + 25 or g > r + 25) and max(r, g, b) > 60


def skinish(p):
    r, g, b, a = p
    return a > 200 and r > 195 and g > 110 and b > 75 and r - b > 60


BLUE = (60, 64, 182)
GREEN = (36, 150, 128)


def belly_x(belly, y, top):
    """Where his belly ends: a gentle curve between the collar and the hem."""
    import math
    (x0, y0), (x1, y1) = belly
    base = x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    t = max(0.0, min(1.0, (y - top) / (232 - top)))
    return base - 2 + 4 * math.sin(math.pi * t) - (6 * (t - 0.85) / 0.15 if t > 0.85 else 0)


def stripe_rows(sp, left_edge, top, bottom):
    """Blue or green for every row: the shirt's own bands, measured on the
    upper chest just left of the book, then carried on down at the same width."""
    x = left_edge[top] - 4
    seen = []
    for y in range(top - 30, top + 6):
        r, g, b, a = sp[x, y]
        if a > 200 and max(r, g, b) > 70:
            seen.append((y, "b" if b > g + 10 else "g"))
    changes = [seen[i][0] for i in range(1, len(seen)) if seen[i][1] != seen[i - 1][1]]
    band = 11
    if len(changes) >= 2:
        gaps = [b - a for a, b in zip(changes, changes[1:]) if 6 <= b - a <= 18]
        if gaps:
            band = sorted(gaps)[len(gaps) // 2]
    last_y, last_kind = (changes[-1], seen[-1][1]) if changes else (top, "b")
    out = {}
    for y in range(top - 40, bottom + 40):
        n = (y - last_y) // band
        kind = last_kind if n % 2 == 0 else ("g" if last_kind == "b" else "b")
        out[y] = (kind, ((y - last_y) % band) / band)
    return out


def process(cell, spec):
    from PIL import ImageFilter
    src = cell.copy()
    px = cell.load()
    sp = src.load()
    w, h = cell.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(spec["book"], fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(7))      # take the book's outline too
    m = mask.load()
    hx0, hy0, hx1, hy1 = spec["hand"]
    top = min(y for _, y in spec["book"]) - 3
    bottom = max(y for _, y in spec["book"]) + 3
    left_edge = {}
    for y in range(top - 12, bottom + 1):
        xs = [x for x in range(w) if y >= top and m[x, y]]
        left_edge[y] = min(xs) if xs else min(x for x, _ in spec["book"])
    kinds = stripe_rows(sp, left_edge, top, bottom)
    for y in range(top, 256):
        edge = belly_x(spec["belly"], min(y, 232), top)
        if y > 228:
            # below the hem: keep the shorts, cut whatever of the fist sticks out
            blues = [x for x in range(int(edge) - 20, min(w, int(edge) + 16))
                     if sp[x, y][3] > 200 and sp[x, y][2] > sp[x, y][0] + 30]
            cut = (max(blues) + 3) if blues else edge + 3
            for x in range(int(cut), w):
                px[x, y] = (0, 0, 0, 0)
            continue
        for x in range(w):
            in_hand = hx0 <= x <= hx1 and hy0 <= y <= hy1 and skinish(sp[x, y])
            if in_hand:
                continue
            if x > edge + 3:
                px[x, y] = (0, 0, 0, 0)       # in front of his belly: book and far arm only
                continue
            if m[x, y] or x > edge - 3:
                # stripes tilt a little downwards towards his front
                k, along = kinds.get(int(y - 0.12 * (x - left_edge[y])), ("b", 0.5))
                r, g, b = BLUE if k == "b" else GREEN
                depth = max(0.0, (x - (edge - 28)) / 28)          # 0 inside, 1 at the belly
                shade = (1.08 - 0.16 * along                       # each band lit from above
                         - 0.32 * depth - 0.15 * max(0.0, (y - 205) / 25))
                new = (r * shade, g * shade, b * shade)
                # blend into the painted shirt over the first few pixels
                blend = min(1.0, (x - left_edge[y] + 1) / 5) if m[x, y] else 1.0
                o = sp[x, y]
                if o[3] < 200 or not m[x, y]:
                    blend = 1.0
                px[x, y] = tuple(min(255, int(n * blend + c * (1 - blend)))
                                 for n, c in zip(new, o[:3])) + (255,)
            if edge - 1 <= x <= edge + 3:
                px[x, y] = OUTLINE
    return cell


sheet = Image.open(SRC).convert("RGBA")
for col, spec in FRAMES.items():
    box = (col * CW, 0, (col + 1) * CW, CH)
    sheet.paste(process(sheet.crop(box), spec), box[:2])
sheet.save(DST)
