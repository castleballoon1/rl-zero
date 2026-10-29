import os
import sys
import math
import random
import pygame

pygame.init()

# Screen Configuration
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Spell Typer - Combat Prototype")

clock = pygame.time.Clock()
FPS = 60

# Paths are built from this file's folder, so the game finds its assets
# no matter which folder you run it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(*parts):
    return os.path.join(BASE_DIR, "assets", *parts)


# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PURPLE = (75, 0, 130)
GOLD = (255, 215, 0)
GRAY = (100, 100, 100)
RED = (220, 20, 60)
GREEN = (80, 220, 120)
LIGHT_GRAY = (170, 165, 185)
PARCHMENT = (235, 222, 190)
PANEL_FILL = (22, 16, 34, 225)   # (r, g, b, alpha) - see-through dark violet
PANEL_EDGE = (150, 120, 60)      # muted gold, so the UI frames the scene instead of shouting
EMBER = (255, 120, 40)
FROST = (130, 200, 255)
WARD_BLUE = (120, 160, 255)
SOUL = (190, 90, 255)

# Fonts (Courier is monospaced, so every letter of an incantation is the same width)
font_large = pygame.font.SysFont("Courier New", 32, bold=True)
font_med = pygame.font.SysFont("Courier New", 24, bold=True)
font_small = pygame.font.SysFont("Courier New", 18)
font_small_bold = pygame.font.SysFont("Courier New", 18, bold=True)
font_tiny = pygame.font.SysFont("Courier New", 14)

# -------------------------------------------------------------------------
# LAYOUT
# Every position on screen is defined here, so the design can be tweaked in
# one place. Characters are placed by their FEET (midbottom) on GROUND_Y,
# so sprites of different sizes always stand on the same line.
# -------------------------------------------------------------------------
GROUND_Y = 400
PLAYER_FEET = (200, GROUND_Y)
ENEMY_FEET = (610, GROUND_Y)

# The dirt path in the forest scene art sits at y = 476 (when the scene is
# 600 px tall). The scene is drawn shifted up so the path lines up with
# GROUND_Y and isn't hidden behind the bottom panel.
SCENE_PATH_Y = 476

PLAYER_SCALE = 3                 # same pixel-art scale as main.py
ENEMY_TARGET_HEIGHT = 230        # enemy is scaled to this height, whatever its file size

BANNER_RECT = pygame.Rect(150, 12, 500, 54)      # combat log at the top
PANEL_RECT = pygame.Rect(16, 412, 768, 180)      # whole bottom panel
TYPING_RECT = pygame.Rect(16, 412, 500, 180)     # left: the spell you are typing
GRIMOIRE_RECT = pygame.Rect(526, 412, 258, 180)  # right: list of collected spells

# Lantern Stag spritesheet: a 4 x 3 grid, but the antlers and hooves spill
# over the grid lines, so a plain grid cut would grab pieces of the
# neighbouring frames. Instead each frame's rectangle is listed by hand,
# like the down_states / left_states dictionaries in class 11.
# (x, y, width, height) in sheet pixels.
STAG_SHEET = asset_path("Sprites", "Enemies", "Lantern_Stag_Spritesheet", "LanternStag.png")
STAG_IDLE_RECTS = [(27, 0, 345, 374), (399, 0, 345, 374), (767, 0, 331, 374), (1123, 0, 325, 374)]
STAG_ATTACK_RECTS = [(27, 376, 327, 358), (401, 376, 314, 358), (729, 376, 385, 358), (1139, 376, 309, 358)]
ENEMY_FACES_RIGHT = True         # the stag is drawn facing right; flip it to face the player
ENEMY_FRAME_TIME = 0.18          # seconds each idle frame is shown
ATTACK_ANIM_TIME = 0.5           # the attack row plays during the last 0.5 s of the enemy's turn

# Combat tuning
PLAYER_NAME = "Wanderer"         # placeholder until the name-entry screen exists
ENEMY_NAME = "Lantern Stag"
PLAYER_MAX_HP = 100
ENEMY_MAX_HP = 140
ENEMY_ATTACK = (8, 14)           # enemy hits for a random amount in this range
ENEMY_TURN_DELAY = 0.9           # pause so the player can read what happened
BURN_DAMAGE = 6


# -------------------------------------------------------------------------
# MODULAR SPELL SCRIPTING
# -------------------------------------------------------------------------
class Spell:
    def __init__(self, name, incantation, effect_func, damage=25,
                 cooldown=0, description="", color=GOLD):
        self.name = name
        self.incantation = incantation.lower()
        self.effect_func = effect_func
        self.damage = damage
        self.cooldown = cooldown         # how many turns you must wait after casting
        self.description = description   # one line shown in the typing panel
        self.color = color               # used for the card accent and hit effects
        self.turns_left = 0              # 0 = ready to cast

    def is_ready(self):
        return self.turns_left <= 0

    def cast(self, combat_state):
        print(f" Casting Spell: {self.name} ('{self.incantation}')")
        self.turns_left = self.cooldown
        if self.effect_func:
            self.effect_func(combat_state)


