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
#  71-100  Lucid    words spelled correctly, no screen effects
#  31-70   Uneasy   slight black vignette, a few letters replaced,
#                   now and then a hallucinated word drifts past
#   0-30   Fraying  red pulsing vignette, garbled nonsense,
#                   hallucinated words everywhere
SANITY_LUCID = 70        # above this you are Lucid
SANITY_FRAYING = 30      # at or below this you are Fraying
# Uneasy: the share of letters replaced climbs from the first number (at 70)
# to the second (at 31).
UNEASY_REPLACE = (0.15, 0.50)
FORBIDDEN_BELOW = 40     # forbidden spells only show on pages below this sanity
GAZE_UNLOCK_BELOW = 15   # win a fight below this to unlock The Gate's Gaze

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
# Each act multiplies the one before it (exponential growth):
# act n = base x GROWTH ** (n - 1). Act 3 creatures have 1.5^2 = 2.25x health.
ACT_HEALTH_GROWTH = 1.50
ACT_DAMAGE_GROWTH = 1.32
ACT_SPEED_GROWTH = 1.10
HEAVY_CHANCE = 0.30      # chance any one attack is a HEAVY blow (rolled, not a rhythm) ...
HEAVY_DAMAGE = 1.5       # ... which hits this much harder and needs a longer word
HEAVY_SHOWS_AT = 0.55    # the bar only turns magenta once it is this full
RAGE_SPEED = 1.4         # a boss below half health attacks this many times as often

# --- Unpredictable foes ----------------------------------------------------------
# Every creature has its own habits (see STYLES in bestiary.py). These are the
# shared numbers behind them.
QUICK_FRACTION = (0.40, 0.65)   # a quick strike comes after this share of a normal wait
FEINT_PAUSE = 0.5               # seconds a feint rears up before it relaxes
FEINT_RECOVER = (0.7, 1.6)      # ... and how soon the real blow follows
FLURRY_GAP = (0.6, 1.2)         # a flurry's second blow follows this fast
PACE_WOBBLE = 0.35              # attack bars fill at 1 +/- this speed, changing smoothly

# --- Difficulty levels -------------------------------------------------------------
# Picked when you name the boy. Multiplies the numbers above.
#   health/damage/speed: the creatures   defend: time on Defend words
DIFFICULTIES = [
    dict(key="story", name="Story", health=0.75, damage=0.6, speed=0.85, defend=1.35,
         desc="For the tale. Gentle foes, generous Defend words."),
    dict(key="normal", name="Normal", health=1.0, damage=1.0, speed=1.0, defend=1.0,
         desc="The woods as they were meant to be."),
    dict(key="hard", name="Hard", health=1.25, damage=1.25, speed=1.12, defend=0.9,
         desc="Tougher, faster creatures."),
    dict(key="nightmare", name="Nightmare", health=1.5, damage=1.5, speed=1.25, defend=0.8,
         desc="Everything in the dark wants you."),
]
DIFFICULTY = {d["key"]: d for d in DIFFICULTIES}

# --- Endless woods (after act 3) -----------------------------------------------------
# Beat the third boss and you may walk on instead of leaving. Every act past
# the third multiplies these again, so the climb is exponential but slow.
ENDLESS_HEALTH = 1.15    # creatures' health
ENDLESS_DAMAGE = 1.10    # sanity each blow takes
ENDLESS_SPEED = 1.06     # how often they attack
ENDLESS_COOLDOWN = 0.94  # the wait after a feint, flurry or first attack
MIN_INTERVAL = 1.6       # no creature ever waits less than this between attacks

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
