"""Everything the game draws that is a picture.

The painted art in assets/ is loaded through the team's own helpers:
    scene.py    the forest parallax layers
    enemies.py  the creature sheets (idle / hurt / attack rows)
    sprites.py  cutting, cleaning, aligning by the feet, scaling
This file adds the creatures' death sheets, the child with his three sanity
looks, the pages, and small things that have no painted art yet (platforms,
thorns, shrines, the gate), which are drawn with shapes.

If a painted file is missing the game still runs: a drawn stand-in is used.
"""
import math
import os
import random

import pygame

import enemies as creature_table
import sprites
from bestiary import ACTS, DEATH_SHEETS, act_info
from settings import WIDTH, HEIGHT, GROUND_Y

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

_cache = {}


# --- Sprite sheet helpers ---------------------------------------------------
def build_sheet(draw_frame, count, w, h):
    """Draw `count` frames side by side on one sheet surface."""
    sheet = pygame.Surface((w * count, h), pygame.SRCALPHA)
    for i in range(count):
        frame = pygame.Surface((w, h), pygame.SRCALPHA)
        draw_frame(frame, i, count)
        sheet.blit(frame, (i * w, 0))
    return sheet


def slice_sheet(sheet, w, h):
    count = sheet.get_width() // w
    return [sheet.subsurface((i * w, 0, w, h)) for i in range(count)]


def frames(name, draw_frame, count, w, h):
    """Load assets/<name>.png if it exists, otherwise generate the sheet."""
    if name in _cache:
        return _cache[name]
    path = os.path.join(ASSET_DIR, name + ".png")
    sheet = None
    if os.path.exists(path):
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except pygame.error:
            sheet = None
    if sheet is None:
        sheet = build_sheet(draw_frame, count, w, h)
    result = slice_sheet(sheet, w, h)
    _cache[name] = result
    return result


def glow(radius, color, strength=120):
    """A soft round light made of stacked transparent circles."""
    key = ("glow", radius, color, strength)
    if key in _cache:
        return _cache[key]
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    steps = 12
    for i in range(steps):
        r = radius * (1 - i / steps)
        a = int(strength * (i + 1) / steps / 3)
        pygame.draw.circle(surf, (*color, a), (radius, radius), max(1, int(r)))
    _cache[key] = surf
    return surf


# --- The lost boy (12 frames, 32 x 48) ---------------------------------------
# 0-1 idle, 2-5 walk, 6 jump, 7 cast, 8-11 death
def _draw_player_death(surf, step):
    cloak = (40, 44, 62)
    skin = (226, 214, 196)
    if step == 0:      # drops to his knees
        pygame.draw.polygon(surf, cloak, [(16, 22), (6, 47), (26, 47)])
        pygame.draw.circle(surf, cloak, (16, 22), 9)
        pygame.draw.circle(surf, skin, (17, 24), 5)
        pygame.draw.rect(surf, (255, 200, 90), (25, 41, 5, 6))
    elif step == 1:    # slumps over
        pygame.draw.ellipse(surf, cloak, (3, 33, 24, 14))
        pygame.draw.circle(surf, cloak, (24, 37), 8)
        pygame.draw.circle(surf, skin, (25, 39), 4)
        pygame.draw.rect(surf, (200, 150, 70), (1, 42, 5, 5))
    elif step == 2:    # lies still, lantern dimming
        pygame.draw.ellipse(surf, (30, 33, 48), (3, 38, 26, 9))
        pygame.draw.circle(surf, (30, 33, 48), (26, 42), 5)
        pygame.draw.rect(surf, (130, 100, 60), (1, 42, 5, 5))
    else:              # only a heap of cloth and a dark lantern
        pygame.draw.ellipse(surf, (22, 24, 36), (5, 42, 22, 5))
        pygame.draw.rect(surf, (70, 60, 50), (1, 42, 5, 5))


