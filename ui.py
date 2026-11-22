"""Drawing helpers shared by every scene: text, bars, panels, typed words."""
import os
import random

import pygame

from pixelfont import PixelFont
from settings import WHITE, GRAY, TYPED_COL, DARK

_fonts = {}
_glyphs = {}


def font(size):
    """The game's medieval pixel font, at about `size` pixels.

    Pixel letters only look right at whole-number scales, so a requested size
    picks the nearest step: small text, headings, titles, the game's name.
    """
    if size not in _fonts:
        if size <= 24:
            scale = 1
        elif size <= 46:
            scale = 2
        elif size <= 80:
            scale = 3
        else:
            scale = 5
        _fonts[size] = PixelFont(scale)
    return _fonts[size]


def draw_text(surface, fnt, text, color, outline=True, **position):
    """Render text and place it with any rect keyword, e.g. center=(x, y).

    Light text gets a black outline so it reads over the busy forest.
    Pass outline=False for dark ink on a light page.
    """
    rect = fnt.render(text, True, color).get_rect(**position)
    if outline and sum(color[:3]) > 300:
        surface.blit(fnt.outlined(text, color), rect.move(-fnt.edge, -fnt.edge))
    else:
        surface.blit(fnt.render(text, True, color), rect)
    return rect


def draw_bar(surface, rect, fraction, color, back=(30, 26, 36), border=GRAY):
    x, y, w, h = rect
    pygame.draw.rect(surface, back, rect)
    fraction = max(0.0, min(1.0, fraction))
    if fraction > 0:
        pygame.draw.rect(surface, color, (x, y, int(w * fraction), h))
    pygame.draw.rect(surface, border, rect, 1)


# --- The vined stone frame around every box ------------------------------------------
# assets/Sprites/UI/vine_frame.png is the painted frame with its inside made
# see-through (tools/make_vine_frame.py). It is cut into 9 pieces: the 4
# corners (where the vines are) keep their shape, the edges repeat, and the
# inside is filled in code so a box can be any size and any opacity.
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "Sprites")
FRAME_FILES = [os.path.join(_ASSETS, "UI", "vine_frame.png"),
               os.path.join(_ASSETS, "Blank Vined Pixel-Art HUD Frame.png")]
FRAME_SLICE = (215, 215, 140, 132)    # left, right, top, bottom: the corner sizes in the file
FRAME_INSET = (50, 50, 40, 38)        # where the inside starts under the stones
FRAME_FILL = (23, 6, 25)              # the painted inside's colour
FRAME_SCALE = (0.15, 0.24)            # smallest and largest the frame is drawn
_frame = {}


def _frame_image():
    """The painted frame, trimmed, or None if it can't be found."""
    if "image" not in _frame:
        image = None
        for path in FRAME_FILES:
            try:
                image = pygame.image.load(path).convert_alpha()
            except (pygame.error, FileNotFoundError):
                continue
            box = image.get_bounding_rect(min_alpha=20)     # the file has faint noise
            image = image.subsurface(box).copy()
            break
        _frame["image"] = image
    return _frame["image"]


def frame_scale(w, h):
    """How big the frame is drawn for a box: bigger boxes get thicker stones."""
    left, right, top, bottom = FRAME_SLICE
    low, high = FRAME_SCALE
    return min(high, max(low, h / 800), h / (top + bottom), w / (left + right))


