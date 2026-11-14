"""Drawing helpers shared by every scene: text, bars, panels, typed words."""
import random

import pygame

from pixelfont import PixelFont
from settings import WHITE, GRAY, TYPED_COL, DARK

_fonts = {}
_glyphs = {}


def font(size, mono=False):
    """The game's pixel font, at about `size` pixels.

    Pixel letters only look right at whole-number scales, so a requested size
    picks the nearest step: small text, headings, titles. Headings are bold.
    """
    key = (size, mono)
    if key not in _fonts:
        if size <= 30:
            scale = 2
        elif size <= 46:
            scale = 3
        elif size <= 66:
            scale = 4
        elif size <= 80:
            scale = 5
        else:
            scale = 7
        _fonts[key] = PixelFont(scale, mono, bold=scale >= 3 and not mono)
    return _fonts[key]


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


def panel(surface, rect, alpha=200, color=DARK, border=(80, 70, 100)):
    x, y, w, h = rect
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((*color, alpha))
    surface.blit(s, (x, y))
    pygame.draw.rect(surface, border, rect, 1)


def glyph(ch, color, size):
    key = (ch, color, size)
    if key not in _glyphs:
        _glyphs[key] = font(size, mono=True).outlined(ch, color)
    return _glyphs[key]


def draw_incantation(surface, text, typed, pos, size=20, jitter=0.0,
                     color=WHITE, typed_color=TYPED_COL, rng=random):
    """Draw a word one letter at a time.

    Letters already typed are highlighted. At low sanity the letters jitter,
    but the letters themselves never change while you type them.
    Spaces are drawn as a small dot so the player can see them.
    """
    x, y = pos
    fnt = font(size, mono=True)
    advance = fnt.size("m")[0]
    for i, ch in enumerate(text):
        col = typed_color if i < typed else color
        shown = "·" if ch == " " else ch
        if ch == " " and i >= typed:
            col = GRAY
        dx = dy = 0
        if jitter > 0 and i >= typed:
            dx = rng.uniform(-jitter, jitter)
            dy = rng.uniform(-jitter, jitter)
        # the outlined letter is fnt.edge pixels bigger on every side
        surface.blit(glyph(shown, col, size),
                     (x + i * advance + dx - fnt.edge, y + dy - fnt.edge))
        if i == typed:
            pygame.draw.line(surface, typed_color,
                             (x + i * advance, y + fnt.height + 1),
                             (x + (i + 1) * advance - 2, y + fnt.height + 1), 2)
    return advance * len(text)


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
