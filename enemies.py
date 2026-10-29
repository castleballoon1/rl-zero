"""Every enemy in one table, plus a loader that turns its spritesheet into frames.

All enemy sheets share one layout: 4 columns x 3 rows.
    row 0 = idle, row 1 = hurt (recoil), row 2 = attack
The art spills over the grid lines, so each frame's rectangle is listed
by hand, like the down_states / left_states dictionaries in class 11.
(x, y, width, height) in sheet pixels. They were measured with
tools/measure_frames.py; re-run it if a sheet is re-exported.

To add an enemy: add an entry to ENEMIES. Nothing else needs to change.
"""
import os
import pygame
import sprites

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENEMY_DIR = os.path.join(BASE_DIR, "assets", "Sprites", "Enemies")

# Stats and flavour text for everything except the stag are first guesses,
# for the team to tune.
ENEMIES = {
    "stag": {
        'name': "Lantern Stag",
        'short': "stag",                       # used in messages: "the stag is burning"
        'sheet': os.path.join("Lantern_Stag_Spritesheet", "LanternStag.png"),
        'faces_right': True,                   # drawn facing right, so flip it to face the player
        'height': 230,                         # height on screen in combat, in pixels
        'hover': 0,                            # pixels above the ground (for flying enemies)
        'max_hp': 140,
        'attack': (8, 14),                     # damage range of its attack
        'attack_text': "The stag's lantern flares!",
        'frames': {
            'idle': [(0, 0, 369, 364), (369, 0, 369, 364), (738, 0, 358, 364), (1096, 0, 352, 364)],
            'hurt': [(0, 364, 362, 361), (362, 364, 362, 362), (724, 364, 377, 362), (1101, 364, 347, 362)],
            'attack': [(0, 725, 362, 361), (362, 726, 372, 360), (734, 726, 405, 360), (1139, 726, 309, 360)],
        },
    },
    "moth": {
        'name': "Moth Choir",
        'short': "choir",
        'sheet': os.path.join("Moth Choir-SpriteSheet", "Moth Choir.png"),
        'faces_right': False,
        'height': 200,
        'hover': 28,
        'max_hp': 90,
        'attack': (6, 10),
        'attack_text': "A storm of eyed wings slices past you!",
        'frames': {
            'idle': [(0, 0, 361, 367), (361, 0, 362, 368), (723, 0, 362, 367), (1085, 0, 362, 367)],
            'hurt': [(0, 367, 392, 361), (392, 368, 331, 360), (723, 367, 362, 369), (1085, 367, 362, 361)],
            'attack': [(0, 728, 361, 359), (361, 728, 360, 359), (721, 736, 375, 351), (1096, 728, 351, 359)],
        },
    },
    "maw": {
        'name': "Mire Maw",
        'short': "maw",
        'sheet': os.path.join("Mire_Maw_Spritesheet", "Mire_Maw.png"),
        'faces_right': False,
        'height': 190,
        'hover': 0,
        'max_hp': 160,
        'attack': (10, 16),
        'attack_text': "The Mire Maw lunges, jaws wide!",
        'frames': {
            'idle': [(0, 0, 388, 343), (388, 0, 387, 345), (775, 0, 382, 344), (1157, 0, 379, 344)],
            'hurt': [(0, 343, 388, 340), (388, 345, 380, 336), (768, 344, 384, 338), (1152, 344, 384, 338)],
            'attack': [(0, 683, 379, 341), (379, 681, 357, 343), (736, 682, 428, 342), (1164, 682, 372, 342)],
        },
    },
    "pilgrim": {
        'name': "Rootbound Pilgrim",
        'short': "pilgrim",
        'sheet': os.path.join("Rootnound_Pilgrim_SpriteSheet", "Rootbound_Pilgirm.png"),
        'faces_right': False,
        'height': 240,
        'hover': 0,
        'max_hp': 180,
        'attack': (9, 15),
        'attack_text': "Rootbound arms lash out and drag at you!",
        'frames': {
            'idle': [(0, 0, 407, 376), (407, 0, 380, 376), (787, 0, 390, 376), (1177, 0, 359, 376)],
            'hurt': [(0, 376, 438, 350), (438, 376, 373, 352), (811, 376, 363, 352), (1174, 376, 362, 352)],
            'attack': [(0, 726, 453, 298), (453, 728, 362, 296), (815, 728, 391, 296), (1206, 728, 330, 296)],
        },
    },
    "bellwether": {
        'name': "Starved Bellwether",
        'short': "bellwether",
        'sheet': os.path.join("Starved_Bellwether_SpriteSheet", "Starved_Bellwether .png"),
        'faces_right': False,
        'height': 240,
        'hover': 0,
        'max_hp': 220,
        'attack': (12, 18),
        'attack_text': "The bell tolls, and the sound tears through you!",
        'frames': {
            'idle': [(0, 0, 384, 341), (384, 0, 384, 341), (768, 0, 384, 341), (1152, 0, 384, 341)],
            'hurt': [(0, 341, 384, 341), (384, 341, 384, 341), (768, 341, 384, 341), (1152, 341, 384, 341)],
            'attack': [(0, 682, 384, 342), (384, 682, 389, 342), (773, 682, 379, 342), (1152, 682, 384, 342)],
        },
    },
}

