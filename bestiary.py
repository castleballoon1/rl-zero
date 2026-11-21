"""Enemies, bosses and the acts.

The creatures themselves (name, sprite sheet, flavour text) live in the
team's enemies.py. This file adds what the full game needs on top of that:
how each one fights in real time, its trait, its habits, where its death
sheet is, which creatures roam which act, and how much tougher each act is.
"""
import os

import enemies as creature_table
from settings import (FOE_HEALTH, FOE_DAMAGE, FOE_SPEED, ACT_HEALTH_GROWTH,
                      ACT_DAMAGE_GROWTH, ACT_SPEED_GROWTH, DIFFICULTY,
                      ENDLESS_HEALTH, ENDLESS_DAMAGE, ENDLESS_SPEED, ENDLESS_COOLDOWN,
                      MIN_INTERVAL)

# Real-time combat numbers for an ordinary creature (act 1 strength).
#   hp          its health
#   dmg         sanity you lose when its blow lands (sanity is your health)
#   interval    seconds between attacks (random in this range; it is wide
#               on purpose so you cannot count the beat)
STATS = {
    "moth": dict(hp=34, dmg=6, interval=(4.8, 8.6), trait="stare"),
    "maw": dict(hp=56, dmg=10, interval=(5.8, 9.6), trait="drink"),
    "stag": dict(hp=60, dmg=9, interval=(5.8, 9.6), trait="hex"),
    "pilgrim": dict(hp=72, dmg=12, interval=(6.4, 10.0), trait="dirge"),
    "bellwether": dict(hp=64, dmg=9, interval=(6.4, 10.0), trait="rally"),
}

# Each creature's habits, so no two fight alike and none keeps a steady beat.
#   quick   chance an attack comes early (a fraction of the usual wait)
#   feint   chance it rears up, then holds back, and strikes soon after
#   flurry  chance a blow is followed at once by a second
#   heavy   chance a blow is a HEAVY one (magenta bar)
#   wobble  how unevenly its attack bar fills (0 = steady)
STYLES = {
    "moth": dict(quick=0.15, feint=0.25, flurry=0.05, heavy=0.20, wobble=1.0),   # erratic
    "maw": dict(quick=0.30, feint=0.05, flurry=0.10, heavy=0.30, wobble=0.6),    # lunges
    "stag": dict(quick=0.10, feint=0.12, flurry=0.08, heavy=0.45, wobble=0.4),   # heavy horns
    "pilgrim": dict(quick=0.05, feint=0.10, flurry=0.30, heavy=0.30, wobble=0.5),  # flails
    "bellwether": dict(quick=0.15, feint=0.18, flurry=0.15, heavy=0.30, wobble=0.7),
}
BOSS_STYLE_BONUS = dict(feint=0.05, flurry=0.08)     # bosses are craftier
RAGE_STYLE_BONUS = dict(quick=0.10, flurry=0.12)     # ... and wilder once enraged

# name/trait per creature, in the shape the codex expects
ENEMIES = {key: dict(name=creature_table.ENEMIES[key]["name"], **stats)
           for key, stats in STATS.items()}

# One boss per act: a great old specimen of one of the creatures.
BOSSES = {
    1: dict(kind="stag", name="The Lantern Stag", hp=230, dmg=13,
            interval=(4.6, 7.6), trait="hex",
            rage="The Stag's lantern burns white!"),
    2: dict(kind="pilgrim", name="The Rootbound Pilgrim", hp=340, dmg=16,
            interval=(4.6, 7.2), trait="dirge",
            rage="Roots tear up through the path!"),
    3: dict(kind="bellwether", name="The Starved Bellwether", hp=470, dmg=19,
            interval=(4.2, 6.8), trait="rally",
            rage="The bell will not stop ringing!"),
}

# Short label shown over the enemy, and the full rule for the codex.
TRAITS = {
    "stare": ("Stare", "Its eyes drain your sanity for as long as it lives."),
    "drink": ("Drink", "Heals itself by the sanity it takes from you."),
    "hex": ("Hex", "A blow that lands scrambles one of your spells until you cast it."),
    "dirge": ("Grasp", "Its roots drag at you: longer Defend words."),
    "rally": ("Toll", "Rings its bell: allies hurry. Alone, it costs sanity and a spell."),
}

# Death sheets: 4 pictures per row. The rows are not all the same height, so
# each row's (top, bottom) in sheet pixels is listed, like the frame
# rectangles in enemies.py. The last rows show the page the creature drops.
DEATH_SHEETS = {
    "stag": (os.path.join("Lantern_Stag_Spritesheet", "LanternStag_Death.png"),
             [(0, 370), (370, 718), (718, 980), (980, 1199)]),
    "maw": (os.path.join("Mire_Maw_Spritesheet", "Mire_Maw_death.png"),
            [(0, 314), (314, 601), (601, 820), (820, 1024)]),
    "moth": (os.path.join("Moth Choir-SpriteSheet", "Moth_Choir_death.png"),
             [(0, 408), (408, 745), (745, 1033), (1033, 1199)]),
    "pilgrim": (os.path.join("Rootnound_Pilgrim_SpriteSheet", "Rootbound_Pilgrim_death.png"),
                [(0, 400), (400, 770), (770, 1030), (1030, 1199)]),
    "bellwether": (os.path.join("Starved_Bellwether_SpriteSheet", "Starved_Bellweather_death.png"),
                   [(0, 256), (256, 512), (512, 768), (768, 1024)]),
}

