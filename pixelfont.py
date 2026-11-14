"""A pixel font drawn in code.

The game's art is pixel art, so its text is too. Every letter is a small grid
of dots, listed below, and is drawn as squares `scale` pixels wide. No font
file is needed, so the text looks the same on every computer.

PixelFont has the same two methods the game uses on a pygame Font,
render() and size(), so it can stand in for one anywhere.
"""
import pygame

ROWS = 9            # 7 rows for the letter body + 2 below the line (g, j, p, q, y)
MONO_ADVANCE = 6    # fixed-width cell: 5 columns + 1 gap
SPACE_WIDTH = 3

# Capitals, digits and punctuation: the classic 5 x 7 dot-matrix letters.
# Each letter is 5 COLUMNS; in a column, bit 0 is the top dot.
COLUMNS = {
    "!": (0x00, 0x00, 0x5F, 0x00, 0x00), '"': (0x00, 0x07, 0x00, 0x07, 0x00),
    "#": (0x14, 0x7F, 0x14, 0x7F, 0x14), "$": (0x24, 0x2A, 0x7F, 0x2A, 0x12),
    "%": (0x23, 0x13, 0x08, 0x64, 0x62), "&": (0x36, 0x49, 0x55, 0x22, 0x50),
    "'": (0x00, 0x00, 0x03, 0x00, 0x00), "(": (0x00, 0x1C, 0x22, 0x41, 0x00),
    ")": (0x00, 0x41, 0x22, 0x1C, 0x00), "*": (0x14, 0x08, 0x3E, 0x08, 0x14),
    "+": (0x08, 0x08, 0x3E, 0x08, 0x08), ",": (0x00, 0x00, 0xC0, 0x00, 0x00),
    "-": (0x00, 0x08, 0x08, 0x08, 0x00), ".": (0x00, 0x00, 0x40, 0x00, 0x00),
    "/": (0x20, 0x10, 0x08, 0x04, 0x02),
    "0": (0x3E, 0x51, 0x49, 0x45, 0x3E), "1": (0x00, 0x42, 0x7F, 0x40, 0x00),
    "2": (0x42, 0x61, 0x51, 0x49, 0x46), "3": (0x21, 0x41, 0x45, 0x4B, 0x31),
    "4": (0x18, 0x14, 0x12, 0x7F, 0x10), "5": (0x27, 0x45, 0x45, 0x45, 0x39),
    "6": (0x3C, 0x4A, 0x49, 0x49, 0x30), "7": (0x01, 0x71, 0x09, 0x05, 0x03),
    "8": (0x36, 0x49, 0x49, 0x49, 0x36), "9": (0x06, 0x49, 0x49, 0x29, 0x1E),
    ":": (0x00, 0x00, 0x24, 0x00, 0x00), ";": (0x00, 0x00, 0xA4, 0x00, 0x00),
    "<": (0x08, 0x14, 0x22, 0x41, 0x00), "=": (0x14, 0x14, 0x14, 0x14, 0x00),
    ">": (0x00, 0x41, 0x22, 0x14, 0x08), "?": (0x02, 0x01, 0x51, 0x09, 0x06),
    "@": (0x32, 0x49, 0x79, 0x41, 0x3E),
    "A": (0x7E, 0x11, 0x11, 0x11, 0x7E), "B": (0x7F, 0x49, 0x49, 0x49, 0x36),
    "C": (0x3E, 0x41, 0x41, 0x41, 0x22), "D": (0x7F, 0x41, 0x41, 0x22, 0x1C),
    "E": (0x7F, 0x49, 0x49, 0x49, 0x41), "F": (0x7F, 0x09, 0x09, 0x09, 0x01),
    "G": (0x3E, 0x41, 0x49, 0x49, 0x7A), "H": (0x7F, 0x08, 0x08, 0x08, 0x7F),
    "I": (0x00, 0x41, 0x7F, 0x41, 0x00), "J": (0x20, 0x40, 0x41, 0x3F, 0x01),
    "K": (0x7F, 0x08, 0x14, 0x22, 0x41), "L": (0x7F, 0x40, 0x40, 0x40, 0x40),
    "M": (0x7F, 0x02, 0x0C, 0x02, 0x7F), "N": (0x7F, 0x04, 0x08, 0x10, 0x7F),
    "O": (0x3E, 0x41, 0x41, 0x41, 0x3E), "P": (0x7F, 0x09, 0x09, 0x09, 0x06),
    "Q": (0x3E, 0x41, 0x51, 0x21, 0x5E), "R": (0x7F, 0x09, 0x19, 0x29, 0x46),
    "S": (0x46, 0x49, 0x49, 0x49, 0x31), "T": (0x01, 0x01, 0x7F, 0x01, 0x01),
    "U": (0x3F, 0x40, 0x40, 0x40, 0x3F), "V": (0x1F, 0x20, 0x40, 0x20, 0x1F),
    "W": (0x3F, 0x40, 0x38, 0x40, 0x3F), "X": (0x63, 0x14, 0x08, 0x14, 0x63),
    "Y": (0x07, 0x08, 0x70, 0x08, 0x07), "Z": (0x61, 0x51, 0x49, 0x45, 0x43),
    "[": (0x00, 0x7F, 0x41, 0x41, 0x00), "\\": (0x02, 0x04, 0x08, 0x10, 0x20),
    "]": (0x00, 0x41, 0x41, 0x7F, 0x00), "^": (0x04, 0x02, 0x01, 0x02, 0x04),
    "_": (0x40, 0x40, 0x40, 0x40, 0x40), "`": (0x00, 0x01, 0x02, 0x00, 0x00),
    "{": (0x00, 0x08, 0x36, 0x41, 0x00), "|": (0x00, 0x00, 0x7F, 0x00, 0x00),
    "}": (0x00, 0x41, 0x36, 0x08, 0x00), "~": (0x08, 0x04, 0x08, 0x10, 0x08),
    "·": (0x00, 0x00, 0x08, 0x00, 0x00),    # middle dot: shows a space to type
}