ROWS = ('idle', 'hurt', 'attack')
OUTLINE_COLOR = (215, 190, 255, 70)  # pale rim so dark creatures stand out from the dark forest

_cache = {}  # (key, height) -> frames, so each sheet is only cut once


def make_placeholder_enemy():
    """Simple drawn creature, used if a sheet is missing."""
    frames = []
    for glow in (200, 255):
        surf = pygame.Surface((90, 84), pygame.SRCALPHA)
        body = (70, 45, 90)
        pygame.draw.ellipse(surf, body, (10, 34, 60, 30))
        for x in (18, 28, 52, 62):
            pygame.draw.rect(surf, body, (x, 58, 5, 26))
        pygame.draw.polygon(surf, body, [(30, 40), (18, 18), (10, 24), (20, 46)])
        pygame.draw.ellipse(surf, body, (4, 12, 18, 12))
        pygame.draw.circle(surf, (glow, glow - 40, 60), (8, 38), 5)
        frames.append(surf)
    return frames


def load_enemy_frames(key, height=None):
    """Return {'idle': [...], 'hurt': [...], 'attack': [...]} ready to draw.

    Frames face LEFT (toward the player), are scaled so the idle pose is
    `height` pixels tall, and all share one feet position, so drawing any
    frame with get_rect(midbottom=feet) puts its feet on the same spot.
    """
    enemy = ENEMIES[key]
    height = height or enemy['height']
    if (key, height) in _cache:
        return _cache[(key, height)]

    sheet = sprites.load_image_safely(os.path.join(ENEMY_DIR, enemy['sheet']))
    if sheet:
        rows = {row: [sprites.clean_frame(f) for f in sprites.cut_frames(sheet, enemy['frames'][row])]
                for row in ROWS}
        if enemy['faces_right']:
            rows = {row: sprites.flip_frames(frames) for row, frames in rows.items()}
    else:
        placeholder = make_placeholder_enemy()
        rows = {row: placeholder for row in ROWS}

    # Align ALL rows together, so switching idle -> hurt -> attack doesn't hop
    everything = rows['idle'] + rows['hurt'] + rows['attack']
    aligned = sprites.align_by_feet(everything)
    factor = height / aligned[0].get_bounding_rect().height
    aligned = sprites.scale_frames(aligned, factor, smooth=sheet is not None)
    aligned = sprites.outlined(aligned, OUTLINE_COLOR)

    n = len(rows['idle'])
    m = len(rows['hurt'])
    result = {'idle': aligned[:n], 'hurt': aligned[n:n + m], 'attack': aligned[n + m:]}
    _cache[(key, height)] = result
    return result
