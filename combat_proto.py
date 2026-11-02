import os
import sys
import math
import random
import pygame

import sprites
import enemies

pygame.init()

# Screen Configuration
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
# Reuse the window if main.py already opened one; otherwise open our own.
screen = pygame.display.get_surface() or pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

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
ENEMY_X = 610                    # enemy feet x; its feet y is GROUND_Y minus its 'hover'

# The dirt path in the forest scene art sits at y = 476 (when the scene is
# 600 px tall). The scene is drawn shifted up so the path lines up with
# GROUND_Y and isn't hidden behind the bottom panel.
SCENE_PATH_Y = 476

PLAYER_SCALE = 3                 # same pixel-art scale as main.py

BANNER_RECT = pygame.Rect(150, 12, 500, 54)      # combat log at the top
PANEL_RECT = pygame.Rect(16, 412, 768, 180)      # whole bottom panel
TYPING_RECT = pygame.Rect(16, 412, 500, 180)     # left: the spell you are typing
GRIMOIRE_RECT = pygame.Rect(526, 412, 258, 180)  # right: list of collected spells

ENEMY_FRAME_TIME = 0.18          # seconds each idle frame is shown
ATTACK_ANIM_TIME = 0.5           # the attack row plays during the last 0.5 s of the enemy's turn
HURT_ANIM_TIME = 0.4             # the hurt row plays for 0.4 s after the enemy is hit

# Fight intro: nothing you type counts until it finishes, so keys still held
# or pressed while walking into the enemy can't end up in the spell box.
INTRO_TIME = 2.6                 # seconds from the start of the fight until your first turn
INTRO_FADE = 0.5                 # fade in from black
INTRO_SLIDE = 0.9                # both fighters step into place
READY_TIME = 0.7                 # "Ready..." shows for the last 0.7 s of the intro
CAST_FLASH_TIME = 0.6            # "CAST!" shows when your first turn starts
END_INPUT_DELAY = 1.0            # the win/lose box ignores keys for 1 s (no accidental skip)

# Combat tuning (each enemy's own HP and attack live in enemies.py)
PLAYER_NAME = "Wanderer"         # placeholder until the name-entry screen exists
PLAYER_MAX_HP = 100
ENEMY_TURN_DELAY = 0.9           # pause so the player can read what happened
BURN_DAMAGE = 6

# -------------------------------------------------------------------------
# CRITICAL HITS FROM TYPING SPEED
# Typing speed is measured in words per minute (WPM), where a "word" is
# 5 letters, timed from the first letter typed until Enter is pressed.
# The faster you type the incantation, the more likely a critical hit.
# -------------------------------------------------------------------------
CRIT_TABLE = [      # (lowest WPM for this tier, crit chance)
    (121, 0.50),    # 121-200 WPM (and anything faster)
    (101, 0.33),    # 101-120 WPM
    (81, 0.25),     # 81-100 WPM
    (61, 0.15),     # 61-80 WPM
    (0, 0.05),      # 60 WPM and below
]
CRIT_MULTIPLIER = 1.5            # a critical hit deals 1.5x damage


def typing_wpm(letters, start_ms, end_ms):
    """Words per minute for typing `letters` letters between two get_ticks() times."""
    minutes = max(end_ms - start_ms, 1) / 60000
    return round((letters / 5) / minutes)


def crit_chance(wpm):
    for lowest_wpm, chance in CRIT_TABLE:
        if wpm >= lowest_wpm:
            return chance
    return CRIT_TABLE[-1][1]


# -------------------------------------------------------------------------
# MODULAR SPELL SCRIPTING
# -------------------------------------------------------------------------
class Spell:
    def __init__(self, name, incantation, effect_func, damage=25,
                 cooldown=0, description="", color=GOLD, can_crit=True):
        self.name = name
        self.incantation = incantation.lower()
        self.effect_func = effect_func
        self.damage = damage
        self.cooldown = cooldown         # how many turns you must wait after casting
        self.description = description   # one line shown in the typing panel
        self.color = color               # used for the card accent and hit effects
        self.can_crit = can_crit         # False for spells that don't deal damage
        self.turns_left = 0              # 0 = ready to cast

    def is_ready(self):
        return self.turns_left <= 0

    def cast(self, combat_state):
        print(f" Casting Spell: {self.name} ('{self.incantation}')")
        self.turns_left = self.cooldown
        if self.effect_func:
            self.effect_func(combat_state)