def _draw_player(surf, i, n):
    if i >= 8:
        _draw_player_death(surf, i - 8)
        return
    cloak = (40, 44, 62)
    cloak_dark = (26, 28, 42)
    skin = (226, 214, 196)
    bob = 1 if i == 1 else 0
    # legs
    if 2 <= i <= 5:
        swing = [-4, 0, 4, 0][i - 2]
        pygame.draw.line(surf, cloak_dark, (14, 36), (14 + swing, 47), 4)
        pygame.draw.line(surf, cloak_dark, (19, 36), (19 - swing, 47), 4)
    elif i == 6:
        pygame.draw.line(surf, cloak_dark, (13, 36), (10, 44), 4)
        pygame.draw.line(surf, cloak_dark, (19, 36), (22, 43), 4)
    else:
        pygame.draw.line(surf, cloak_dark, (14, 36), (14, 47), 4)
        pygame.draw.line(surf, cloak_dark, (19, 36), (19, 47), 4)
    # cloak body
    pygame.draw.polygon(surf, cloak, [(16, 12 + bob), (6, 40), (26, 40)])
    # hood + face
    pygame.draw.circle(surf, cloak, (16, 12 + bob), 9)
    pygame.draw.circle(surf, skin, (17, 13 + bob), 5)
    pygame.draw.rect(surf, (20, 20, 30), (16, 12 + bob, 2, 2))
    pygame.draw.rect(surf, (20, 20, 30), (19, 12 + bob, 2, 2))
    # arm + lantern / casting hand
    if i == 7:
        pygame.draw.line(surf, cloak, (18, 22), (29, 12), 3)
        pygame.draw.circle(surf, (255, 230, 150), (29, 11), 3)
    else:
        sway = [0, 1, 0, -1][i % 4] if 2 <= i <= 5 else 0
        pygame.draw.line(surf, cloak, (20, 22 + bob), (25, 29 + bob), 3)
        pygame.draw.line(surf, (90, 80, 60), (25, 29 + bob), (25 + sway, 32 + bob), 1)
        pygame.draw.rect(surf, (255, 200, 90), (23 + sway, 32 + bob, 5, 6))
        pygame.draw.rect(surf, (255, 245, 200), (24 + sway, 34 + bob, 3, 2))


def player_frames():
    return frames("player", _draw_player, 12, 32, 48)


# --- Scenery ------------------------------------------------------------------
def shrine_surface(used):
    surf = pygame.Surface((40, 60), pygame.SRCALPHA)
    stone = (70, 70, 80) if not used else (40, 40, 46)
    pygame.draw.rect(surf, stone, (8, 20, 24, 40))
    pygame.draw.polygon(surf, stone, [(4, 22), (20, 6), (36, 22)])
    flame = (130, 180, 255) if not used else (60, 60, 70)
    pygame.draw.circle(surf, flame, (20, 32), 6)
    return surf


# The painted shrine: a 3 x 2 atlas of 512 px cells, the shrine in the same
# spot in each. 0 is waiting (its rune faintly lit), 1-4 wake it as he prays
# (motes, a swirl, a ring of light), 5 is spent (the rune dark).
SHRINE_TALL = 110          # how tall the shrine stands in the woods
LORE_TALL = 78             # ... and the lore tablets
SHRINE_CELL = 512
SHRINE_BOX = (55, 11, 403, 469)     # x, y, w, h of the shrine inside every cell
SHRINE_WAITING, SHRINE_SPENT = 0, 5
SHRINE_PRAYING = [1, 2, 3, 4]


def shrine_frames(height):
    """The six painted shrine frames, all scaled alike, or None if missing."""
    key = ("shrine_frames", height)
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, "Sprites", "Teal Rune Shrine Animation Atlas-2.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None
    x, y, w, h = SHRINE_BOX
    frames = []
    for i in range(6):
        row, col = divmod(i, 3)
        cell = pygame.Rect(col * SHRINE_CELL + x, row * SHRINE_CELL + y, w, h)
        frames.append(_solid(sheet.subsurface(cell).copy(), 20))
    frames = sprites.scale_frames(frames, height / h, smooth=True)
    _cache[key] = frames
    return frames


def lore_tablet(height):
    """The glowing runic tablet the lore stones are drawn with, or None."""
    key = ("lore_tablet", height)
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, "Sprites", "Glowing Runic Stone Tablet.png")
    try:
        image = _solid(pygame.image.load(path).convert_alpha(), 20)
    except (pygame.error, FileNotFoundError):
        return None
    image = image.subsurface(image.get_bounding_rect()).copy()
    image = sprites.scale_frames([image], height / image.get_height(), smooth=True)[0]
    _cache[key] = image
    return image


def lore_surface():
    surf = pygame.Surface((26, 34), pygame.SRCALPHA)
    pygame.draw.rect(surf, (60, 58, 64), (2, 6, 22, 28), border_radius=6)
    pygame.draw.line(surf, (150, 140, 200), (8, 14), (18, 14), 1)
    pygame.draw.line(surf, (150, 140, 200), (8, 19), (16, 19), 1)
    pygame.draw.line(surf, (150, 140, 200), (8, 24), (18, 24), 1)
    return surf