# --- helpers the spell effects share (damage numbers, sparks, shake) ------
def damage_enemy(state, amount, color):
    state['enemy_hp'] = max(0, state['enemy_hp'] - amount)
    state['enemy_shake'] = 0.3
    popups.append(FloatingText(f"-{amount}", color, enemy_rect.midtop))
    burst(enemy_rect.center, color, 22)


def heal_player(state, amount):
    before = state['player_hp']
    state['player_hp'] = min(state['player_max_hp'], before + amount)
    healed = state['player_hp'] - before
    popups.append(FloatingText(f"+{healed}", GREEN, player_rect.midtop))
    burst(player_rect.center, GREEN, 14)
    return healed


# --- the spells themselves -------------------------------------------------
def spark_effect(state):
    damage_enemy(state, state['current_spell'].damage, GOLD)
    state['message'] = f"Spark struck the beast for {state['current_spell'].damage} damage!"


def ember_effect(state):
    spell = state['current_spell']
    damage_enemy(state, spell.damage, EMBER)
    state['enemy_burn'] = 3
    state['message'] = f"Ember Lash sears for {spell.damage}! The stag is burning."


def frost_effect(state):
    spell = state['current_spell']
    damage_enemy(state, spell.damage, FROST)
    state['enemy_frozen'] = True
    state['message'] = f"Frost Bind deals {spell.damage} and freezes the stag in place!"


def ward_effect(state):
    state['player_ward'] = True
    burst(player_rect.center, WARD_BLUE, 16)
    state['message'] = "A ward shimmers around you. The next attack will be blocked."


def mend_effect(state):
    healed = heal_player(state, state['current_spell'].damage)
    state['message'] = f"Mend knits your wounds. You recover {healed} HP."


