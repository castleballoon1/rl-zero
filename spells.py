"""Spell definitions and the damage formula (pure Python, no pygame).

Longer incantations do more: every spell's strength is
    power-per-letter x number of letters x level bonus x page potency
and then accuracy and crits are applied when it is cast.
"""
from dataclasses import dataclass

from settings import (LEVEL_BONUS, CRIT_K, CRIT_MIN, CRIT_MAX, CRIT_MULT,
                      FOCUS_BONUS)
from words import sanity_tier


@dataclass(frozen=True)
class SpellDef:
    key: str
    name: str
    incantation: str
    kind: str            # damage, aoe, drain, dot, slow, execute, shield, sanity, regen, pact,
                         # weaken, interrupt, mirror, echo, plague, desperate
    power: float         # strength per letter
    sanity_cost: int
    element: str
    tier: str            # common, rare, forbidden
    desc: str
    unlock: str = ""     # empty = available from the start; else how to unlock
    chill: float = 0.0   # seconds added to the target's attack timer
    lifesteal: float = 0.0

    @property
    def letters(self):
        return sum(1 for c in self.incantation if c.isalpha())

    @property
    def base_amount(self):
        return self.power * self.letters


SPELL_LIST = [
    # --- starters -------------------------------------------------------
    SpellDef("ember", "Ember", "ignis", "damage", 3.0, 2, "fire", "common",
             "A spark from the grimoire's first page."),
    SpellDef("ward", "Ward", "aegis fortis", "shield", 1.6, 3, "ward", "common",
             "A thin skin of light that absorbs blows."),
    # --- common ----------------------------------------------------------
    SpellDef("frost", "Frost Needle", "glacies acus", "damage", 2.5, 4, "frost",
             "common", "Pierces and chills; delays the target's attack.",
             chill=1.5),
    SpellDef("lash", "Spark Lash", "fulgur verbera", "damage", 2.8, 5, "storm",
             "common", "A whip of crackling storm."),
    SpellDef("mend", "Mend", "sana vulnus meum", "regen", 2.2, 0, "life",
             "common", "Your mind knits itself back together over 6 seconds."),
    SpellDef("clarity", "Clarity", "mens clara manet", "sanity", 1.2, 0, "mind",
             "common", "Steady the mind at once, and lift every hex."),
    SpellDef("cinder", "Cinder Rain", "pluvia cinerum", "aoe", 1.6, 5, "fire",
             "common", "Ash and embers fall on every foe."),
    SpellDef("wither", "Withering Word", "marcesce vis tua", "weaken", 1.5, 4, "mind",
             "common", "Wounds the target and saps its blows by 30% for the fight."),
    SpellDef("shatter", "Shatter Stride", "frange impetum", "interrupt", 2.2, 5, "storm",
             "common", "Wounds the target and knocks its attack bar back to empty."),
    # --- rare -------------------------------------------------------------
    SpellDef("rot", "Hex of Rot", "putresce caro mortalis", "dot", 3.2, 6, "rot",
             "rare", "The target rots over six seconds."),
    SpellDef("bone", "Bone Spear", "os hasta perforat", "damage", 3.4, 7, "bone",
             "rare", "A spear of old marrow."),
    SpellDef("pact", "Whisper Pact", "foedus susurri in tenebris", "pact", 4.0, 12,
             "void", "rare", "Pay sanity now; your next spell strikes that much harder (%)."),
    SpellDef("drain", "Soul Drain", "anima tua mihi exhauritur", "drain", 2.6, 8,
             "void", "rare", "Tear out their soul; regain half the damage as sanity.",
             unlock="Defeat The Lantern Stag", lifesteal=0.5),
    SpellDef("chain", "Chain Lightning", "tonitrus catena saltat", "aoe", 2.4, 9,
             "storm", "rare", "Leaps between every foe.",
             unlock="Defeat The Rootbound Pilgrim"),
    SpellDef("hourglass", "Hourglass Rend", "clepsydra frangitur", "slow", 1.2, 6,
             "mind", "rare", "Shatter time; every foe's attack is delayed.",
             unlock="Defeat The Rootbound Pilgrim"),
    SpellDef("thorn", "Thorn Cage", "spinae te claudunt", "damage", 2.6, 6, "bone",
             "rare", "Thorns bind the target; its attack is delayed 3 s.",
             unlock="Deflect 8 attacks in one run", chill=3.0),
    SpellDef("flare", "Grimoire Flare", "lumen lucernae exardescit", "aoe", 1.9, 7,
             "fire", "rare", "The grimoire blazes over every foe.",
             unlock="Cast 40 spells in one run"),
    SpellDef("finalword", "Final Word", "verbum ultimum", "execute", 2.6, 6, "mind",
             "rare", "Double damage to a foe below 30% health.",
             unlock="Cast a 20+ letter incantation with 100% accuracy"),
    SpellDef("mirror", "Mirror Veil", "speculum reddit ictum", "mirror", 1.0, 6, "ward",
             "rare", "The next blow that would land is turned back on its maker, harder."),
    SpellDef("echo", "Echo", "echo verborum redit", "echo", 3.4, 3, "mind",
             "rare", "Your last spell sounds again, weaker (%), for free.",
             unlock="Defeat The Lantern Stag"),
    SpellDef("plague", "Creeping Plague", "lues per omnes serpit", "plague", 2.0, 9, "rot",
             "rare", "Every foe rots over six seconds.",
             unlock="Defeat The Rootbound Pilgrim"),
    # --- forbidden ------------------------------------------------------
    SpellDef("blacksun", "Black Sun", "sol niger ardet in me", "damage", 4.0, 15,
             "void", "forbidden", "A sun that gives no light. Costs dearly."),
    SpellDef("gaze", "The Gate's Gaze", "oculus ultra portam aperitur", "damage",
             4.5, 20, "void", "forbidden", "Something behind the gate looks back.",
             unlock="Win a fight with under 15 sanity"),
    SpellDef("hymn", "Starless Hymn", "cantus sine stellis omnia devorat", "aoe",
             3.2, 18, "void", "forbidden", "Sing the song that ate the stars.",
             unlock="Defeat The Starved Bellwether"),
    SpellDef("bloodprice", "Blood Price", "sanguis pro verbis meis", "desperate", 2.6, 10,
             "bone", "forbidden", "The less sanity you have left, the harder it hits (up to x2.5).",
             unlock="Win a fight while Fraying (30 sanity or below)"),
]

