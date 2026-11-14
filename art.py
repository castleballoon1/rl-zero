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
from bestiary import ACTS, DEATH_SHEETS
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


def vignette(strength):
    """Dark edges that close in as sanity drops. strength 0..1."""
    level = max(0, min(10, int(strength * 10)))
    key = ("vignette", level)
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
            small.set_at((x, y), (10, 0, 14, a))
    surf = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
    _cache[key] = surf
    return surf


# =============================================================================
# THE TEAM'S PAINTED ART
# =============================================================================
CHILD_SHEET = os.path.join(ASSET_DIR, "Sprites", "MC (detailed)",
                           "the child spritesheet (detailed).png")
PAGE_FILES = ["page (high sanity - cyan).png",      # lucid
              "page (low sanity - violet).png",     # uneasy / fraying
              "page (critical sanity - crimson).png"]  # mad
DEATH_FRAME_TIME = 0.1


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
def _child_rows(height):
    """The detailed child: 3 rows (one per sanity look) of [stride, stand, stride]."""
    sheet = sprites.load_image_safely(CHILD_SHEET)
    if sheet is None:
        return None
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

    Returns {'looks': [look, look, look], 'death': frames or None}. A look is
    {'right': poses, 'left': poses} and poses is
    {'idle': Surface, 'walk': [Surfaces], 'jump': Surface, 'cast': Surface}.
    looks[0] is calm, looks[1] is shaken, looks[2] is mad.
    """
    key = ("hero", height)
    if key in _cache:
        return _cache[key]

    def both_ways(poses):
        left = {name: (sprites.flip_frames(value) if isinstance(value, list)
                       else pygame.transform.flip(value, True, False))
                for name, value in poses.items()}
        return dict(right=poses, left=left)

    rows = _child_rows(height)
    if rows:
        looks = [both_ways(dict(idle=stand, walk=[a, stand, b, stand], jump=a, cast=b))
                 for a, stand, b in rows]
        death = None      # no painted death yet: the fight tips him over and fades him
    else:
        drawn = [pygame.transform.scale(f, (round(height * 32 / 48), height))
                 for f in player_frames()]
        look = both_ways(dict(idle=drawn[0], walk=drawn[2:6], jump=drawn[6], cast=drawn[7]))
        looks = [look, look, look]
        death = drawn[8:12]
    _cache[key] = dict(looks=looks, death=death)
    return _cache[key]


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
