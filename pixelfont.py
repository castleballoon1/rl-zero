"""A medieval (blackletter-style) pixel font drawn in code.

The game's art is pixel art, so its text is too. Every letter is a small grid
of dots, listed below, and is drawn as squares `scale` pixels wide. No font
file is needed, so the text looks the same on every computer.

The letters follow the look of medieval blackletter: upright stems two dots
thick, a small flag at the top-left of a stem and a foot at the bottom-right,
angular bowls, and a thin inner line in round capitals (C, E, G, O, Q).
They are kept plainer than real blackletter so that single letters are easy
to tell apart: this is a typing game.

PixelFont has the same two methods the game uses on a pygame Font,
render() and size(), so it can stand in for one anywhere.
"""
import pygame

ROWS = 14           # row 0 spare, rows 1-10 capitals/ascenders, 4-10 small letters, 11-13 tails
SPACE_WIDTH = 4

# letter -> (first row, rows separated by "|").  X is a dot.
SHAPES = {
    # ---- small letters ---------------------------------------------------
    "a": (4, ".XXXX.|X...XX|....XX|.XXXXX|XX..XX|XX..XX|.XXXXXX"),
    "b": (1, "XXX|.XX|.XX|.XX.XX.|.XXXXXX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|.XXXXX."),
    "c": (4, "..XXXX|.XX..X|XX....|XX....|XX....|XX...X|.XXXX."),
    "d": (1, "...XXX|....XX|....XX|.XXXXX|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|.XXXXXX"),
    "e": (4, "..XXXX.|.XX..XX|XX...XX|XXXXXX.|XX.....|XX....X|.XXXXX."),
    "f": (1, "..XXX|.XX..|.XX..|XXXXX|.XX..|.XX..|.XX..|.XX..|.XX..|XXXX."),
    "g": (4, ".XXXXX|XX..XX|XX..XX|XX..XX|XX..XX|.XXXXX|....XX|....XX|X...XX|.XXXX."),
    "h": (1, "XXX|.XX|.XX|.XX.XX.|.XXXXXX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|.....XX|....XX."),
    "i": (2, ".XX|...|XXX|.XX|.XX|.XX|.XX|.XX|.XXX"),
    "j": (2, ".XX|...|XXX|.XX|.XX|.XX|.XX|.XX|.XX|.XX|.XX|XX."),
    "k": (1, "XXX|.XX|.XX|.XX..XX|.XX.XX.|.XXXX..|.XXXX..|.XX.XX.|.XX..XX|.XX..XXX"),
    "l": (1, "XXX|.XX|.XX|.XX|.XX|.XX|.XX|.XX|.XX|.XXX"),
    "m": (4, "XXX.XX..XX.|.XXXXXXXXXX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XXX"),
    "n": (4, "XXX.XX.|.XXXXXX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|.XX..XXX"),
    "o": (4, "..XXXX.|.XX..XX|XX...XX|XX...XX|XX...XX|XX..XX.|.XXXX.."),
    "p": (4, "XXX.XX.|.XXXXXX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|.XXXXX.|.XX|.XX|XXXX"),
    "q": (4, ".XXXXX|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|.XXXXX|....XX|....XX|...XXXX"),
    "r": (4, "XXX.XX|.XXXXX|.XX..X|.XX|.XX|.XX|XXXX"),
    "s": (4, ".XXXXX|XX...X|XX....|.XXXX.|....XX|X...XX|XXXXX."),
    "t": (2, ".XX|.XX|XXXXX|.XX|.XX|.XX|.XX|.XX..X|..XXX."),
    "u": (4, "XXX.XXX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|..XXXXXX"),
    "v": (4, "XXX..XX|.XX..XX|.XX..XX|.XX..XX|.XX.XX.|.XXXX..|..XX..."),
    "w": (4, "XXX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX.XX.|.XXXXXXXX..|..XX..XX..."),
    "x": (4, "XX...XX|.XX.XX.|..XXX..|..XXX..|..XXX..|.XX.XX.|XX...XX"),
    "y": (4, "XXX.XXX|.XX..XX|.XX..XX|.XX..XX|.XX..XX|..XXXXX|.....XX|.....XX|X...XX.|.XXXX.."),
    "z": (4, "XXXXXX|X...XX|...XX.|.XXXX.|.XX...|XX...X|XXXXXX"),
    # ---- capitals ----------------------------------------------------------
    "A": (1, "...XXXXX|..XX..XX|.XX...XX|.XX...XX|XX.X..XX|XX.X..XX|XXXXXXXX|XX.X..XX|XX.X..XX|XXX..XXXX"),
    "B": (1, "XXXXXXXX|X.XX..XXX|X.XX...XX|X.XX..XX|X.XXXXX|X.XX..XX|X.XX...XX|X.XX...XX|X.XX..XXX|XXXXXXXX"),
    "C": (1, "..XXXXX|.XX...XX|XX.X|XX.X|XX.X|XX.X|XX.X|XX.X...X|.XX...XX|..XXXXX"),
    "D": (1, "XXXXXXX|X.XX..XX|X.XX...XX|X.XX...XX|X.XX...XX|X.XX...XX|X.XX...XX|X.XX...XX|X.XX..XX|XXXXXXX"),
    "E": (1, "..XXXXXX|.XX....X|XX.X|XX.X|XX.XXXX|XX.X|XX.X|XX.X...X|.XX...XX|..XXXXX"),
    "F": (1, "XXXXXXXXX|X.XX....X|X.XX|X.XX|X.XXXXX|X.XX|X.XX|X.XX|X.XX|XXXXX"),
    "G": (1, "..XXXXX|.XX...XX|XX.X|XX.X|XX.X|XX.X.XXX|XX.X..XX|XX.X..XX|.XX...XX|..XXXXX"),
    "H": (1, "XXXX..XXX|X.XX..XX|X.XX..XX|X.XX..XX|X.XXXXXX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|XXXX..XXX"),
    "I": (1, "XXXXXX|..XX|..XX|..XX|..XX|..XX|..XX|..XX|..XX|XXXXXX"),
    "J": (1, "..XXXXXX|....XX|....XX|....XX|....XX|....XX|....XX|XX..XX|XX..XX|.XXXX"),
    "K": (1, "XXXX.XXX|X.XX.XX|X.XXXX|X.XXX|X.XXX|X.XXXX|X.XX.XX|X.XX..XX|X.XX..XX|XXXX..XXX"),
    "L": (1, "XXXX|X.XX|X.XX|X.XX|X.XX|X.XX|X.XX|X.XX|X.XX....X|XXXXXXXXX"),
    "M": (1, "XXXXX.XXXX|.XX.XXX.XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|.XX..XX..XX|XXX..XX..XXX"),
    "N": (1, "XXXX..XXX|X.XXX.XX|X.XXXXXX|X.XX.XXX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|XXXX..XXX"),
    "O": (1, "..XXXX|.XX..XX|XX.X..XX|XX.X..XX|XX.X..XX|XX.X..XX|XX.X..XX|XX.X..XX|.XX..XX|..XXXX"),
    "P": (1, "XXXXXXXX|X.XX...XX|X.XX...XX|X.XX...XX|X.XX..XX|X.XXXXX|X.XX|X.XX|X.XX|XXXXX"),
    "Q": (1, "..XXXX|.XX..XX|XX.X..XX|XX.X..XX|XX.X..XX|XX.X..XX|XX.X..XX|XX.X.XXX|.XX.XXX|..XXX.XX"),
    "R": (1, "XXXXXXXX|X.XX...XX|X.XX...XX|X.XX..XX|X.XXXXX|X.XX.XX|X.XX..XX|X.XX..XX|X.XX...XX|XXXXX..XXX"),
    "S": (1, ".XXXXXX|XX....XX|XX|XXX|.XXXXX|...XXXX|......XX|......XX|XX....XX|.XXXXXX"),
    "T": (1, "XXXXXXXXX|X...XX..X|...XX|..XX.X|..XX.X|..XX.X|..XX.X|..XX.X..X|...XX..XX|....XXXX"),
    "U": (1, "XXXX..XXX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|.XXXXXXXX"),
    "V": (1, "XXXX..XXX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX..XX|X.XX.XX|X.XXXX|.XXXX|..XX"),
    "W": (1, "XXX.....XXX|.XX.....XX|.XX.....XX|.XX..X..XX|.XX..X..XX|.XX.XXX.XX|.XX.XXX.XX|.XXXX.XXXX|..XX...XX|..XX...XX"),
    "X": (1, "XXX..XXX|.XX..XX|..XXXX|..XXXX|...XX|...XX|..XXXX|..XXXX|.XX..XX|XXX..XXX"),
    "Y": (1, "XXX..XXX|.XX..XX|.XX..XX|..XXXX|..XXXX|...XX|...XX|...XX|...XX|..XXXX"),
    "Z": (1, "XXXXXXXX|X....XXX|....XXX|...XXX|.XXXXXX|..XXX|.XXX|XXX....X|XXX...XX|XXXXXXXX"),
    # ---- digits ---------------------------------------------------------------
    "0": (1, ".XXXX.|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|.XXXX."),
    "1": (1, "..XX|.XXX|XXXX|..XX|..XX|..XX|..XX|..XX|..XX|XXXXXX"),
    "2": (1, ".XXXX.|XX..XX|....XX|....XX|...XX.|..XX..|.XX...|XX....|XX...X|XXXXXX"),
    "3": (1, ".XXXX.|XX..XX|....XX|....XX|..XXX.|....XX|....XX|....XX|XX..XX|.XXXX."),
    "4": (1, "...XXX|..XXXX|.XX.XX|XX..XX|XX..XX|XXXXXX|....XX|....XX|....XX|...XXXX"),
    "5": (1, "XXXXXX|XX....|XX....|XXXXX.|....XX|....XX|....XX|....XX|XX..XX|.XXXX."),
    "6": (1, "..XXX.|.XX...|XX....|XXXXX.|XX..XX|XX..XX|XX..XX|XX..XX|XX..XX|.XXXX."),
    "7": (1, "XXXXXX|X...XX|....XX|...XX.|...XX.|..XX..|..XX..|.XX...|.XX...|.XX..."),
    "8": (1, ".XXXX.|XX..XX|XX..XX|XX..XX|.XXXX.|XX..XX|XX..XX|XX..XX|XX..XX|.XXXX."),
    "9": (1, ".XXXX.|XX..XX|XX..XX|XX..XX|XX..XX|.XXXXX|....XX|....XX|...XX.|.XXX.."),
    # ---- punctuation -------------------------------------------------------------
    ".": (9, "XX|XX"),
    ",": (9, "XX|XX|.X|X."),
    ":": (5, "XX|XX|..|..|XX|XX"),
    ";": (5, "XX|XX|..|..|XX|XX|.X|X."),
    "!": (1, "XX|XX|XX|XX|XX|XX|XX|..|XX|XX"),
    "?": (1, ".XXXX.|XX..XX|....XX|...XX.|..XX..|..XX..|..XX..|......|..XX..|..XX.."),
    "'": (1, "XX|XX|X."),
    '"': (1, "XX.XX|XX.XX|X..X."),
    "-": (6, "XXXXX|XXXXX"),
    "+": (4, "..XX..|..XX..|XXXXXX|XXXXXX|..XX..|..XX.."),
    "=": (5, "XXXXXX|......|......|XXXXXX"),
    "/": (1, "....XX|....XX|...XX.|...XX.|..XX..|..XX..|.XX...|.XX...|XX....|XX...."),
    "\\": (1, "XX....|XX....|.XX...|.XX...|..XX..|..XX..|...XX.|...XX.|....XX|....XX"),
    "(": (1, "..XX|.XX.|XX..|XX..|XX..|XX..|XX..|XX..|.XX.|..XX"),
    ")": (1, "XX..|.XX.|..XX|..XX|..XX|..XX|..XX|..XX|.XX.|XX.."),
    "[": (1, "XXXX|XX..|XX..|XX..|XX..|XX..|XX..|XX..|XX..|XXXX"),
    "]": (1, "XXXX|..XX|..XX|..XX|..XX|..XX|..XX|..XX|..XX|XXXX"),
    "<": (3, "...XX|..XX.|.XX..|XX...|.XX..|..XX.|...XX"),
    ">": (3, "XX...|.XX..|..XX.|...XX|..XX.|.XX..|XX..."),
    "%": (1, "XX...XX|XX...XX|....XX.|....XX.|...XX..|..XX...|.XX....|.XX....|XX...XX|XX...XX"),
    "*": (3, "X.XX.X|.XXXX.|XXXXXX|.XXXX.|X.XX.X"),
    "#": (3, ".XX.XX.|XXXXXXX|.XX.XX.|.XX.XX.|.XX.XX.|XXXXXXX|.XX.XX."),
    "&": (1, "..XXX|.XX.XX|.XX.XX|..XXX|.XXX...X|XX.XX.XX|XX..XXX|XX...XX|XX..XXXX|.XXXX.XX"),
    "@": (3, ".XXXXX.|XX...XX|XX.XXXX|XX.X.XX|XX.XXXX|XX.....|.XXXXX."),
    "_": (11, "XXXXXX|XXXXXX"),
    "~": (6, ".XX..X|X..XX."),
    "|": (1, "XX|XX|XX|XX|XX|XX|XX|XX|XX|XX|XX"),
    "^": (1, "..XX..|.XXXX.|XX..XX"),
    "`": (1, "XX.|.XX"),
    "{": (1, "..XX|.XX.|.XX.|.XX.|XX..|XX..|.XX.|.XX.|.XX.|..XX"),
    "}": (1, "XX..|.XX.|.XX.|.XX.|..XX|..XX|.XX.|.XX.|.XX.|XX.."),
    "·": (7, "XX|XX"),          # middle dot: shows a space you have to type
}