# --- helpers the spell effects share (damage numbers, sparks, shake) ------
def spell_damage(state):
    """The current spell's damage, multiplied if this cast was a critical hit."""
    damage = state['current_spell'].damage
    if state['crit']:
        damage = round(damage * CRIT_MULTIPLIER)
    return damage


def damage_enemy(state, amount, color, crit=False):
    state['enemy_hp'] = max(0, state['enemy_hp'] - amount)
    state['enemy_shake'] = 0.3
    state['enemy_hurt'] = HURT_ANIM_TIME
    if crit:
        popups.append(FloatingText(f"CRIT -{amount}", GOLD, enemy_rect.midtop, font_large))
        burst(enemy_rect.center, GOLD, 30)
    else:
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
    damage = spell_damage(state)
    damage_enemy(state, damage, GOLD, state['crit'])
    state['message'] = f"Spark struck the {enemy['short']} for {damage} damage!"


def ember_effect(state):
    damage = spell_damage(state)
    damage_enemy(state, damage, EMBER, state['crit'])
    state['enemy_burn'] = 3
    state['message'] = f"Ember Lash sears for {damage}! The {enemy['short']} is burning."


def frost_effect(state):
    damage = spell_damage(state)
    damage_enemy(state, damage, FROST, state['crit'])
    state['enemy_frozen'] = True
    state['message'] = f"Frost Bind deals {damage} and freezes the {enemy['short']} in place!"


def ward_effect(state):
    state['player_ward'] = True
    burst(player_rect.center, WARD_BLUE, 16)
    state['message'] = "A ward shimmers around you. The next attack will be blocked."


def mend_effect(state):
    healed = heal_player(state, state['current_spell'].damage)
    state['message'] = f"Mend knits your wounds. You recover {healed} HP."


def drain_effect(state):
    damage = spell_damage(state)
    damage_enemy(state, damage, SOUL, state['crit'])
    healed = heal_player(state, damage // 2)
    state['message'] = f"Soul Drain tears {damage} from the {enemy['short']} and returns {healed} HP."


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
          description="Blocks the next enemy attack completely.", color=WARD_BLUE, can_crit=False),
    Spell("Mend", "episkey", mend_effect, damage=25, cooldown=3,
          description="Restores 25 HP.", color=GREEN, can_crit=False),
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
def make_placeholder_player():
    surf = pygame.Surface((20, 32), pygame.SRCALPHA)
    pygame.draw.rect(surf, (60, 90, 170), (5, 12, 10, 14))      # coat
    pygame.draw.circle(surf, (235, 205, 170), (10, 8), 6)        # head
    pygame.draw.ellipse(surf, (70, 45, 30), (4, 1, 12, 6))        # hair
    pygame.draw.rect(surf, (40, 40, 60), (5, 26, 4, 6))          # legs
    pygame.draw.rect(surf, (40, 40, 60), (11, 26, 4, 6))
    return [surf, surf]


# Load Player graphics based on Milestone 1 references
player_frames = []
for name in ("child_east1.png", "child_east2.png"):
    img = sprites.load_image_safely(asset_path("Sprites", "MC (simplified)", name))
    if img:
        player_frames.append(img)
if len(player_frames) < 2:
    player_frames = make_placeholder_player()
player_frames = sprites.scale_frames(sprites.align_by_feet(sprites.crop_to_content(player_frames)), PLAYER_SCALE)

# Images are drawn by their feet (midbottom). These rects are the visible
# bodies on screen - used for health bars, damage numbers and shadows.
player_rect = sprites.body_rect(player_frames[0], PLAYER_FEET)

# The enemy is chosen when a fight starts (see start_fight)
enemy = None              # the enemy's entry from enemies.ENEMIES
enemy_rows = None         # {'idle': [...], 'hurt': [...], 'attack': [...]}
enemy_frost_frames = None
enemy_feet = (ENEMY_X, GROUND_Y)
enemy_rect = None