# Lower-case letters, drawn narrower so long lines of text still fit.
# X is a dot. The rows run top to bottom; a letter may hang 2 rows below.
LOWER = {
    "a": ["....", "....", ".XX.", "...X", ".XXX", "X..X", ".XXX"],
    "b": ["X...", "X...", "XXX.", "X..X", "X..X", "X..X", "XXX."],
    "c": ["....", "....", ".XXX", "X...", "X...", "X...", ".XXX"],
    "d": ["...X", "...X", ".XXX", "X..X", "X..X", "X..X", ".XXX"],
    "e": ["....", "....", ".XX.", "X..X", "XXXX", "X...", ".XXX"],
    "f": [".XX", "X..", "XXX", "X..", "X..", "X..", "X.."],
    "g": ["....", "....", ".XXX", "X..X", "X..X", "X..X", ".XXX", "...X", ".XX."],
    "h": ["X...", "X...", "XXX.", "X..X", "X..X", "X..X", "X..X"],
    "i": ["X", ".", "X", "X", "X", "X", "X"],
    "j": [".X", "..", ".X", ".X", ".X", ".X", ".X", ".X", "X."],
    "k": ["X...", "X...", "X..X", "X.X.", "XX..", "X.X.", "X..X"],
    "l": ["X.", "X.", "X.", "X.", "X.", "X.", ".X"],
    "m": [".....", ".....", "XX.X.", "X.X.X", "X.X.X", "X.X.X", "X.X.X"],
    "n": ["....", "....", "XXX.", "X..X", "X..X", "X..X", "X..X"],
    "o": ["....", "....", ".XX.", "X..X", "X..X", "X..X", ".XX."],
    "p": ["....", "....", "XXX.", "X..X", "X..X", "X..X", "XXX.", "X...", "X..."],
    "q": ["....", "....", ".XXX", "X..X", "X..X", "X..X", ".XXX", "...X", "...X"],
    "r": ["....", "....", "X.XX", "XX..", "X...", "X...", "X..."],
    "s": ["....", "....", ".XXX", "X...", ".XX.", "...X", "XXX."],
    "t": [".X.", ".X.", "XXX", ".X.", ".X.", ".X.", "..X"],
    "u": ["....", "....", "X..X", "X..X", "X..X", "X..X", ".XXX"],
    "v": [".....", ".....", "X...X", "X...X", ".X.X.", ".X.X.", "..X.."],
    "w": [".....", ".....", "X...X", "X.X.X", "X.X.X", "X.X.X", ".X.X."],
    "x": [".....", ".....", "X...X", ".X.X.", "..X..", ".X.X.", "X...X"],
    "y": ["....", "....", "X..X", "X..X", "X..X", "X..X", ".XXX", "...X", ".XX."],
    "z": ["....", "....", "XXXX", "...X", ".XX.", "X...", "XXXX"],
}