def _build_glyphs():
    """letter -> list of ROWS strings, all the same width."""
    glyphs = {}
    for ch, (top, shape) in SHAPES.items():
        rows = shape.split("|")
        width = max(len(row) for row in rows)
        grid = ["." * width] * top + [row.ljust(width, ".") for row in rows]
        grid += ["." * width] * (ROWS - len(grid))
        glyphs[ch] = grid[:ROWS]
    glyphs[" "] = ["." * SPACE_WIDTH] * ROWS
    return glyphs


GLYPHS = _build_glyphs()


class PixelFont:
    """Draws text with the dot letters above, each dot `scale` pixels wide."""

    def __init__(self, scale):
        self.scale = scale
        self.height = ROWS * scale
        # the outline is about half a dot thick, so it frames the letters without drowning them
        self.edge = max(1, round(scale / 2))
        self._letters = {}     # (letter, colour) -> Surface
        self._texts = {}       # (text, colour) -> Surface
        self._outlined = {}    # (text, colour) -> Surface with a black edge

    def advance(self, ch, gap=1):
        """How far the next letter starts after this one, in pixels."""
        return (len(GLYPHS.get(ch, GLYPHS["?"])[0]) + gap) * self.scale

    def size(self, text):
        return (max(1, sum(self.advance(ch) for ch in text)), self.height)

    def letter(self, ch, color):
        key = (ch, color)
        if key not in self._letters:
            rows = GLYPHS.get(ch, GLYPHS["?"])
            s = self.scale
            surf = pygame.Surface((len(rows[0]) * s, self.height), pygame.SRCALPHA)
            for y, row in enumerate(rows):
                for x, dot in enumerate(row):
                    if dot == "X":
                        surf.fill(color, (x * s, y * s, s, s))
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
                surf.blit(self.letter(ch, color), (x, 0))
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