scroll_img = sprites.load_image_safely(os.path.join(BASE_DIR, "Scroll.png"))  # Optional spell banner background
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
black = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))  # fades use set_alpha on this
black.fill((0, 0, 0))
hurt_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
hurt_overlay.fill((160, 0, 20, 90))


# -------------------------------------------------------------------------
# EFFECTS: floating damage numbers and sparks (like Asteroid Blaster II)
# -------------------------------------------------------------------------
class FloatingText:
    def __init__(self, text, color, pos, font=font_med):
        # Draw the text twice: a dark copy 2px down-right acts as a shadow
        front = font.render(text, True, color)
        back = font.render(text, True, BLACK)
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
def new_combat_state(player_hp=PLAYER_MAX_HP):
    return {
        'enemy_hp': enemy['max_hp'],
        'enemy_max_hp': enemy['max_hp'],
        'player_hp': player_hp,
        'player_max_hp': PLAYER_MAX_HP,
        'current_spell': baseline_spell,
        'selected': 0,                 # index into grimoire of the highlighted spell
        'typed_buffer': "",
        'typing_start': None,          # get_ticks() when the first letter was typed
        'last_wpm': None,              # speed of the last successful cast
        'crit': False,                 # is the spell being cast right now a critical hit?
        'message': f"The {enemy['name']} blocks your path...",
        'phase': "intro",              # "intro", "player", "enemy", "won" or "lost"
        'intro_time': 0.0,             # seconds since the fight started (for the intro)
        'cast_flash': 0.0,             # time left on the "CAST!" message
        'end_time': 0.0,               # seconds since the fight was won or lost
        'turn': 1,
        'enemy_timer': 0.0,
        'enemy_burn': 0,               # turns of burning left
        'enemy_frozen': False,
        'player_ward': False,
        # visual-only values
        'enemy_hp_shown': enemy['max_hp'],   # the pale "ghost" part of the HP bar
        'player_hp_shown': player_hp,
        'enemy_shake': 0.0,
        'enemy_hurt': 0.0,             # time left on the hurt animation
        'player_shake': 0.0,
        'hurt_flash': 0.0,
        'cast_pose': 0.0,
        'death_fade': 0.0,             # enemy fades out over 1 s when defeated
    }


combat_state = None


def start_fight(enemy_key, player_hp=PLAYER_MAX_HP):
    """Load the chosen enemy and reset everything for a fresh fight."""
    global enemy, enemy_rows, enemy_frost_frames, enemy_feet, enemy_rect, combat_state
    enemy = enemies.ENEMIES[enemy_key]
    enemy_rows = enemies.load_enemy_frames(enemy_key)
    enemy_frost_frames = sprites.tinted(enemy_rows['idle'], (150, 200, 255), pygame.BLEND_RGB_MULT)
    enemy_feet = (ENEMY_X, GROUND_Y - enemy['hover'])
    enemy_rect = sprites.body_rect(enemy_rows['idle'][0], enemy_feet)
    combat_state = new_combat_state(player_hp)
    for spell in grimoire:
        spell.turns_left = 0
    popups.clear()
    particles.clear()


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


def type_letter(char):
    state = combat_state
    if state['typed_buffer'] == "":
        state['typing_start'] = pygame.time.get_ticks()  # the clock starts on the first letter
    state['typed_buffer'] += char
    auto_switch(state['typed_buffer'])


def erase_letter():
    state = combat_state
    state['typed_buffer'] = state['typed_buffer'][:-1]
    if state['typed_buffer'] == "":
        state['typing_start'] = None


def live_wpm():
    """Typing speed so far, while the player is still typing (None if too early to tell)."""
    state = combat_state
    letters = len(state['typed_buffer'])
    if state['typing_start'] is None or letters < 2:
        return None
    # letters - 1 gaps between the first and the latest letter
    return typing_wpm(letters - 1, state['typing_start'], pygame.time.get_ticks())