def _frame_surface(w, h, k):
    """The frame alone (no inside) for a w x h box, drawn at scale k. Cached."""
    key = (w, h, round(k, 3))
    if key in _frame:
        return _frame[key]
    if len(_frame) > 300:                         # many sizes: start the cache over
        image = _frame["image"]
        _frame.clear()
        _frame["image"] = image
    image = _frame_image()
    scaled_key = ("scaled", round(k, 3))
    if scaled_key not in _frame:
        _frame[scaled_key] = pygame.transform.smoothscale(
            image, (max(1, round(image.get_width() * k)), max(1, round(image.get_height() * k))))
    src = _frame[scaled_key]
    sw, sh = src.get_size()
    left, right, top, bottom = (max(1, round(v * k)) for v in FRAME_SLICE)
    # a box smaller than the corners: shrink the corners to fit
    left, right = min(left, w // 2), min(right, w - w // 2)
    top, bottom = min(top, h // 2), min(bottom, h - h // 2)
    out = pygame.Surface((w, h), pygame.SRCALPHA)

    def piece(sx, sy, pw, ph, dx, dy):
        if pw > 0 and ph > 0:
            out.blit(src, (dx, dy), (sx, sy, pw, ph))

    piece(0, 0, left, top, 0, 0)
    piece(sw - right, 0, right, top, w - right, 0)
    piece(0, sh - bottom, left, bottom, 0, h - bottom)
    piece(sw - right, sh - bottom, right, bottom, w - right, h - bottom)
    # the edges: the stones between the corners, repeated as often as needed
    span = max(1, sw - round(FRAME_SLICE[0] * k) - round(FRAME_SLICE[1] * k))
    sx0 = round(FRAME_SLICE[0] * k)
    x = left
    while x < w - right:
        n = min(span, w - right - x)
        piece(sx0, 0, n, top, x, 0)
        piece(sx0, sh - bottom, n, bottom, x, h - bottom)
        x += n
    span = max(1, sh - round(FRAME_SLICE[2] * k) - round(FRAME_SLICE[3] * k))
    sy0 = round(FRAME_SLICE[2] * k)
    y = top
    while y < h - bottom:
        n = min(span, h - bottom - y)
        piece(0, sy0, left, n, 0, y)
        piece(sw - right, sy0, right, n, w - right, y)
        y += n
    _frame[key] = out
    return out


def panel(surface, rect, alpha=200, color=None, border=None, scale=None, border_width=1):
    """A box for text and menus: the vined stone frame, its inside `alpha` opaque.

    border: a colour to light the inside edge with (a chosen row, a warning).
    scale: draw the frame at this size instead of choosing one from the box's size.
    Falls back to a plain box if the frame picture is missing.
    """
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    if _frame_image() is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((*(color or DARK), alpha))
        surface.blit(s, (x, y))
        pygame.draw.rect(surface, border or (80, 70, 100), rect, border_width)
        return
    k = scale or frame_scale(w, h)
    il, ir, it, ib = (round(v * k) for v in FRAME_INSET)
    inside = pygame.Rect(x + il, y + it, w - il - ir, h - it - ib)
    if inside.width > 0 and inside.height > 0:
        s = pygame.Surface(inside.size, pygame.SRCALPHA)
        s.fill((*(color or FRAME_FILL), alpha))
        surface.blit(s, inside)
    surface.blit(_frame_surface(w, h, k), (x, y))
    if border:
        pygame.draw.rect(surface, border, inside.inflate(-2, -2), border_width)


def glyph(ch, color, size):
    key = (ch, color, size)
    if key not in _glyphs:
        _glyphs[key] = font(size).outlined(ch, color)
    return _glyphs[key]


def draw_incantation(surface, text, typed, pos, size=20, jitter=0.0,
                     color=WHITE, typed_color=TYPED_COL, rng=random, max_width=None):
    """Draw a word one letter at a time. Returns its width.

    Letters already typed are highlighted. At low sanity the letters jitter,
    but the letters themselves never change while you type them.
    Spaces are drawn as a small dot so the player can see them.
    If the word is wider than max_width its letters are set closer together.
    """
    x, y = pos
    fnt = font(size)
    shown = text.replace(" ", "\u00b7")
    gap = 1
    if max_width and fnt.size(shown)[0] > max_width:
        gap = 0
    for i, ch in enumerate(shown):
        col = typed_color if i < typed else color
        if text[i] == " " and i >= typed:
            col = GRAY
        dx = dy = 0
        if jitter > 0 and i >= typed:
            dx = rng.uniform(-jitter, jitter)
            dy = rng.uniform(-jitter, jitter)
        step = fnt.advance(ch, gap)
        if text[i] == " ":
            step += 2 * fnt.scale      # a little air around the dot between words
            dx += fnt.scale
        # the outlined letter is fnt.edge pixels bigger on every side
        surface.blit(glyph(ch, col, size), (x + dx - fnt.edge, y + dy - fnt.edge))
        if i == typed:
            # a bar under the next letter to type
            pygame.draw.rect(surface, typed_color,
                             (x, y + 12 * fnt.scale, max(3, step - fnt.scale), fnt.scale + 1))
        x += step
    return x - pos[0]


def incantation_width(text, size):
    fnt = font(size)
    shown = text.replace(" ", "\u00b7")
    return fnt.size(shown)[0] + 2 * fnt.scale * text.count(" ")


def wrap(text, fnt, width):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if fnt.size(test)[0] <= width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def fit(text, fnt, width):
    """Shorten text with an ellipsis until it fits in width pixels."""
    if fnt.size(text)[0] <= width:
        return text
    while text and fnt.size(text + "...")[0] > width:
        text = text[:-1]
    return text + "..."


# --- The stone tablet frame, for the words carved on the lore stones ------------------
# assets/Sprites/Blank Ancient Violet Stone Tablet-1.png, cut into 9 pieces like the
# vine frame, but its inside is painted (so it is stretched, not filled), and the
# teal gem on the top edge and the moss under the bottom edge stay whole in the
# middle while the plain stone either side of them repeats.
STONE_FILE = os.path.join(_ASSETS, "Blank Ancient Violet Stone Tablet-1.png")
STONE_SLICE = (260, 260, 340, 340)    # left, right, top, bottom corner sizes (trimmed file)
STONE_ORNAMENT = (590, 830)           # the columns holding the gem and the moss
_stone = {}


def _stone_image():
    if "image" not in _stone:
        try:
            image = pygame.image.load(STONE_FILE).convert_alpha()
            image = image.subsurface(image.get_bounding_rect(min_alpha=20)).copy()
        except (pygame.error, FileNotFoundError):
            image = None
        _stone["image"] = image
    return _stone["image"]


def _stone_surface(w, h, k):
    key = (w, h, round(k, 3))
    if key in _stone:
        return _stone[key]
    image = _stone_image()
    scaled_key = ("scaled", round(k, 3))
    if scaled_key not in _stone:
        _stone[scaled_key] = pygame.transform.smoothscale(
            image, (max(1, round(image.get_width() * k)), max(1, round(image.get_height() * k))))
    src = _stone[scaled_key]
    sw, sh = src.get_size()
    sl, sr, st, sb = (max(1, round(v * k)) for v in STONE_SLICE)
    left, right = min(sl, w // 2), min(sr, w - w // 2)
    top, bottom = min(st, h // 2), min(sb, h - h // 2)
    out = pygame.Surface((w, h), pygame.SRCALPHA)

    def piece(sx, sy, pw, ph, dx, dy):
        if pw > 0 and ph > 0:
            out.blit(src, (dx, dy), (sx, sy, pw, ph))

    # the painted inside, stretched to fit
    cw, ch = sw - sl - sr, sh - st - sb
    if cw > 0 and ch > 0 and w - left - right > 0 and h - top - bottom > 0:
        inside = pygame.transform.smoothscale(src.subsurface((sl, st, cw, ch)),
                                              (w - left - right, h - top - bottom))
        out.blit(inside, (left, top))
    # the sides: plain stone, repeated
    y = top
    while y < h - bottom and ch > 0:
        n = min(ch, h - bottom - y)
        piece(0, st, left, n, 0, y)
        piece(sw - sr + (sr - right), st, right, n, w - right, y)
        y += n
    # the top and bottom: the gem / moss in the middle, plain stone either side
    o0, o1 = round(STONE_ORNAMENT[0] * k), round(STONE_ORNAMENT[1] * k)
    ow = o1 - o0
    if w - left - right >= ow:
        # where the gem sits along the edge, kept in proportion (exactly where it
        # was painted when the box is the tablet's own width)
        free, src_free = w - left - right - ow, max(1, sw - sl - sr - ow)
        ox = left + round((o0 - sl) * free / src_free)
        spans = [(left, ox, sl, o0), (ox + ow, w - right, o1, sw - sr)]
        piece(o0, 0, ow, top, ox, 0)
        piece(o0, sh - bottom, ow, bottom, ox, h - bottom)
    else:
        spans = [(left, w - right, sl, sw - sr)]
    for x0, x1, s0, s1 in spans:
        x = x0
        while x < x1 and s1 > s0:
            n = min(s1 - s0, x1 - x)
            piece(s0, 0, n, top, x, 0)
            piece(s0, sh - bottom, n, bottom, x, h - bottom)
            x += n
    # the corners, last, so the vines lie over everything
    piece(0, 0, left, top, 0, 0)
    piece(sw - right, 0, right, top, w - right, 0)
    piece(0, sh - bottom, left, bottom, 0, h - bottom)
    piece(sw - right, sh - bottom, right, bottom, w - right, h - bottom)
    if len(_stone) > 60:
        _stone.clear()
        _stone["image"] = image
    _stone[key] = out
    return out


def stone_panel(surface, rect):
    """A stone tablet behind carved words (the lore stones). Plain box if it's missing.

    The tablet is scaled to the box's width, so its top and bottom edges are
    drawn whole, as painted; only its height is fitted (the plain stone of the
    sides is repeated, or the middle of them left out).
    """
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    image = _stone_image()
    if image is None:
        panel(surface, rect, 235)
        return
    surface.blit(_stone_surface(w, h, w / image.get_width()), (x, y))