# tint multiplies the scene art's colours so each act has its own mood.
# encounters: how many groups of creatures roam the act; group: how many
# creatures stand in one group (smallest, largest).
ACTS = {
    1: dict(name="The Whispering Woods", pool=["moth", "maw"], tint=None,
            sky=(22, 26, 44), fog=(70, 80, 110), tree=(10, 14, 22),
            ground=(24, 30, 28), encounters=5, group=(1, 2)),
    2: dict(name="The Hollow Marsh", pool=["moth", "maw", "stag"], tint=(165, 235, 200),
            sky=(26, 34, 30), fog=(80, 100, 80), tree=(12, 20, 14),
            ground=(30, 36, 24), encounters=7, group=(2, 3)),
    3: dict(name="The Starless Grove", pool=["maw", "stag", "pilgrim", "moth"],
            tint=(245, 150, 185),
            sky=(30, 14, 34), fog=(110, 60, 120), tree=(18, 8, 20),
            ground=(30, 18, 30), encounters=9, group=(2, 3)),
}

FINAL_ACT = 3            # the story ends here; past it are the endless woods
ENDLESS_POOL = ["moth", "maw", "stag", "pilgrim", "bellwether"]
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def depth_of(act):
    """How many acts past the story this is (0 during the story)."""
    return max(0, act - FINAL_ACT)


def act_info(act):
    """Everything about one act, for any act number.

    Acts 1-3 are the story. Past them the woods repeat their three looks,
    deeper each time, with every creature roaming and a few more groups.
    'look' is the story act whose art and lore it borrows.
    """
    look = (act - 1) % FINAL_ACT + 1
    info = dict(ACTS[look])
    info["look"] = look
    info["depth"] = depth_of(act)
    if info["depth"]:
        d = info["depth"]
        numeral = ROMAN[d] if d < len(ROMAN) else str(d)
        info["name"] = f"Deeper {numeral}: {ACTS[look]['name']}"
        info["pool"] = list(ENDLESS_POOL)
        info["encounters"] = min(12, ACTS[FINAL_ACT]["encounters"] + d)
        info["group"] = (2, 3)
    return info


def _with_art(data, kind):
    creature = creature_table.ENEMIES[kind]
    data["kind"] = kind
    data["art"] = kind
    data["attack_text"] = creature["attack_text"]
    return data


def _toughen(data, story_steps, depth, difficulty):
    """Apply the difficulty numbers from settings.py to one creature.

    story_steps: acts of exponential story growth to apply.
    depth: acts past the story (each multiplies by the ENDLESS numbers).
    """
    level = DIFFICULTY.get(difficulty, DIFFICULTY["normal"])
    data["hp"] = round(data["hp"] * FOE_HEALTH * level["health"]
                       * ACT_HEALTH_GROWTH ** story_steps * ENDLESS_HEALTH ** depth)
    data["dmg"] = round(data["dmg"] * FOE_DAMAGE * level["damage"]
                        * ACT_DAMAGE_GROWTH ** story_steps * ENDLESS_DAMAGE ** depth)
    speed = FOE_SPEED * level["speed"] * ACT_SPEED_GROWTH ** story_steps * ENDLESS_SPEED ** depth
    low, high = data["interval"]
    data["interval"] = (max(MIN_INTERVAL, low / speed), max(MIN_INTERVAL + 0.6, high / speed))
    data["cooldown"] = ENDLESS_COOLDOWN ** depth     # feints and flurries come back faster
    return data


def _style(kind, boss):
    style = dict(STYLES[kind])
    if boss:
        for key, extra in BOSS_STYLE_BONUS.items():
            style[key] += extra
    return style


def scaled_enemy(kind, act, difficulty="normal"):
    """An ordinary creature's stats, scaled up for later acts."""
    data = dict(STATS[kind])
    data["name"] = creature_table.ENEMIES[kind]["name"]
    data["boss"] = False
    data["style"] = _style(kind, False)
    story_steps = min(act, FINAL_ACT) - 1
    return _with_art(_toughen(data, story_steps, depth_of(act), difficulty), kind)


def boss_for(act, difficulty="normal"):
    """The boss at the end of an act. Bosses carry their own act's strength in
    their numbers; in the endless woods they come back stronger."""
    look = (act - 1) % FINAL_ACT + 1
    data = dict(BOSSES[look])
    data["boss"] = True
    data["style"] = _style(data["kind"], True)
    depth = depth_of(act)
    if depth:
        data["name"] = data["name"].replace("The ", "The Deeper ", 1)
    story_steps = min(act, FINAL_ACT) - look
    return _with_art(_toughen(data, story_steps, depth, difficulty), data["kind"])