def player_cast(typed):
    """Enter was pressed: cast whichever grimoire spell was typed."""
    state = combat_state
    spell = find_spell(typed)
    start = state['typing_start']
    state['typed_buffer'] = ""
    state['typing_start'] = None

    if spell is None:
        tick_cooldowns()
        state['message'] = f"Incantation fizzled! The {enemy['short']} seizes the moment..."
        end_player_turn()
        return

    if not spell.is_ready():
        # No turn lost: the player just picked a spell that is recharging.
        state['message'] = f"{spell.name} is still recharging ({spell.turns_left} more turn(s))."
        return

    # How fast was it typed? Faster typing = better chance of a critical hit.
    wpm = typing_wpm(len(typed), start, pygame.time.get_ticks())
    state['last_wpm'] = wpm
    state['crit'] = spell.can_crit and random.random() < crit_chance(wpm)

    tick_cooldowns()
    select_spell(grimoire.index(spell))  # typing a spell's words also switches to it
    spell.cast(state)
    state['cast_pose'] = 0.35
    if state['crit']:
        state['message'] = "CRITICAL! " + state['message']
    state['message'] += f" ({wpm} WPM)"
    state['crit'] = False

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
    combat_state['message'] = f"The {enemy['name']} collapses into the dark."


def enemy_turn():
    state = combat_state
    short = enemy['short']
    notes = []

    if state['enemy_burn'] > 0:
        state['enemy_burn'] -= 1
        damage_enemy(state, BURN_DAMAGE, EMBER)
        notes.append(f"Flames lick the {short} for {BURN_DAMAGE}.")
        if state['enemy_hp'] <= 0:
            win()
            return

    if state['enemy_frozen']:
        state['enemy_frozen'] = False
        notes.append(f"The {short} is frozen solid and cannot attack!")
    else:
        hit = random.randint(*enemy['attack'])
        if state['player_ward']:
            state['player_ward'] = False
            popups.append(FloatingText("BLOCKED", WARD_BLUE, player_rect.midtop))
            burst(player_rect.center, WARD_BLUE, 18)
            notes.append(f"The {short} attacks, but your ward absorbs all {hit} damage!")
        else:
            state['player_hp'] = max(0, state['player_hp'] - hit)
            state['player_shake'] = 0.3
            state['hurt_flash'] = 0.25
            popups.append(FloatingText(f"-{hit}", RED, player_rect.midtop))
            notes.append(f"{enemy['attack_text']} You take {hit} damage.")

    state['message'] = " ".join(notes)
    if state['player_hp'] <= 0:
        state['phase'] = "lost"
        state['message'] = f"The {enemy['name']} drags you into the dark..."
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
    hp_text = f"{max(hp, 0)}/{max_hp}"
    # at least 180 px, wider if a long name would run into the HP numbers
    width = max(180, font_small_bold.size(name)[0] + font_tiny.size(hp_text)[0] + 16)
    x = anchor_rect.centerx - width // 2
    x = max(8, min(SCREEN_WIDTH - width - 8, x))  # keep it on screen
    y = max(BANNER_RECT.bottom + 26, anchor_rect.top - 30)
    # dark backing plate so the text stays readable over the busy forest
    plate = pygame.Rect(x - 8, y - 24, width + 16, 44 if not badges else 62)
    draw_panel(plate, fill=(14, 10, 22, 170), edge=(0, 0, 0, 0), radius=8)
    name_rect = draw_text(font_small_bold, name, WHITE, bottomleft=(x, y - 2))
    draw_text(font_tiny, hp_text, LIGHT_GRAY, bottomright=(x + width, name_rect.bottom - 1))
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
    elif combat_state['phase'] == "intro":
        label, color = "GET READY", PARCHMENT
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


def draw_speed_meter(box):
    """Right side of the input box: typing speed and the crit chance it gives."""
    wpm = live_wpm()
    if wpm is not None:
        chance = crit_chance(wpm)
        color = GOLD if chance >= 0.33 else (PARCHMENT if chance >= 0.15 else LIGHT_GRAY)
        draw_text(font_tiny, f"{wpm} WPM  {round(chance * 100)}% crit", color,
                  midright=(box.right - 10, box.centery))
    elif combat_state['last_wpm'] is not None:
        draw_text(font_tiny, f"last cast {combat_state['last_wpm']} WPM", GRAY,
                  midright=(box.right - 10, box.centery))


def draw_typing_panel():
    state = combat_state
    spell = state['current_spell']
    r = TYPING_RECT
    draw_panel(r)

    # Spell name with a colored accent stripe
    pygame.draw.rect(screen, spell.color, (r.x + 14, r.y + 16, 5, 26), border_radius=2)
    draw_text(font_med, spell.name, WHITE, topleft=(r.x + 28, r.y + 14))
    if spell.can_crit:
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
    draw_speed_meter(box)

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


