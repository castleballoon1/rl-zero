"""Named constants for Spell Typer.

Every number that changes how the game feels lives here, so tuning the game
means editing one line instead of hunting for magic numbers.
"""

# --- Window -----------------------------------------------------------------
WIDTH, HEIGHT = 960, 600   # the scene art is drawn 600 px tall
FPS = 60
MAX_DT = 0.05            # cap dt so a freeze never makes things tunnel
TITLE = "Spell Typer"

# --- Exploration (platforming) ----------------------------------------------
GROUND_Y = 476           # the dirt path in the scene art (feet stand here)
GRAVITY = 1900           # px / s^2
JUMP_SPEED = 720         # px / s
MOVE_SPEED = 250         # px / s
PLAYER_FRAME_TIME = 0.12

# --- Player run stats -------------------------------------------------------
# Sanity is the boy's ONLY health: spells cost it, blows take it, and at 0 the
# run ends. There is no separate health bar.
START_SANITY = 100
MAX_SANITY = 100
MAX_SHIELD = 60
GRIMOIRE_SIZE = 8

# --- Sanity tiers -----------------------------------------------------------
# sanity >= LUCID      -> words are spelled correctly
# sanity >= FRAYING    -> some letters are replaced
# sanity >= MAD        -> many letters are replaced
# sanity <  MAD        -> garbled nonsense
SANITY_LUCID = 70
SANITY_FRAYING = 40
SANITY_MAD = 15
FORBIDDEN_BELOW = 40     # forbidden spells only show on pages below this sanity

# --- Damage formula ---------------------------------------------------------
LEVEL_BONUS = 0.30       # each extra spell level adds +30%
# Crit chance is INVERSELY proportional to typing speed (chars / second):
#   chance = CRIT_K / cps, clamped to [CRIT_MIN, CRIT_MAX]
# Typing slowly and carefully is rewarded with crits, but enemies keep
# attacking while you take your time.
CRIT_K = 1.0
CRIT_MIN = 0.05
CRIT_MAX = 0.50
CRIT_MULT = 2.0

# --- Defense prompt ---------------------------------------------------------
DEFLECT_ACCURACY = 0.90  # need this accuracy ...
DEFLECT_TIME_FRACTION = 0.60  # ... and to finish within 60% of the time
REFLECT_FRACTION = 0.5   # a deflect sends half the damage back

# --- Colours ----------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (235, 232, 222)
GRAY = (130, 128, 140)
DARK = (14, 12, 20)
BONE = (222, 210, 180)
BLOOD = (170, 30, 40)
SANITY_COL = (120, 90, 220)
SHIELD_COL = (90, 170, 220)
GOLD = (235, 195, 90)
GREEN = (110, 210, 130)
TYPED_COL = (255, 215, 110)
MISS_COL = (255, 70, 70)

ELEMENT_COLORS = {
    "fire": (255, 140, 50),
    "frost": (140, 210, 255),
    "storm": (200, 200, 255),
    "bone": (230, 220, 190),
    "rot": (120, 200, 80),
    "void": (170, 80, 240),
    "life": (120, 230, 140),
    "mind": (160, 140, 255),
    "ward": (110, 180, 230),
}

SAVE_FILE = "save.json"

# --- Focus (streak of clean casts) ------------------------------------------
FOCUS_MAX = 5
FOCUS_BONUS = 0.08       # each point of focus adds +8% to every spell
FOCUS_ACCURACY = 0.95    # a cast this accurate builds focus
FOCUS_BREAK = 0.80       # a cast sloppier than this loses it all

# --- Woods ------------------------------------------------------------------
BRAMBLE_DAMAGE = 6
MOTE_SANITY = 4
SHRINE_SANITY = 35
REST_SANITY = 45
BREATH_SANITY = 6        # regained after every fight

# --- Difficulty ---------------------------------------------------------------
# Raise these to make every creature tougher; 1.0 is the original strength.
FOE_HEALTH = 1.15        # multiplies every creature's and boss's health
FOE_DAMAGE = 1.5         # multiplies the sanity every blow takes
FOE_SPEED = 1.15         # attacks come this many times as often
ACT_HEALTH_GROWTH = 0.40  # extra health per act (act 3 = 1 + 2 x this)
ACT_DAMAGE_GROWTH = 0.30  # extra damage per act
HEAVY_EVERY = 3          # every 3rd attack of a creature is a HEAVY blow ...
HEAVY_DAMAGE = 1.5       # ... which hits this much harder and needs a longer word
RAGE_SPEED = 1.4         # a boss below half health attacks this many times as often

# --- Burnout --------------------------------------------------------------------
# Lean on one spell too hard and it burns out for a while.
BURNOUT_CASTS = 3        # this many casts in quick succession burns a spell out
HEAT_FADE_TIME = 6.0     # seconds for one cast's worth of heat to fade
BURNOUT_TIME = 8.0       # seconds a burnt-out spell cannot be cast
SOOTHE_FADE = 0.6        # each healing spell in one fight restores this much of the last

# --- Scene changes ----------------------------------------------------------------
FADE_TIME = 0.25         # seconds to fade to black, and again to fade back in

# --- Defend words -------------------------------------------------------------------
# Time allowed = DEFEND_REACTION + letters / typing speed. The speed asked of
# you (letters per second) rises as sanity falls: [calm, shaken, desperate].
DEFEND_REACTION = 0.6
DEFEND_SPEED = [3.0, 3.6, 4.2]