def _build_glyphs():
    """Turn both tables into one: letter -> list of ROWS strings, trimmed to its width."""
    glyphs = {}
    for ch, columns in COLUMNS.items():
        rows = ["".join("X" if (col >> y) & 1 else "." for col in columns)
                for y in range(ROWS)]
        # trim the empty columns on both sides
        used = [x for x in range(5) if any(row[x] == "X" for row in rows)]
        glyphs[ch] = [row[used[0]:used[-1] + 1] for row in rows]
    for ch, rows in LOWER.items():
        width = len(rows[0])
        glyphs[ch] = rows + ["." * width] * (ROWS - len(rows))
    glyphs[" "] = ["." * SPACE_WIDTH] * ROWS
    return glyphs


GLYPHS = _build_glyphs()


class PixelFont:
    """Draws text with the dot letters above, each dot `scale` pixels wide.

    mono=True gives every letter the same width, used for incantations so a
    word keeps its length while you type it.
    bold=True makes every dot half as wide again, for headings.
    """

    def __init__(self, scale, mono=False, bold=False):
        self.scale = scale
        self.mono = mono
        self.bold = bold
        self.height = ROWS * scale
        self.extra = scale // 2 if bold else 0    # extra pixels of width per dot
        self._letters = {}     # (letter, colour) -> Surface
        self._texts = {}       # (text, colour) -> Surface
        self._outlined = {}    # (text, colour) -> Surface with a black edge
        # the outline is about half a dot thick, so it frames the letters without drowning them
        self.edge = max(1, round(scale / 2))

    def advance(self, ch):
        """How far the next letter starts after this one, in dots."""
        if self.mono:
            return MONO_ADVANCE
        return len(GLYPHS.get(ch, GLYPHS["?"])[0]) + 1

    def size(self, text):
        return (max(1, sum(self.advance(ch) for ch in text) * self.scale + self.extra),
                self.height)

    def letter(self, ch, color):
        key = (ch, color)
        if key not in self._letters:
            rows = GLYPHS.get(ch, GLYPHS["?"])
            s = self.scale
            surf = pygame.Surface((len(rows[0]) * s + self.extra, self.height), pygame.SRCALPHA)
            for y, row in enumerate(rows):
                for x, dot in enumerate(row):
                    if dot == "X":
                        surf.fill(color, (x * s, y * s, s + self.extra, s))
            self._letters[key] = surf
        return self._letters[key]

    def render(self, text, antialias, color, background=None):
        """Same arguments as pygame.font.Font.render (antialias is not needed)."""
        color = tuple(color[:3])
        key = (text, color)
        if key not in self._texts:
            if len(self._texts) > 1500:      # damage numbers etc. would pile up forever
                self._texts.clear()
            surf = pygame.Surface(self.size(text), pygame.SRCALPHA)
            x = 0
            for ch in text:
                image = self.letter(ch, color)
                pad = 0
                if self.mono:                # centre the letter in its cell
                    pad = (MONO_ADVANCE - 1 - image.get_width() // self.scale) // 2
                surf.blit(image, ((x + pad) * self.scale, 0))
                x += self.advance(ch)
            self._texts[key] = surf
        # a copy, because callers fade their text with set_alpha
        return self._texts[key].copy()

    def outlined(self, text, color, edge_color=(0, 0, 0)):
        """The text with a black outline. The picture is `edge` pixels bigger on every side."""
        color = tuple(color[:3])
        key = (text, color)
        if key not in self._outlined:
            if len(self._outlined) > 1500:
                self._outlined.clear()
            e = self.edge
            dark = self.render(text, True, edge_color)
            surf = pygame.Surface((dark.get_width() + 2 * e, dark.get_height() + 2 * e),
                                  pygame.SRCALPHA)
            # the black copy, stamped once in each of the 8 directions ...
            for dx in (0, e, 2 * e):
                for dy in (0, e, 2 * e):
                    if (dx, dy) != (e, e):
                        surf.blit(dark, (dx, dy))
            # ... then the real letters on top, in the middle
            surf.blit(self.render(text, True, color), (e, e))
            self._outlined[key] = surf
        return self._outlined[key].copy()