def draw_end_screen(standalone):
    screen.blit(overlay, (0, 0))
    if combat_state['phase'] == "won":
        title, color = "ENEMY DEFEATED", GREEN
    else:
        title, color = "YOU HAVE FALLEN", RED
    hint = "R: fight again     Esc: quit" if standalone else "Enter: continue"
    if combat_state['end_time'] < END_INPUT_DELAY:
        hint = ""  # keys are ignored for a moment, so don't offer them yet
    box = pygame.Rect(0, 0, 460, 170)
    box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)
    draw_panel(box, edge=color)
    draw_text(font_large, title, color, center=(box.centerx, box.y + 45))
    for i, line in enumerate(wrap_text(font_small, combat_state['message'], box.width - 40)[:2]):
        draw_text(font_small, line, PARCHMENT, center=(box.centerx, box.y + 88 + i * 22))
    draw_text(font_small, hint, LIGHT_GRAY, center=(box.centerx, box.bottom - 24))


def ease_out(t):
    """0 -> 1, starting fast and slowing down at the end (for slide-ins)."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def draw_intro_overlay():
    """Title card, 'Ready...' and the fade from black at the start of a fight."""
    t = combat_state['intro_time']
    phase = combat_state['phase']

    # Enemy title card, between the slide-in and "Ready..."
    if phase == "intro" and INTRO_SLIDE - 0.2 < t < INTRO_TIME - READY_TIME:
        band = pygame.Surface((SCREEN_WIDTH, 84), pygame.SRCALPHA)
        band.fill((8, 4, 14, 190))
        screen.blit(band, (0, 170))
        draw_text(font_large, enemy['name'].upper(), RED, center=(SCREEN_WIDTH // 2, 200))
        draw_text(font_small, "emerges from the dark woods", PARCHMENT, center=(SCREEN_WIDTH // 2, 232))

    if phase == "intro" and t >= INTRO_TIME - READY_TIME:
        draw_text(font_large, "Ready...", PARCHMENT, center=(SCREEN_WIDTH // 2, 212))
    if combat_state['cast_flash'] > 0:
        draw_text(font_large, "CAST!", GOLD, center=(SCREEN_WIDTH // 2, 212))

    if phase == "intro" and t < INTRO_FADE:
        black.set_alpha(int(255 * (1 - t / INTRO_FADE)))
        screen.blit(black, (0, 0))


def pick_enemy_image(enemy_frame):
    """Which enemy picture to show this frame: attack, hurt, frozen or idle."""
    state = combat_state
    timer = state['enemy_timer']
    if state['phase'] == "enemy" and not state['enemy_frozen'] and timer < ATTACK_ANIM_TIME:
        # progress 0 -> 1 through the attack row; the hit lands on the last frame
        frames = enemy_rows['attack']
        progress = (ATTACK_ANIM_TIME - timer) / ATTACK_ANIM_TIME
        return frames[min(len(frames) - 1, int(progress * len(frames)))]
    if state['enemy_hurt'] > 0:
        frames = enemy_rows['hurt']
        progress = (HURT_ANIM_TIME - state['enemy_hurt']) / HURT_ANIM_TIME
        return frames[min(len(frames) - 1, int(progress * len(frames)))]
    if state['enemy_frozen']:
        return enemy_frost_frames[0]  # frozen = no animation
    return enemy_rows['idle'][enemy_frame]


# -------------------------------------------------------------------------
# GAME LOOP
# -------------------------------------------------------------------------
def run_combat(enemy_key="stag", player_hp=PLAYER_MAX_HP, standalone=False):
    """Play one fight. Returns ("won" or "lost", player HP left).

    main.py calls this when the player walks into an enemy. Running this file
    directly calls it with standalone=True (R restarts, Esc quits).
    """
    global popups, particles, fog_x
    start_fight(enemy_key, player_hp)
    pygame.event.clear()  # throw away any keys pressed before the fight started
    enemy_anim_time = 0.0
    enemy_frame = 0
    clock.tick(FPS)  # forget the time spent before the fight started

    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if combat_state['phase'] == "intro":
                    continue  # nothing counts until the intro is over

                if combat_state['phase'] in ("won", "lost"):
                    if combat_state['end_time'] < END_INPUT_DELAY:
                        continue  # e.g. an extra Enter right after the final spell
                    if standalone and event.key == pygame.K_r:
                        start_fight(enemy_key)
                    elif not standalone and event.key == pygame.K_RETURN:
                        return combat_state['phase'], combat_state['player_hp']
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
                    erase_letter()
                elif event.key == pygame.K_RETURN:
                    # Check if typed text matches any spell incantation in the grimoire
                    player_cast(combat_state['typed_buffer'].strip().lower())
                else:
                    # Append typed letter (incantations are letters only)
                    char = event.unicode.lower()
                    if len(char) == 1 and char.isalpha() and len(combat_state['typed_buffer']) < 16:
                        type_letter(char)

        # ---------- UPDATE ----------
        if combat_state['phase'] == "intro":
            combat_state['intro_time'] += dt
            if combat_state['intro_time'] >= INTRO_TIME:
                combat_state['phase'] = "player"
                combat_state['cast_flash'] = CAST_FLASH_TIME
                combat_state['message'] = "Your turn! Type an incantation and press Enter."
                pygame.event.clear()  # anything pressed during the intro is ignored
        if combat_state['phase'] in ("won", "lost"):
            combat_state['end_time'] += dt
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

        for key in ('enemy_shake', 'enemy_hurt', 'player_shake', 'hurt_flash', 'cast_pose', 'death_fade',
                    'cast_flash'):
            combat_state[key] = max(0.0, combat_state[key] - dt)

        enemy_anim_time += dt
        if enemy_anim_time >= ENEMY_FRAME_TIME:
            enemy_anim_time -= ENEMY_FRAME_TIME
            enemy_frame = (enemy_frame + 1) % len(enemy_rows['idle'])

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

        # During the intro both fighters slide in from the sides of the screen
        slide = ease_out(combat_state['intro_time'] / INTRO_SLIDE)
        player_slide = int(-280 * (1 - slide))  # Rect.move needs whole numbers
        enemy_slide = int(320 * (1 - slide))

        # Render Characters (shadow first, then the sprite standing on it)
        draw_shadow(player_rect.move(player_slide, 0))
        if combat_state['phase'] != "won":
            draw_shadow(enemy_rect.move(enemy_slide, 0))

        offset = player_slide
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
            offset = enemy_slide
            if combat_state['enemy_shake'] > 0:
                offset = random.randint(-6, 6)
            enemy_img = pick_enemy_image(enemy_frame)
            if combat_state['phase'] == "won":
                enemy_img = enemy_img.copy()
                enemy_img.set_alpha(int(255 * combat_state['death_fade']))
            screen.blit(enemy_img, enemy_img.get_rect(midbottom=(enemy_feet[0] + offset, enemy_feet[1])))

        for p in particles:
            p.draw(screen)

        # Render Health Bars above each character
        enemy_badges = []
        if combat_state['enemy_burn'] > 0:
            enemy_badges.append((f"BURN {combat_state['enemy_burn']}", EMBER))
        if combat_state['enemy_frozen']:
            enemy_badges.append(("FROZEN", FROST))
        # name plates appear after the title card, so they don't overlap it
        show_plates = combat_state['phase'] != "intro" or combat_state['intro_time'] >= INTRO_TIME - READY_TIME
        if combat_state['phase'] != "won" and show_plates:
            draw_nameplate(enemy['name'], enemy_rect, combat_state['enemy_hp'], combat_state['enemy_hp_shown'],
                           combat_state['enemy_max_hp'], RED, enemy_badges)
        player_badges = [("WARD", WARD_BLUE)] if combat_state['player_ward'] else []
        if show_plates:
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

        draw_intro_overlay()
        if combat_state['phase'] in ("won", "lost"):
            draw_end_screen(standalone)

        pygame.display.flip()


if __name__ == "__main__":
    # Run a single fight for testing: python combat_proto.py [stag|moth|maw|pilgrim|bellwether]
    pygame.display.set_caption("Spell Typer - Combat Prototype")
    choice = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in enemies.ENEMIES else "stag"
    run_combat(choice, standalone=True)