SPELLS = {s.key: s for s in SPELL_LIST}
STARTER_SPELLS = ["ember", "frost", "ward"]
DAMAGE_KINDS = ("damage", "aoe", "drain", "dot", "slow", "execute", "weaken",
                "interrupt", "plague", "desperate")
# spells that send a bolt at foes (the rest are cast on the boy himself)
TARGET_KINDS = ("damage", "drain", "dot", "execute", "weaken", "interrupt", "desperate")
ALL_FOES_KINDS = ("aoe", "slow", "plague")
TIER_WEIGHT = {"common": 3, "rare": 2, "forbidden": 1}

KIND_LABEL = {
    "damage": "Damage", "aoe": "All foes", "drain": "Drain", "dot": "Rot",
    "slow": "Delay all", "execute": "Execute", "regen": "Regain", "shield": "Shield",
    "sanity": "Sanity", "pact": "Empower", "weaken": "Weaken", "interrupt": "Stagger",
    "mirror": "Mirror +", "echo": "Echo", "plague": "Plague all", "desperate": "Damage",
}
WEAKEN = 0.70            # Withering Word: the target's blows keep this share ...
WEAKEN_FLOOR = 0.40      # ... but never fall below this share of the original
DESPERATE_MAX = 1.5      # Blood Price: up to +150% at no sanity


def effect_text(kind, amount, before=None):
    """What a spell does, in a few words: 'Damage 28', 'Next spell +92%' ..."""
    was = f"{before:.0f} -> " if before is not None else ""
    if kind == "pact":
        return f"Next spell +{was}{amount:.0f}%"
    if kind == "echo":
        return f"Echo {was}{min(100, amount):.0f}%"
    return f"{KIND_LABEL[kind]} {was}{amount:.0f}"


def cost_text(cost):
    return "free" if cost < 0.5 else f"-{cost:.0f} sanity"


def default_unlocked():
    return [s.key for s in SPELL_LIST if not s.unlock]


class OwnedSpell:
    """A spell in the player's grimoire for this run."""

    def __init__(self, key, level=1, potency=1.0):
        self.key = key
        self.level = level
        self.potency = potency

    @property
    def defn(self):
        return SPELLS[self.key]

    def strength(self):
        """Strength before accuracy/crit."""
        return (self.defn.base_amount * (1 + LEVEL_BONUS * (self.level - 1))
                * self.potency)

    def empower(self, potency):
        self.level += 1
        self.potency = max(self.potency, potency)


def crit_chance(cps):
    """Crit chance is inversely proportional to typing speed."""
    if cps <= 0:
        return CRIT_MAX
    return max(CRIT_MIN, min(CRIT_MAX, CRIT_K / cps))


def cast_amount(owned, accuracy, cps, roll, focus=0, crit_mult=CRIT_MULT):
    """Return (amount, crit) for a completed incantation.

    roll is a random number in [0, 1) so this stays testable.
    focus is the player's streak of clean casts (each point adds a bonus).
    """
    amount = owned.strength() * accuracy ** 2 * (1 + FOCUS_BONUS * focus)
    crit = False
    if owned.defn.kind in DAMAGE_KINDS and roll < crit_chance(cps):
        amount *= crit_mult
        crit = True
    return amount, crit


def page_potency(sanity, boss):
    """How powerful a page is: the lower your sanity, the stronger the page."""
    scale = 0.9 if boss else 0.5
    return round(1 + (100 - max(0, sanity)) / 100 * scale, 2)


def page_choice_count(sanity, boss):
    """More choices are offered the lower your sanity is."""
    tier = sanity_tier(sanity)
    return (3 + tier) if boss else (2 + (tier + 1) // 2)


def echo_fraction(amount):
    """Echo's strength is the share of the last spell it repeats (capped at 100%)."""
    return max(0.0, min(1.0, amount / 100))


def desperate_bonus(sanity, max_sanity):
    """Blood Price hits harder the less sanity is left: x1 when full, x2.5 at none."""
    lost = 1 - max(0.0, min(1.0, sanity / max_sanity))
    return 1 + DESPERATE_MAX * lost