def gate_surface():
    surf = pygame.Surface((120, 190), pygame.SRCALPHA)
    pygame.draw.rect(surf, (30, 26, 36), (0, 30, 22, 160))
    pygame.draw.rect(surf, (30, 26, 36), (98, 30, 22, 160))
    pygame.draw.arc(surf, (30, 26, 36), (0, 0, 120, 80), 0, math.pi, 14)
    pygame.draw.rect(surf, (60, 10, 30), (22, 40, 76, 150))
    for k in range(6):
        pygame.draw.circle(surf, (255, 60, 80), (40 + (k % 3) * 20, 70 + (k // 3) * 40), 3)
    return surf


def status_panel_surface(tier):
    """Compact ornate status frame for the run title and sanity gauge."""
    key = ("status_panel", tier)
    if key in _cache:
        return _cache[key]

    w, h = 320, 150
    filenames = ("Lucid.png", "Uneasy.png", "Fraying.png")
    path = os.path.join(ASSET_DIR, "Sprites", "HUD", filenames[tier])
    try:
        image = pygame.image.load(path).convert_alpha()
    except pygame.error:
        image = None
    if image is not None:
        box = image.get_bounding_rect()
        if box.width:
            left = max(0, box.left)
            right = min(image.get_width(), box.right)
            image = image.subsurface((left, 0, right - left, image.get_height())).copy()
        surf = pygame.transform.smoothscale(image, (w, h))
        _cache[key] = surf
        return surf

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = (27, 24, 45)
    edge = (84, 76, 112)
    root = (95, 72, 105)
    accent = [(55, 190, 205), (200, 160, 230), (235, 70, 80)][tier]

    pygame.draw.rect(surf, (*dark, 170), (0, 0, w, h), border_radius=4)
    pygame.draw.rect(surf, edge, (0, 0, w, h), 2, border_radius=4)
    pygame.draw.rect(surf, (140, 125, 176), (4, 4, w - 8, h - 8), 1,
                     border_radius=3)

    pygame.draw.line(surf, root, (4, 67), (12, 54), 4)
    pygame.draw.line(surf, root, (12, 54), (18, 47), 3)
    pygame.draw.line(surf, root, (296, 67), (288, 54), 4)
    pygame.draw.line(surf, root, (288, 54), (282, 47), 3)
    for x, side in ((7, 1), (293, -1)):
        pygame.draw.polygon(surf, accent,
                            [(x, 16), (x + side * 8, 11),
                             (x + side * 5, 18)])

    _cache[key] = surf
    return surf


def progress_sprite(name, size):
    """Load and scale a painted exploration-progress sprite."""
    key = ("progress_sprite", name, size)
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, "Sprites", "Progress", name + ".png")
    try:
        image = pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None
    result = pygame.transform.smoothscale(image, size)
    _cache[key] = result
    return result


def boss_gate_frames():
    """Load the six frames of the enchanted forest boss gate."""
    key = "boss_gate_frames"
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, "Sprites", "Enchanted Forest Boss Door Animation.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except pygame.error:
        result = [gate_surface()]
    else:
        frame_w, frame_h = sheet.get_width() // 3, sheet.get_height() // 2
        result = [
            pygame.transform.scale(
                sheet.subsurface((col * frame_w, row * frame_h, frame_w, frame_h)),
                (192, 192))
            for row in range(2) for col in range(3)
        ]
    _cache[key] = result
    return result


def bramble_surface(w):
    """A patch of thorns. The hitbox is the lower 20 pixels."""
    key = ("bramble", w)
    if key in _cache:
        return _cache[key]
    surf = pygame.Surface((w, 40), pygame.SRCALPHA)
    rng = random.Random(w)
    stems = []
    for x in range(4, w - 4, 6):
        stems.append((x, x + rng.randint(-6, 6), rng.randint(3, 18), rng.choice((-8, 8))))
    # dark outline first, then the bright thorn on top, so it shows on any background
    for width, stem, tip in ((7, (16, 8, 20), (16, 8, 20)), (3, (170, 40, 90), (255, 110, 140))):
        for x, top_x, top, side in stems:
            pygame.draw.line(surf, stem, (x, 40), (top_x, top), width)
            pygame.draw.line(surf, stem, (x, 28), (x + side, 20), max(2, width - 2))
            pygame.draw.line(surf, tip, (top_x, top), (top_x, top + 5), width)
    _cache[key] = surf
    return surf


def campfire_surface(step):
    surf = pygame.Surface((80, 90), pygame.SRCALPHA)
    pygame.draw.line(surf, (60, 40, 30), (14, 86), (66, 74), 7)
    pygame.draw.line(surf, (50, 34, 26), (14, 74), (66, 86), 7)
    rng = random.Random(step)
    for color, scale in (((230, 90, 30), 1.0), ((255, 170, 50), 0.7), ((255, 240, 170), 0.4)):
        h = (52 + rng.randint(-8, 8)) * scale
        w = 22 * scale
        lean = rng.randint(-6, 6)
        pygame.draw.polygon(surf, color, [(40 - w, 78), (40 + w, 78), (40 + lean, 78 - h)])
    return surf


def grimoire_surface(opened=0.0, size=40):
    """The grimoire, drawn with shapes: closed (0.0) to open flat (1.0)."""
    key = ("grimoire", round(opened * 8), size)
    if key in _cache:
        return _cache[key]
    w, h = size * 2, size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cover, edge, page = (88, 34, 40), (40, 14, 20), (226, 214, 180)
    open_k = max(0.0, min(1.0, round(opened * 8) / 8))
    mid = w // 2
    spread = int(size * (0.15 + 0.85 * open_k))       # how far each half leans out
    lift = int(h * 0.35 * (1 - open_k))                 # a closed book stands taller
    for side in (-1, 1):
        far = mid + side * spread
        cover_pts = [(mid, h - 4), (far, h - 6 - lift // 2), (far, 6 + lift // 3), (mid, 4)]
        pygame.draw.polygon(surf, cover, cover_pts)
        pygame.draw.polygon(surf, edge, cover_pts, 2)
        if open_k > 0.2:
            inset = [(mid, h - 8), (far - side * 4, h - 9 - lift // 2),
                     (far - side * 4, 9 + lift // 3), (mid, 8)]
            pygame.draw.polygon(surf, page, inset)
            for k in range(3):                          # lines of ink
                y = 14 + k * (h - 26) // 3
                pygame.draw.line(surf, (110, 80, 90), (mid + side * 5, y),
                                 (far - side * 9, y + 1), 1)
    pygame.draw.line(surf, edge, (mid, 4), (mid, h - 4), 3)    # the spine
    pygame.draw.circle(surf, (255, 200, 110), (mid, h // 2), 3)  # the clasp's stone
    _cache[key] = surf
    return surf


def shadow(width):
    """A soft dark oval drawn under a character's feet."""
    key = ("shadow", width)
    if key not in _cache:
        surf = pygame.Surface((width, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 110), (0, 0, width, 16))
        _cache[key] = surf
    return _cache[key]


def ground_tile(color):
    surf = pygame.Surface((64, HEIGHT - GROUND_Y))
    surf.fill(color)
    dark = tuple(max(0, c - 10) for c in color)
    light = tuple(min(255, c + 45) for c in color)
    pygame.draw.line(surf, light, (0, 0), (64, 0), 3)
    rng = random.Random(3)
    for _ in range(14):
        x, y = rng.randint(0, 63), rng.randint(6, surf.get_height() - 2)
        pygame.draw.circle(surf, dark, (x, y), rng.randint(1, 3))
    return surf


def platform_surface(w, h, color):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, w, h), border_radius=4)
    light = tuple(min(255, c + 40) for c in color)
    pygame.draw.line(surf, light, (3, 1), (w - 4, 1), 2)
    return surf


# --- Parallax layers (each tiles horizontally at WIDTH) ------------------------
def _pine(surf, x, base, height, color):
    w = height * 0.35
    for k in range(3):
        top = base - height + k * height * 0.22
        pygame.draw.polygon(surf, color, [(x, top), (x - w * (0.5 + k * 0.2), top + height * 0.45),
                                          (x + w * (0.5 + k * 0.2), top + height * 0.45)])
    pygame.draw.rect(surf, color, (x - 3, base - height * 0.2, 6, height * 0.2))


def parallax_layers(act_info, seed):
    key = ("layers", act_info["name"], seed)
    if key in _cache:
        return _cache[key]
    rng = random.Random(f"{seed}:{act_info['name']}:sky")
    sky = act_info["sky"]
    far = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        col = tuple(min(255, int(c * (0.55 + 1.3 * t))) for c in sky)
        pygame.draw.line(far, col, (0, y), (WIDTH, y))
    for _ in range(90):
        x, y = rng.randint(0, WIDTH - 1), rng.randint(0, HEIGHT // 2)
        b = rng.randint(90, 200)
        far.set_at((x, y), (b, b, b + 20 if b < 235 else 255))
    moon_x = rng.randint(200, WIDTH - 200)
    far.blit(glow(70, (200, 200, 230), 90), (moon_x - 70, 20))
    pygame.draw.circle(far, (215, 212, 225), (moon_x, 90), 26)
    pygame.draw.circle(far, tuple(int(c * 0.55) for c in sky), (moon_x + 9, 84), 22)

    mid = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    tree = act_info["tree"]
    fog = act_info["fog"]

    def blend(a, b, t):
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    # two rows of pines: a pale far row, then a darker near row
    for shade, count, low, high in ((0.42, 22, 110, 200), (0.2, 24, 150, 270)):
        col = blend(tree, fog, shade)
        for _ in range(count):
            x = rng.randint(0, WIDTH)
            h = rng.randint(low, high)
            for dx in (-WIDTH, 0, WIDTH):
                _pine(mid, x + dx, GROUND_Y + 10, h, col)

    # tall trunks: they stand BEHIND the boy so they never hide a hazard
    trunks = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    trunk_col = blend(tree, fog, 0.06)
    for _ in range(5):
        x = rng.randint(0, WIDTH)
        w = rng.randint(18, 32)
        for dx in (-WIDTH, 0, WIDTH):
            pygame.draw.rect(trunks, trunk_col, (x + dx, 0, w, GROUND_Y + 20))
            for b in range(3):
                by = rng.randint(40, 300)
                pygame.draw.line(trunks, trunk_col, (x + dx + w // 2, by),
                                 (x + dx + w // 2 + rng.choice((-60, 60)), by - 40), 5)

    # low fog drifts in front of everything
    near = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for k in range(5):
        y = GROUND_Y - 60 + k * 10
        pygame.draw.ellipse(near, (*fog, 20), (-100, y, WIDTH + 200, 80))
    result = (far, mid, trunks, near)
    _cache[key] = result
    return result


def vignette(strength, color=(10, 0, 14)):
    """Dark edges that close in as sanity drops. strength 0..1.

    color tints the edge: near-black while Uneasy, blood red while Fraying.
    """
    level = max(0, min(10, int(strength * 10)))
    key = ("vignette", level, color)
    if key in _cache:
        return _cache[key]
    small_w, small_h = 96, 54
    small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    for y in range(small_h):
        for x in range(small_w):
            dx = (x - small_w / 2) / (small_w / 2)
            dy = (y - small_h / 2) / (small_h / 2)
            d = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.25)
            inner = 0.75 - 0.45 * level / 10      # dark edge creeps inward
            t = max(0.0, (d - inner) / (1 - inner)) if d > inner else 0.0
            a = int(min(255, t * 255 * (0.35 + 0.65 * level / 10)))
            small.set_at((x, y), (*color, a))
    surf = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
    _cache[key] = surf
    return surf


# =============================================================================
# THE TEAM'S PAINTED ART
# =============================================================================
CHILD_SHEET = os.path.join(ASSET_DIR, "Sprites", "MC (detailed)",
                           "the child spritesheet (detailed).png")
# The same sheet with the grimoire painted out of the calm row (made by
# tools/remove_book.py). Used in the opening, before he finds the book.
BOOKLESS_SHEET = os.path.join(ASSET_DIR, "Sprites", "MC (detailed)",
                              "the child spritesheet (no book).png")
PAGE_FILES = ["page (high sanity - cyan).png",      # lucid
              "page (low sanity - violet).png",     # uneasy
              "page (critical sanity - crimson).png"]  # fraying
DEATH_FRAME_TIME = 0.1
DEATH_TALL = 440             # how tall the boy stands in the death scene


# --- The forest ---------------------------------------------------------------
class ForestScene:
    """The painted forest from scene.py, tinted per act.

    scene.py scrolls its layers by adding the camera's movement each frame.
    Here the layers are placed from the camera's absolute position instead,
    so the woods, a fight and the menus can all share the same pictures.
    """

    def __init__(self):
        from scene import ParallaxBackground
        self.layers = ParallaxBackground(HEIGHT).layers
        self.tinted = {}

    def images(self, act):
        act = act_info(act)["look"]          # the endless woods reuse the three looks
        if act not in self.tinted:
            tint = ACTS[act]["tint"]
            images = []
            for layer in self.layers:
                image = layer.image
                if tint:
                    image = image.copy()
                    image.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
                images.append(image)
            self.tinted[act] = images
        return self.tinted[act]

    def draw(self, surface, act, camera_x, time, y=0):
        for layer, image in zip(self.layers, self.images(act)):
            # speed: how much the layer follows the camera; drift: mist moving alone
            offset = (camera_x * layer.speed + time * 60 * layer.drift) % layer.width
            x = -offset
            while x < surface.get_width():
                surface.blit(image, (round(x), y))
                x += layer.width
        if y == 0:
            # the painted ground stops just short of the window's bottom edge
            pygame.draw.rect(surface, (14, 10, 22), (0, HEIGHT - 20, surface.get_width(), 20))


def forest_scene():
    """The shared ForestScene, or None if the scene art is missing."""
    if "forest" not in _cache:
        try:
            _cache["forest"] = ForestScene()
        except Exception as error:
            print(f"Scene art not found, drawing the woods with shapes ({error})")
            _cache["forest"] = None
    return _cache["forest"]


# --- Creatures -------------------------------------------------------------------
def creature_hover(kind, height):
    """How far above the ground a creature floats when drawn `height` px tall."""
    info = creature_table.ENEMIES[kind]
    return info["hover"] * height / info["height"]


def _death_rows(kind):
    """Cut a death sheet into rows of 4 pictures, each row standing on its bottom edge."""
    key = ("death_rows", kind)
    if key in _cache:
        return _cache[key]
    path, bands = DEATH_SHEETS[kind]
    sheet = sprites.load_image_safely(os.path.join(creature_table.ENEMY_DIR, path))
    rows = []
    if sheet:
        w = sheet.get_width() // 4
        for top, bottom in bands:
            cells = [sheet.subsurface((c * w, top, w, bottom - top)).copy() for c in range(4)]
            if creature_table.ENEMIES[kind]["faces_right"]:
                cells = sprites.flip_frames(cells)
            lowest = max(cell.get_bounding_rect().bottom for cell in cells)
            if lowest > 0:
                rows.append([cell.subsurface((0, 0, w, lowest)).copy() for cell in cells])
    _cache[key] = rows
    return rows


def creature_frames(kind, height):
    """{'idle', 'hurt', 'attack', 'death'} frame lists, `height` px tall, facing left.

    Every frame is drawn with get_rect(midbottom=feet). 'death' is empty if
    the death sheet is missing (the creature then just fades out).
    """
    key = ("creature", kind, height)
    if key in _cache:
        return _cache[key]
    info = creature_table.ENEMIES[kind]
    base = creature_table.load_enemy_frames(kind)       # cut and cleaned once, cached there
    factor = height / info["height"]
    result = {row: sprites.scale_frames(frames, factor, smooth=True)
              for row, frames in base.items()}
    rows = _death_rows(kind)
    result["death"] = []
    if rows:
        standing = rows[0][0].get_bounding_rect().height
        for cells in rows:
            result["death"] += sprites.scale_frames(cells, height / standing, smooth=True)
    _cache[key] = result
    return result


# --- The child -------------------------------------------------------------------
# The detailed sheet has 3 rows, one per sanity look (calm, shaken, mad), and
# in each row 3 right-facing pictures: stride, stand, stride.
HERO_LOOK = [0, 1, 2]        # sanity tier (lucid, uneasy, fraying) -> row of the sheet

# His eye. As sanity falls it is recoloured from brown towards a glowing red
# (levels 0..EYE_RED); in the death scene it then drains to black
# (levels EYE_RED+1..EYE_BLACK).
EYE_RED = 5
EYE_BLACK = 8
EYE_CALM = (150, 96, 62)     # eye colour at full sanity
EYE_MAD = (255, 24, 24)      # eye colour at no sanity
# Where the eye is in each picture on the sheet: (row, column) -> (x0, y0, x1, y1)
# measured inside that picture, like the frame rectangles in enemies.py.
EYE_BOXES = {
    (0, 0): (160, 86, 180, 104), (0, 1): (133, 84, 154, 104), (0, 2): (141, 85, 161, 104),
    (1, 0): (160, 86, 180, 102), (1, 1): (134, 85, 154, 102), (1, 2): (142, 85, 161, 102),
    (2, 0): (160, 78, 181, 96), (2, 1): (131, 78, 154, 95), (2, 2): (141, 79, 161, 96),
}


def eye_level(sanity, max_sanity=100):
    """0 at full sanity up to EYE_RED at none."""
    lost = 1 - max(0.0, min(1.0, sanity / max_sanity))
    return round(lost * EYE_RED)


def _is_iris(r, g, b):
    """Is this pixel part of the coloured eye (red in two rows, violet in one)?"""
    red = r > 110 and g < 0.4 * r and b < 0.4 * r + 10
    violet = b > g + 35 and r > g + 30 and g < 110
    return red or violet


def _eye_sheet(sheet, level, tag="book"):
    """A copy of the child's sheet with every eye recoloured for one eye level."""
    key = ("eye_sheet", tag, level)
    if key in _cache:
        return _cache[key]
    if level <= EYE_RED:
        t = level / EYE_RED
        target = [EYE_CALM[i] + (EYE_MAD[i] - EYE_CALM[i]) * t for i in range(3)]
        glow = 1 + 0.6 * t          # a mad eye is also brighter
        shine = 1.0
    else:
        k = (level - EYE_RED) / (EYE_BLACK - EYE_RED)   # 0..1 on the way to black
        target = [EYE_MAD[i] * (1 - k) for i in range(3)]
        glow = 1.6
        shine = 1 - k               # the white glint goes out too
    out = sheet.copy()
    cw, ch = sheet.get_width() / 6, sheet.get_height() / 3
    for (row, col), (x0, y0, x1, y1) in EYE_BOXES.items():
        ox, oy = round(col * cw), round(row * ch)
        for y in range(oy + y0, oy + y1):
            for x in range(ox + x0, ox + x1):
                r, g, b, a = sheet.get_at((x, y))
                if a < 200:
                    continue
                if _is_iris(r, g, b):
                    v = min(1.0, max(r, g, b) / 255 * glow)     # keep the painted shading
                    out.set_at((x, y), (int(target[0] * v), int(target[1] * v),
                                        int(target[2] * v), a))
                elif shine < 1 and min(r, g, b) > 200:
                    out.set_at((x, y), (int(r * shine), int(g * shine), int(b * shine), a))
    _cache[key] = out
    return out


def _child_rows(sheet, height):
    """Cut one sheet into 3 rows of [stride, stand, stride], `height` px tall."""
    cw, ch = sheet.get_width() / 6, sheet.get_height() / 3
    # columns 0-2 face right; the left-facing ones are made by flipping
    cells = [sheet.subsurface((round(c * cw), round(r * ch), int(cw), int(ch))).copy()
             for r in range(3) for c in range(3)]
    cells = sprites.align_by_feet(sprites.crop_to_content(cells))
    factor = height / cells[1].get_bounding_rect().height
    cells = sprites.scale_frames(cells, factor, smooth=True)
    return [cells[0:3], cells[3:6], cells[6:9]]


def hero_frames(height):
    """The boy's pictures at one size.

    Returns {'looks': looks, 'death': frames or None} where
    looks[row][eye_level] is {'right': poses, 'left': poses} and poses is
    {'idle': Surface, 'walk': [Surfaces], 'jump': Surface, 'cast': Surface}.
    row 0 is calm, 1 shaken, 2 mad. Use hero_poses() to pick the right one.
    """
    key = ("hero", height)
    if key in _cache:
        return _cache[key]

    def both_ways(poses):
        left = {name: (sprites.flip_frames(value) if isinstance(value, list)
                       else pygame.transform.flip(value, True, False))
                for name, value in poses.items()}
        return dict(right=poses, left=left)

    sheet = sprites.load_image_safely(CHILD_SHEET)
    if sheet:
        looks = [[], [], []]
        for level in range(EYE_BLACK + 1):
            rows = _child_rows(_eye_sheet(sheet, level), height)
            for row, (a, stand, b) in enumerate(rows):
                looks[row].append(both_ways(dict(idle=stand, walk=[a, stand, b, stand],
                                                 jump=a, cast=b)))
        death = None
    else:
        drawn = [pygame.transform.scale(f, (round(height * 32 / 48), height))
                 for f in player_frames()]
        look = both_ways(dict(idle=drawn[0], walk=drawn[2:6], jump=drawn[6], cast=drawn[7]))
        looks = [[look] * (EYE_BLACK + 1)] * 3
        death = drawn[8:12]
    _cache[key] = dict(looks=looks, death=death)
    return _cache[key]


# The death sheet is a 3 x 3 grid with 8 pictures (the last cell is empty).
# The artist's columns are a little narrower than a third of the sheet, so the
# boy drifts left inside each third; these are his centres, measured from the
# sheet, so every picture can be cut around him and he stays on one spot.
UNRAVEL_CENTERS = [140, 384, 626]   # x of the boy in columns 0, 1, 2
UNRAVEL_ROW = 259                   # height of one row
UNRAVEL_HALF = 120                  # half the width cut around him
UNRAVEL_COUNT = 8


def unravel_frames(height):
    """Eight painted frames of the boy dissolving into purple wisps.

    Every frame is cut on the same box around him and scaled by one factor, so
    he neither moves nor changes size between them. Each is returned painted
    onto black (an opaque picture whose colours are already multiplied by their
    transparency), which lets the death scene blend one frame smoothly into
    the next by adding them together.
    """
    key = ("unravel_frames", height)
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, "Sprites", "Death",
                        "Fading Boy with Purple Wisps.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None
    cut = []
    for i in range(UNRAVEL_COUNT):
        row, col = divmod(i, 3)
        box = pygame.Rect(UNRAVEL_CENTERS[col] - UNRAVEL_HALF, row * UNRAVEL_ROW,
                          UNRAVEL_HALF * 2, UNRAVEL_ROW).clip(sheet.get_rect())
        cut.append(_solid(sheet.subsurface(box).copy()))
    boy = cut[0].get_bounding_rect(min_alpha=60).height or UNRAVEL_ROW
    cut = sprites.scale_frames(cut, height / boy, smooth=True)
    frames = []
    for frame in cut:
        dark = pygame.Surface(frame.get_size())       # opaque black
        dark.blit(frame, (0, 0))
        frames.append(dark)
    _cache[key] = frames
    return frames


# The opening atlas is a 3 x 3 grid, but the boy pokes over the grid lines
# (his hair reaches into the row above), so each picture has its own box,
# cut in the empty gaps between them: (x, y, w, h) in sheet pixels.
OPENING_CELLS = [(0, 0, 255, 237), (255, 0, 265, 237), (520, 0, 248, 237),      # lie, push up, sit
                 (0, 237, 256, 250), (256, 237, 259, 250), (515, 237, 253, 250),  # sit, kneel, crouch
                 (0, 487, 243, 281), (243, 487, 267, 281), (510, 487, 258, 281)]  # stand, step, step
OPENING_STAND = 6          # the standing picture: the one matched to the boy's usual size


def _solid(frame, min_alpha=8):
    """The frame with its faint background noise (alpha below min_alpha) removed."""
    mask = pygame.mask.from_surface(frame, min_alpha)
    return mask.to_surface(setsurface=frame, unsetcolor=(0, 0, 0, 0))


def opening_boy_frames(height):
    """Nine wake-to-walk frames from the painted opening cutscene atlas.

    All nine are scaled by ONE factor, chosen so that he stands exactly as tall
    as the boy with the grimoire (hero_frames at the same height), so he does
    not grow or shrink as he gets up, walks and takes the book. The standing
    and walking frames (3-8) share one canvas with the feet at the bottom
    centre, like the hero's own frames, so get_rect(midbottom=feet) puts every
    one of them on the same spot.
    """
    key = ("opening_boy_frames", height)
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, "Sprites", "Opening", "Wake to Walk.png")
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None
    frames = []
    for cell in OPENING_CELLS:
        frame = _solid(sheet.subsurface(cell).copy())
        box = frame.get_bounding_rect()
        if box.width and box.height:
            frame = frame.subsurface(box).copy()
        frames.append(frame)
    # how tall the boy with the book really stands (his sheet has faint pixels
    # above his hair, so measure the solid part of him)
    hero_idle = hero_frames(height)["looks"][0][0]["right"]["idle"]
    tall = hero_idle.get_bounding_rect(min_alpha=60).height or height
    factor = tall / frames[OPENING_STAND].get_bounding_rect(min_alpha=60).height
    frames = sprites.scale_frames(frames, factor, smooth=True)
    frames[3:] = sprites.align_by_feet(frames[3:])
    _cache[key] = frames
    return frames


def hero_bookless(height):
    """The calm boy WITHOUT the grimoire, for the opening: {'right': poses, 'left': poses}.

    Falls back to the usual pictures (with the book) if the sheet is missing.
    """
    key = ("hero_bookless", height)
    if key in _cache:
        return _cache[key]
    sheet = sprites.load_image_safely(BOOKLESS_SHEET)
    if sheet:
        a, stand, b = _child_rows(_eye_sheet(sheet, 0, "bookless"), height)[0]
        poses = dict(idle=stand, walk=[a, stand, b, stand], jump=a, cast=b)
        left = {name: (sprites.flip_frames(v) if isinstance(v, list)
                       else pygame.transform.flip(v, True, False)) for name, v in poses.items()}
        result = dict(right=poses, left=left)
    else:
        hero = hero_frames(height)
        result = {side: hero["looks"][0][0][side] for side in ("right", "left")}
    _cache[key] = result
    return result


def hero_poses(hero, sanity, max_sanity=100, facing="right"):
    """The boy's poses for his current sanity: the look row and the eye colour."""
    from words import sanity_tier
    row = HERO_LOOK[sanity_tier(sanity)]
    return hero["looks"][row][eye_level(sanity, max_sanity)][facing]


# --- Pages -----------------------------------------------------------------------
def page_image(look, height):
    """The dropped page: 0 cyan (calm), 1 violet (shaken), 2 crimson (mad)."""
    key = ("page", look, height)
    if key not in _cache:
        image = sprites.load_image_safely(
            os.path.join(ASSET_DIR, "Sprites", "drops", PAGE_FILES[look]))
        if image:
            w = round(image.get_width() * height / image.get_height())
            image = pygame.transform.smoothscale(image, (w, height))
        _cache[key] = image
    return _cache[key]


def preload(report):
    """Load the slow things up front. report(text) shows what is happening."""
    report("Painting the woods...")
    forest_scene()
    for kind, info in creature_table.ENEMIES.items():
        report(f"Waking the {info['name']}...")
        creature_table.load_enemy_frames(kind)
        _death_rows(kind)
    report("Finding the child...")
    hero_frames(84)
    hero_frames(120)
    hero_bookless(120)       # the opening, before he finds the grimoire
    opening_boy_frames(120)  # ... the painted wake-to-walk frames
    unravel_frames(DEATH_TALL)   # the death scene, so it starts without a hitch
    shrine_frames(SHRINE_TALL)   # the painted shrine and its prayer
    lore_tablet(LORE_TALL)       # the runic tablets in the woods
    hero_frames(DEATH_TALL)