def drain_effect(state):
    spell = state['current_spell']
    damage_enemy(state, spell.damage, SOUL)
    healed = heal_player(state, spell.damage // 2)
    state['message'] = f"Soul Drain tears {spell.damage} from the stag and returns {healed} HP to you."


# Initialize our baseline spell
baseline_spell = Spell(
    name="Spark",
    incantation="lumos",
    effect_func=spark_effect,
    damage=30,
    description="A quick bolt of light.",
    color=GOLD,
)

# The grimoire: every spell the player has collected, in display order.
# To add a spell: write an effect function above, then add a Spell(...) here.
grimoire = [
    baseline_spell,
    Spell("Ember Lash", "incendio", ember_effect, damage=18, cooldown=2,
          description=f"Burns for {BURN_DAMAGE}/turn over 3 turns.", color=EMBER),
    Spell("Frost Bind", "glacius", frost_effect, damage=12, cooldown=3,
          description="Freezes the enemy. It loses its next attack.", color=FROST),
    Spell("Ward", "protego", ward_effect, damage=0, cooldown=3,
          description="Blocks the next enemy attack completely.", color=WARD_BLUE),
    Spell("Mend", "episkey", mend_effect, damage=25, cooldown=3,
          description="Restores 25 HP.", color=GREEN),
    Spell("Soul Drain", "exhaurio", drain_effect, damage=20, cooldown=2,
          description="Steals life: damage, and heal half of it.", color=SOUL),
]


def find_spell(typed):
    for spell in grimoire:
        if spell.incantation == typed:
            return spell
    return None


# -------------------------------------------------------------------------
# LOAD ASSETS (Fallback to simple shapes if files aren't found)
# -------------------------------------------------------------------------
def load_image_safely(path, scale=1):
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale != 1:
            w, h = img.get_size()
            # scale (not smoothscale) keeps pixel art crisp
            img = pygame.transform.scale(img, (int(w * scale), int(h * scale)))
        return img
    except Exception:
        return None


def cut_frames(sheet, rects):
    """Cut frames out of a spritesheet, one pygame.Rect per frame (see class 11)."""
    return [sheet.subsurface(pygame.Rect(r)).copy() for r in rects]


def feet_position(frame):
    """(x, y) of the middle of the character's feet inside a frame.

    Uses the bottom strip of visible pixels, so antlers or a raised arm
    don't pull the anchor sideways the way the image center would.
    """
    body = frame.get_bounding_rect()
    strip_h = max(1, body.height // 12)
    feet = frame.subsurface((0, body.bottom - strip_h, frame.get_width(), strip_h)).get_bounding_rect()
    return feet.centerx, body.bottom


def align_by_feet(frames):
    """Put every frame on a same-size canvas with the feet at the bottom-center.

    After this, get_rect(midbottom=...) places the FEET exactly on the spot,
    for every frame, so the animation doesn't slide or hop.
    """
    anchors = [feet_position(f) for f in frames]
    half = max(max(fx, f.get_width() - fx) for f, (fx, _) in zip(frames, anchors))
    height = max(bottom for _, bottom in anchors)
    aligned = []
    for f, (fx, bottom) in zip(frames, anchors):
        canvas = pygame.Surface((half * 2, height), pygame.SRCALPHA)
        canvas.blit(f, (half - fx, height - bottom))
        aligned.append(canvas)
    return aligned


def crop_to_content(frames):
    """Trim the empty transparent border around a set of frames.

    The SAME box is used for every frame, so the animation does not jitter.
    This is what lets midbottom put the character's real feet on the ground,
    instead of the bottom of an image with empty space under it.
    """
    box = frames[0].get_bounding_rect()
    for frame in frames[1:]:
        box.union_ip(frame.get_bounding_rect())
    if box.width == 0 or box.height == 0:
        return frames
    return [frame.subsurface(box).copy() for frame in frames]


def scale_frames(frames, factor, smooth=False):
    # scale keeps pixel art crisp; smoothscale looks better when SHRINKING
    # a large painted image like the enemy sheets
    scale = pygame.transform.smoothscale if smooth else pygame.transform.scale
    return [scale(f, (round(f.get_width() * factor), round(f.get_height() * factor)))
            for f in frames]


def outlined(frames, color, thickness=2):
    """Add a soft colored outline around each frame (class 11: masks).

    A mask of the opaque pixels is turned into a one-color silhouette, which
    is drawn 8 times around the sprite before the sprite itself.
    """
    result = []
    for frame in frames:
        silhouette = pygame.mask.from_surface(frame).to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
        canvas = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
        t = thickness
        for dx, dy in ((-t, 0), (t, 0), (0, -t), (0, t), (-t, -t), (t, t), (-t, t), (t, -t)):
            canvas.blit(silhouette, (dx, dy))
        canvas.blit(frame, (0, 0))
        result.append(canvas)
    return result


def body_rect(frame, feet):
    """Screen rectangle around the visible pixels of a frame standing at feet."""
    placed = frame.get_rect(midbottom=feet)
    return frame.get_bounding_rect().move(placed.topleft)


def tinted(frames, color, flag):
    """Copies of the frames with a color added or multiplied (hit flash, frost)."""
    result = []
    for frame in frames:
        copy = frame.copy()
        copy.fill(color, special_flags=flag)
        result.append(copy)
    return result


def make_placeholder_player():
    surf = pygame.Surface((20, 32), pygame.SRCALPHA)
    pygame.draw.rect(surf, (60, 90, 170), (5, 12, 10, 14))      # coat
    pygame.draw.circle(surf, (235, 205, 170), (10, 8), 6)        # head
    pygame.draw.ellipse(surf, (70, 45, 30), (4, 1, 12, 6))        # hair
    pygame.draw.rect(surf, (40, 40, 60), (5, 26, 4, 6))          # legs
    pygame.draw.rect(surf, (40, 40, 60), (11, 26, 4, 6))
    return [surf, surf]


def make_placeholder_enemy():
    frames = []
    for glow in (200, 255):
        surf = pygame.Surface((90, 84), pygame.SRCALPHA)
        body = (70, 45, 90)
        pygame.draw.ellipse(surf, body, (10, 34, 60, 30))          # body
        for x in (18, 28, 52, 62):
            pygame.draw.rect(surf, body, (x, 58, 5, 26))            # legs
        pygame.draw.polygon(surf, body, [(60, 40), (72, 18), (80, 24), (70, 46)])  # neck
        pygame.draw.ellipse(surf, body, (68, 12, 18, 12))           # head
        pygame.draw.line(surf, body, (74, 14), (66, 2), 2)          # antlers
        pygame.draw.line(surf, body, (80, 14), (88, 2), 2)
        pygame.draw.line(surf, (90, 70, 40), (84, 22), (84, 34), 1)
        pygame.draw.circle(surf, (glow, glow - 40, 60), (84, 38), 5)  # lantern
        frames.append(surf)
    return frames


# Load Player & Enemy graphics based on Milestone 1 references
player_frames = []
for name in ("child_east1.png", "child_east2.png"):
    img = load_image_safely(asset_path("Sprites", "MC (simplified)", name))
    if img:
        player_frames.append(img)
if len(player_frames) < 2:
    player_frames = make_placeholder_player()
player_frames = scale_frames(align_by_feet(crop_to_content(player_frames)), PLAYER_SCALE)

enemy_sheet = load_image_safely(STAG_SHEET)
if enemy_sheet:
    idle = cut_frames(enemy_sheet, STAG_IDLE_RECTS)
    attack = cut_frames(enemy_sheet, STAG_ATTACK_RECTS)
else:
    idle = make_placeholder_enemy()
    attack = idle
if ENEMY_FACES_RIGHT and enemy_sheet:
    idle = [pygame.transform.flip(f, True, False) for f in idle]
    attack = [pygame.transform.flip(f, True, False) for f in attack]
# Align idle and attack frames together so they share one feet position
aligned = align_by_feet(idle + attack)
factor = ENEMY_TARGET_HEIGHT / aligned[0].get_bounding_rect().height
aligned = scale_frames(aligned, factor, smooth=enemy_sheet is not None)
# The stag's dark colors blend into the dark forest, so give it a pale rim
aligned = outlined(aligned, (215, 190, 255, 70))
enemy_frames = aligned[:len(idle)]
enemy_attack_frames = aligned[len(idle):]
enemy_hit_frames = tinted(enemy_frames, (70, 60, 60), pygame.BLEND_RGB_ADD)
enemy_frost_frames = tinted(enemy_frames, (150, 200, 255), pygame.BLEND_RGB_MULT)

# Images are drawn by their feet (midbottom). These rects are the visible
# bodies on screen - used for health bars, damage numbers and shadows.
player_rect = body_rect(player_frames[0], PLAYER_FEET)
enemy_rect = body_rect(enemy_frames[0], ENEMY_FEET)

scroll_img = load_image_safely(os.path.join(BASE_DIR, "Scroll.png"))  # Optional spell banner background
if scroll_img:
    scroll_img = pygame.transform.scale(scroll_img, GRIMOIRE_RECT.size)


# --- Background: the forest parallax from scene.py if its art is there ----
def build_fallback_background():
    """A dark-woods backdrop drawn with shapes, used when the scene art is missing."""
    bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    top, bottom = (10, 8, 22), (44, 30, 58)
    for y in range(GROUND_Y):
        t = y / GROUND_Y
        color = [int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)]
        pygame.draw.line(bg, color, (0, y), (SCREEN_WIDTH, y))
    pygame.draw.circle(bg, (200, 195, 170), (690, 95), 28)          # moon
    pygame.draw.circle(bg, (top[0] + 6, top[1] + 4, top[2] + 10), (702, 88), 24)  # crescent
    rng = random.Random(7)  # fixed seed: the same forest every time
    for layer_color, height in (((30, 22, 44), 170), ((20, 15, 30), 120)):
        x = -20
        while x < SCREEN_WIDTH + 20:
            w = rng.randint(40, 80)
            h = rng.randint(height - 50, height + 40)
            pygame.draw.polygon(bg, layer_color, [(x, GROUND_Y), (x + w // 2, GROUND_Y - h), (x + w, GROUND_Y)])
            x += w - rng.randint(5, 20)
    pygame.draw.rect(bg, (16, 12, 20), (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
    pygame.draw.line(bg, (60, 48, 70), (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)
    return bg


def build_fog():
    fog = pygame.Surface((SCREEN_WIDTH, 120), pygame.SRCALPHA)
    rng = random.Random(3)
    for _ in range(14):
        w = rng.randint(120, 260)
        x = rng.randint(-40, SCREEN_WIDTH - 40)
        pygame.draw.ellipse(fog, (150, 140, 180, 18), (x, rng.randint(30, 80), w, 40))
    return fog


try:
    from scene import ParallaxBackground
    background = ParallaxBackground(SCREEN_HEIGHT)
except Exception as e:
    print(f"Scene art not found, using drawn background ({e})")
    background = None
fallback_bg = build_fallback_background()
fog = build_fog()
fog_x = 0.0

# Shared see-through surfaces (built once, reused every frame)
overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
overlay.fill((0, 0, 0, 160))
scene_dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
scene_dim.fill((6, 2, 14, 80))  # darkens the scene a little so characters and UI stand out
hurt_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
hurt_overlay.fill((160, 0, 20, 90))


# -------------------------------------------------------------------------
# EFFECTS: floating damage numbers and sparks (like Asteroid Blaster II)
# -------------------------------------------------------------------------
class FloatingText:
    def __init__(self, text, color, pos):
        # Draw the text twice: a dark copy 2px down-right acts as a shadow
        front = font_med.render(text, True, color)
        back = font_med.render(text, True, BLACK)
        self.image = pygame.Surface((front.get_width() + 2, front.get_height() + 2), pygame.SRCALPHA)
        self.image.blit(back, (2, 2))
        self.image.blit(front, (0, 0))
        self.x, self.y = pos[0], pos[1] + 40  # start on the body, then float up
        self.age = 0.0
        self.life = 1.0

    def update(self, dt):
        self.age += dt
        self.y -= 40 * dt
        return self.age < self.life

    def draw(self, surface):
        self.image.set_alpha(int(255 * (1 - self.age / self.life)))
        surface.blit(self.image, self.image.get_rect(center=(round(self.x), round(self.y))))


class Particle:
    def __init__(self, pos, color):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 220)
        self.x, self.y = pos
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.color = color
        self.age = 0.0
        self.life = random.uniform(0.3, 0.7)
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= math.exp(-3 * dt)
        self.vy *= math.exp(-3 * dt)
        return self.age < self.life

    def draw(self, surface):
        t = self.age / self.life
        self.image.fill((*self.color, int(255 * (1 - t))))
        surface.blit(self.image, (round(self.x), round(self.y)))


popups = []
particles = []


def burst(pos, color, count):
    for _ in range(count):
        particles.append(Particle(pos, color))


# -------------------------------------------------------------------------
# COMBAT STATE
# -------------------------------------------------------------------------
def new_combat_state():
    return {
        'enemy_hp': ENEMY_MAX_HP,
        'enemy_max_hp': ENEMY_MAX_HP,
        'player_hp': PLAYER_MAX_HP,
        'player_max_hp': PLAYER_MAX_HP,
        'current_spell': baseline_spell,
        'selected': 0,                 # index into grimoire of the highlighted spell
        'typed_buffer': "",
        'message': "A wild horror emerges from the dark woods! Cast your spell!",
        'phase': "player",             # "player", "enemy", "won" or "lost"
        'turn': 1,
        'enemy_timer': 0.0,
        'enemy_burn': 0,               # turns of burning left
        'enemy_frozen': False,
        'player_ward': False,
        # visual-only values
        'enemy_hp_shown': ENEMY_MAX_HP,   # the pale "ghost" part of the HP bar
        'player_hp_shown': PLAYER_MAX_HP,
        'enemy_shake': 0.0,
        'player_shake': 0.0,
        'hurt_flash': 0.0,
        'cast_pose': 0.0,
        'death_fade': 0.0,             # enemy fades out over 1 s when defeated
    }


def reset():
    global combat_state
    combat_state = new_combat_state()
    for spell in grimoire:
        spell.turns_left = 0
    popups.clear()
    particles.clear()


combat_state = new_combat_state()


def select_spell(index):
    combat_state['selected'] = index % len(grimoire)
    combat_state['current_spell'] = grimoire[combat_state['selected']]


def auto_switch(typed):
    """Typing the start of another spell's words switches to that spell."""
    if combat_state['current_spell'].incantation.startswith(typed):
        return
    for i, spell in enumerate(grimoire):
        if spell.incantation.startswith(typed):
            select_spell(i)
            return


def tick_cooldowns():
    for spell in grimoire:
        if spell.turns_left > 0:
            spell.turns_left -= 1


def player_cast(typed):
    """Enter was pressed: cast whichever grimoire spell was typed."""
    state = combat_state
    spell = find_spell(typed)
    state['typed_buffer'] = ""

    if spell is None:
        tick_cooldowns()
        state['message'] = "Incantation fizzled! The stag seizes the moment..."
        end_player_turn()
        return

    if not spell.is_ready():
        # No turn lost: the player just picked a spell that is recharging.
        state['message'] = f"{spell.name} is still recharging ({spell.turns_left} more turn(s))."
        return

    tick_cooldowns()
    select_spell(grimoire.index(spell))  # typing a spell's words also switches to it
    spell.cast(state)
    state['cast_pose'] = 0.35

    if state['enemy_hp'] <= 0:
        win()
    else:
        end_player_turn()


def end_player_turn():
    combat_state['phase'] = "enemy"
    combat_state['enemy_timer'] = ENEMY_TURN_DELAY


def win():
    combat_state['phase'] = "won"
    combat_state['death_fade'] = 1.0
    combat_state['message'] = f"The {ENEMY_NAME} collapses into the dark."


def enemy_turn():
    state = combat_state
    notes = []

    if state['enemy_burn'] > 0:
        state['enemy_burn'] -= 1
        damage_enemy(state, BURN_DAMAGE, EMBER)
        notes.append(f"Flames lick the stag for {BURN_DAMAGE}.")
        if state['enemy_hp'] <= 0:
            win()
            return

    if state['enemy_frozen']:
        state['enemy_frozen'] = False
        notes.append("The stag is frozen solid and cannot attack!")
    else:
        hit = random.randint(*ENEMY_ATTACK)
        if state['player_ward']:
            state['player_ward'] = False
            popups.append(FloatingText("BLOCKED", WARD_BLUE, player_rect.midtop))
            burst(player_rect.center, WARD_BLUE, 18)
            notes.append(f"The stag charges, but your ward absorbs all {hit} damage!")
        else:
            state['player_hp'] = max(0, state['player_hp'] - hit)
            state['player_shake'] = 0.3
            state['hurt_flash'] = 0.25
            popups.append(FloatingText(f"-{hit}", RED, player_rect.midtop))
            notes.append(f"The stag's lantern flares! You take {hit} damage.")

    state['message'] = " ".join(notes)
    if state['player_hp'] <= 0:
        state['phase'] = "lost"
        state['message'] = "The lantern's light swallows you whole..."
    else:
        state['phase'] = "player"
        state['turn'] += 1


# -------------------------------------------------------------------------
# DRAWING HELPERS (UI)
# -------------------------------------------------------------------------
def draw_text(font, text, color, **position):
    image = font.render(text, True, color)
    rect = image.get_rect(**position)
    screen.blit(image, rect)
    return rect


def wrap_text(font, text, max_width):
    words = text.split(" ")
    lines, line = [], ""
    for word in words:
        test = word if line == "" else line + " " + word
        if font.size(test)[0] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def draw_panel(rect, fill=PANEL_FILL, edge=PANEL_EDGE, radius=10):
    """A rounded, see-through box with a thin gold edge."""
    box = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(box, fill, box.get_rect(), border_radius=radius)
    pygame.draw.rect(box, edge, box.get_rect(), 2, border_radius=radius)
    screen.blit(box, rect.topleft)


def draw_bar(x, y, w, h, value, shown, maximum, color):
    """HP bar with a pale 'ghost' segment that drains after a hit."""
    pygame.draw.rect(screen, (30, 20, 30), (x, y, w, h), border_radius=4)
    ghost_w = int(w * max(shown, 0) / maximum)
    pygame.draw.rect(screen, (240, 230, 200), (x, y, ghost_w, h), border_radius=4)
    fill_w = int(w * max(value, 0) / maximum)
    if fill_w > 0:
        pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
    pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2, border_radius=4)


def draw_badge(text, color, pos):
    """A small rounded tag like 'BURN 2' or 'WARD'. Returns its width."""
    image = font_tiny.render(text, True, color)
    rect = image.get_rect(topleft=pos).inflate(10, 4)
    rect.topleft = pos
    pygame.draw.rect(screen, (20, 14, 28), rect, border_radius=6)
    pygame.draw.rect(screen, color, rect, 1, border_radius=6)
    screen.blit(image, image.get_rect(center=rect.center))
    return rect.width


def draw_nameplate(name, anchor_rect, hp, shown, max_hp, color, badges):
    """Name, HP bar and status badges, centered above a character."""
    width = 180
    x = anchor_rect.centerx - width // 2
    x = max(8, min(SCREEN_WIDTH - width - 8, x))  # keep it on screen
    y = max(BANNER_RECT.bottom + 26, anchor_rect.top - 30)
    # dark backing plate so the text stays readable over the busy forest
    plate = pygame.Rect(x - 8, y - 24, width + 16, 44 if not badges else 62)
    draw_panel(plate, fill=(14, 10, 22, 170), edge=(0, 0, 0, 0), radius=8)
    name_rect = draw_text(font_small_bold, name, WHITE, bottomleft=(x, y - 2))
    draw_text(font_tiny, f"{max(hp, 0)}/{max_hp}", LIGHT_GRAY, bottomright=(x + width, name_rect.bottom - 1))
    draw_bar(x, y, width, 12, hp, shown, max_hp, color)
    bx = x
    for text, badge_color in badges:
        bx += draw_badge(text, badge_color, (bx, y + 16)) + 4


def draw_shadow(rect):
    shadow = pygame.Surface((rect.width + 20, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
    screen.blit(shadow, shadow.get_rect(center=(rect.centerx, GROUND_Y - 2)))


def draw_banner():
    draw_panel(BANNER_RECT, fill=(14, 10, 22, 200))
    if combat_state['phase'] == "enemy":
        label, color = "ENEMY TURN", RED
    elif combat_state['phase'] == "player":
        label, color = f"TURN {combat_state['turn']}", GOLD
    else:
        label, color = "", GOLD
    lines = wrap_text(font_small, combat_state['message'], BANNER_RECT.width - 30)[:2]
    if len(lines) == 1:
        draw_text(font_small, lines[0], PARCHMENT, center=BANNER_RECT.center)
    else:
        draw_text(font_small, lines[0], PARCHMENT, center=(BANNER_RECT.centerx, BANNER_RECT.centery - 10))
        draw_text(font_small, lines[1], PARCHMENT, center=(BANNER_RECT.centerx, BANNER_RECT.centery + 10))
    if label:
        tag = font_tiny.render(label, True, color)
        tag_rect = tag.get_rect(midtop=(BANNER_RECT.centerx, BANNER_RECT.bottom - 1)).inflate(14, 4)
        pygame.draw.rect(screen, (14, 10, 22), tag_rect, border_radius=6)
        pygame.draw.rect(screen, color, tag_rect, 1, border_radius=6)
        screen.blit(tag, tag.get_rect(center=tag_rect.center))


def draw_incantation(target, typed, center_x, y):
    """Typing-of-the-Dead feedback: each letter turns green (right) or red (wrong)."""
    letters = [font_large.render(ch, True, WHITE) for ch in target]
    total = sum(img.get_width() for img in letters)
    x = center_x - total // 2
    for i, ch in enumerate(target):
        if i < len(typed):
            color = GREEN if typed[i] == ch else RED
        else:
            color = LIGHT_GRAY
        img = font_large.render(ch, True, color)
        screen.blit(img, (x, y))
        if i == len(typed) and combat_state['phase'] == "player":
            # blinking underline under the next letter to type
            if int(pygame.time.get_ticks() / 400) % 2 == 0:
                pygame.draw.line(screen, GOLD, (x, y + img.get_height()), (x + img.get_width() - 2, y + img.get_height()), 3)
        x += img.get_width()


def draw_typing_panel():
    state = combat_state
    spell = state['current_spell']
    r = TYPING_RECT
    draw_panel(r)

    # Spell name with a colored accent stripe
    pygame.draw.rect(screen, spell.color, (r.x + 14, r.y + 16, 5, 26), border_radius=2)
    draw_text(font_med, spell.name, WHITE, topleft=(r.x + 28, r.y + 14))
    if spell.damage and spell.effect_func not in (ward_effect, mend_effect):
        draw_text(font_small, f"DMG {spell.damage}", LIGHT_GRAY, topright=(r.right - 16, r.y + 20))
    draw_text(font_tiny, spell.description, LIGHT_GRAY, topleft=(r.x + 28, r.y + 44))

    # The word to type, letter by letter
    draw_incantation(spell.incantation, state['typed_buffer'], r.centerx, r.y + 68)

    # Input box
    box = pygame.Rect(r.x + 16, r.y + 112, r.width - 32, 34)
    pygame.draw.rect(screen, (10, 8, 16), box, border_radius=6)
    edge = GOLD if state['phase'] == "player" else GRAY
    pygame.draw.rect(screen, edge, box, 2, border_radius=6)
    if state['phase'] == "player":
        cursor = "_" if int(pygame.time.get_ticks() / 400) % 2 == 0 else " "
        draw_text(font_med, "> " + state['typed_buffer'] + cursor, WHITE, midleft=(box.x + 10, box.centery))
    else:
        draw_text(font_small, "...", GRAY, midleft=(box.x + 10, box.centery))

    draw_text(font_tiny, "Enter: cast   Tab / Up / Down / 1-6: switch spell", GRAY,
              midbottom=(r.centerx, r.bottom - 8))


def draw_grimoire():
    r = GRIMOIRE_RECT
    if scroll_img:
        screen.blit(scroll_img, r.topleft)
    else:
        draw_panel(r)
    draw_text(font_small_bold, "GRIMOIRE", GOLD, topleft=(r.x + 14, r.y + 10))
    draw_text(font_tiny, f"{len(grimoire)} spells", GRAY, topright=(r.right - 14, r.y + 13))

    row_h = 24
    top = r.y + 36
    for i, spell in enumerate(grimoire):
        row = pygame.Rect(r.x + 8, top + i * row_h, r.width - 16, row_h - 2)
        selected = i == combat_state['selected']
        if selected:
            pygame.draw.rect(screen, (60, 45, 85), row, border_radius=5)
            pygame.draw.rect(screen, spell.color, row, 1, border_radius=5)
        name_color = WHITE if spell.is_ready() else GRAY
        draw_text(font_tiny, str(i + 1), GRAY, midleft=(row.x + 6, row.centery))
        pygame.draw.circle(screen, spell.color if spell.is_ready() else GRAY, (row.x + 24, row.centery), 4)
        draw_text(font_small if not selected else font_small_bold, spell.name, name_color,
                  midleft=(row.x + 34, row.centery))
        if spell.is_ready():
            draw_text(font_tiny, spell.incantation, LIGHT_GRAY, midright=(row.right - 6, row.centery))
        else:
            draw_text(font_tiny, f"wait {spell.turns_left}", RED, midright=(row.right - 6, row.centery))


def draw_end_screen():
    screen.blit(overlay, (0, 0))
    if combat_state['phase'] == "won":
        title, color = "ENEMY DEFEATED", GREEN
    else:
        title, color = "YOU HAVE FALLEN", RED
    box = pygame.Rect(0, 0, 460, 170)
    box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)
    draw_panel(box, edge=color)
    draw_text(font_large, title, color, center=(box.centerx, box.y + 45))
    for i, line in enumerate(wrap_text(font_small, combat_state['message'], box.width - 40)[:2]):
        draw_text(font_small, line, PARCHMENT, center=(box.centerx, box.y + 88 + i * 22))
    draw_text(font_small, "R: fight again     Esc: quit", LIGHT_GRAY, center=(box.centerx, box.bottom - 24))


# -------------------------------------------------------------------------
# GAME LOOP
# -------------------------------------------------------------------------
enemy_anim_time = 0.0
enemy_frame = 0

running = True
while running:
    dt = min(clock.tick(FPS) / 1000, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if combat_state['phase'] in ("won", "lost"):
                if event.key == pygame.K_r:
                    reset()
                continue

            # Switching spells works any time (even during the enemy's turn)
            if event.key == pygame.K_TAB:
                step = -1 if event.mod & pygame.KMOD_SHIFT else 1
                select_spell(combat_state['selected'] + step)
                continue
            if event.key == pygame.K_UP:
                select_spell(combat_state['selected'] - 1)
                continue
            if event.key == pygame.K_DOWN:
                select_spell(combat_state['selected'] + 1)
                continue
            if event.unicode in "123456789" and event.unicode != "" and int(event.unicode) <= len(grimoire):
                select_spell(int(event.unicode) - 1)
                continue

            if combat_state['phase'] != "player":
                continue  # no typing while the enemy is acting

            if event.key == pygame.K_BACKSPACE:
                combat_state['typed_buffer'] = combat_state['typed_buffer'][:-1]
            elif event.key == pygame.K_RETURN:
                # Check if typed text matches any spell incantation in the grimoire
                player_cast(combat_state['typed_buffer'].strip().lower())
            else:
                # Append typed letter (incantations are letters only)
                char = event.unicode.lower()
                if len(char) == 1 and char.isalpha() and len(combat_state['typed_buffer']) < 16:
                    combat_state['typed_buffer'] += char
                    auto_switch(combat_state['typed_buffer'])

    # ---------- UPDATE ----------
    if combat_state['phase'] == "enemy":
        combat_state['enemy_timer'] -= dt
        if combat_state['enemy_timer'] <= 0:
            enemy_turn()

    # Ghost HP bars slide down toward the real HP
    for key in ('enemy', 'player'):
        real, shown = combat_state[key + '_hp'], combat_state[key + '_hp_shown']
        if shown > real:
            combat_state[key + '_hp_shown'] = max(real, shown - 60 * dt)
        else:
            combat_state[key + '_hp_shown'] = real

    for key in ('enemy_shake', 'player_shake', 'hurt_flash', 'cast_pose', 'death_fade'):
        combat_state[key] = max(0.0, combat_state[key] - dt)

    enemy_anim_time += dt
    if enemy_anim_time >= ENEMY_FRAME_TIME:
        enemy_anim_time -= ENEMY_FRAME_TIME
        enemy_frame = (enemy_frame + 1) % len(enemy_frames)

    if combat_state['enemy_burn'] > 0 and random.random() < 0.25:
        particles.append(Particle((random.randint(enemy_rect.left, enemy_rect.right), enemy_rect.centery), EMBER))

    popups = [p for p in popups if p.update(dt)]
    particles = [p for p in particles if p.update(dt)]

    if background:
        background.update(0)  # combat is stationary; only drifting layers move
    fog_x = (fog_x - 12 * dt) % SCREEN_WIDTH

    # ---------- DRAW ----------
    # Background (Dark cursed fantasy theme)
    if background:
        screen.fill((14, 10, 22))
        background.draw(screen, GROUND_Y - SCENE_PATH_Y)  # shift up: path on GROUND_Y
        screen.blit(scene_dim, (0, 0))
        # the scene image ends above the bottom of the window; cover that edge
        screen.fill((14, 10, 22), (0, PANEL_RECT.top, SCREEN_WIDTH, SCREEN_HEIGHT - PANEL_RECT.top))
    else:
        screen.blit(fallback_bg, (0, 0))
        screen.blit(fog, (fog_x - SCREEN_WIDTH, GROUND_Y - 110))
        screen.blit(fog, (fog_x, GROUND_Y - 110))

    # Render Characters (shadow first, then the sprite standing on it)
    draw_shadow(player_rect)
    if combat_state['phase'] != "won":
        draw_shadow(enemy_rect)

    offset = 0
    if combat_state['player_shake'] > 0:
        offset = random.randint(-4, 4)
    player_img = player_frames[1] if combat_state['cast_pose'] > 0 else player_frames[0]
    if combat_state['phase'] != "lost":
        screen.blit(player_img, player_img.get_rect(midbottom=(PLAYER_FEET[0] + offset, GROUND_Y)))

    if combat_state['player_ward']:
        pulse = 4 * math.sin(pygame.time.get_ticks() / 200)
        ring = pygame.Surface((160, 160), pygame.SRCALPHA)
        pygame.draw.circle(ring, (*WARD_BLUE, 40), (80, 80), int(64 + pulse))
        pygame.draw.circle(ring, (*WARD_BLUE, 160), (80, 80), int(64 + pulse), 2)
        screen.blit(ring, ring.get_rect(center=player_rect.center))

    if combat_state['phase'] != "won" or combat_state['death_fade'] > 0:
        offset = 0
        if combat_state['enemy_shake'] > 0:
            offset = random.randint(-6, 6)
        timer = combat_state['enemy_timer']
        attacking = (combat_state['phase'] == "enemy" and not combat_state['enemy_frozen']
                     and timer < ATTACK_ANIM_TIME)
        if attacking:
            # progress 0 -> 1 through the attack row; the hit lands on the last frame
            progress = (ATTACK_ANIM_TIME - timer) / ATTACK_ANIM_TIME
            enemy_img = enemy_attack_frames[min(len(enemy_attack_frames) - 1,
                                                int(progress * len(enemy_attack_frames)))]
        elif combat_state['enemy_shake'] > 0.15:
            enemy_img = enemy_hit_frames[enemy_frame]
        elif combat_state['enemy_frozen']:
            enemy_img = enemy_frost_frames[0]  # frozen = no animation
        else:
            enemy_img = enemy_frames[enemy_frame]
        if combat_state['phase'] == "won":
            enemy_img = enemy_img.copy()
            enemy_img.set_alpha(int(255 * combat_state['death_fade']))
        screen.blit(enemy_img, enemy_img.get_rect(midbottom=(ENEMY_FEET[0] + offset, GROUND_Y)))

    for p in particles:
        p.draw(screen)

    # Render Health Bars above each character
    enemy_badges = []
    if combat_state['enemy_burn'] > 0:
        enemy_badges.append((f"BURN {combat_state['enemy_burn']}", EMBER))
    if combat_state['enemy_frozen']:
        enemy_badges.append(("FROZEN", FROST))
    if combat_state['phase'] != "won":
        draw_nameplate(ENEMY_NAME, enemy_rect, combat_state['enemy_hp'], combat_state['enemy_hp_shown'],
                       combat_state['enemy_max_hp'], RED, enemy_badges)
    player_badges = [("WARD", WARD_BLUE)] if combat_state['player_ward'] else []
    draw_nameplate(PLAYER_NAME, player_rect, combat_state['player_hp'], combat_state['player_hp_shown'],
                   combat_state['player_max_hp'], GREEN, player_badges)

    for p in popups:
        p.draw(screen)

    # -------------------------------------------------------------------------
    # TYPING OF THE DEAD
    # -------------------------------------------------------------------------
    draw_banner()
    draw_typing_panel()
    draw_grimoire()

    if combat_state['hurt_flash'] > 0:
        screen.blit(hurt_overlay, (0, 0))

    if combat_state['phase'] in ("won", "lost"):
        draw_end_screen()

    pygame.display.flip()
