"""Enemies, bosses and the three acts.

The creatures themselves (name, sprite sheet, flavour text) live in the
team's enemies.py. This file adds what the full game needs on top of that:
how each one fights in real time, its trait, where its death sheet is, and
which creatures roam which act.
"""
import os

import enemies as creature_table
from settings import (FOE_HEALTH, FOE_DAMAGE, FOE_SPEED, ACT_HEALTH_GROWTH,
                      ACT_DAMAGE_GROWTH)

# Real-time combat numbers for an ordinary creature (act 1 strength).
#   hp, dmg     health and damage per blow
#   dread       sanity lost when its blow lands
#   interval    seconds between attacks (random in this range)
STATS = {
    "moth": dict(hp=34, dmg=6, dread=6, interval=(6.0, 7.5), trait="stare"),
    "maw": dict(hp=56, dmg=10, dread=3, interval=(7.0, 8.5), trait="drink"),
    "stag": dict(hp=60, dmg=9, dread=6, interval=(7.0, 8.5), trait="hex"),
    "pilgrim": dict(hp=72, dmg=12, dread=4, interval=(7.5, 9.0), trait="dirge"),
    "bellwether": dict(hp=64, dmg=9, dread=6, interval=(7.5, 9.0), trait="rally"),
}

# name/trait per creature, in the shape the codex expects
ENEMIES = {key: dict(name=creature_table.ENEMIES[key]["name"], **stats)
           for key, stats in STATS.items()}

# One boss per act: a great old specimen of one of the creatures.
BOSSES = {
    1: dict(kind="stag", name="The Lantern Stag", hp=230, dmg=13, dread=6,
            interval=(5.5, 7.0), trait="hex",
            rage="The Stag's lantern burns white!"),
    2: dict(kind="pilgrim", name="The Rootbound Pilgrim", hp=340, dmg=16, dread=8,
            interval=(5.5, 6.5), trait="dirge",
            rage="Roots tear up through the path!"),
    3: dict(kind="bellwether", name="The Starved Bellwether", hp=470, dmg=19, dread=10,
            interval=(5.0, 6.0), trait="rally",
            rage="The bell will not stop ringing!"),
}

# Short label shown over the enemy, and the full rule for the codex.
TRAITS = {
    "stare": ("STARE", "Its eyes drain your sanity for as long as it lives."),
    "drink": ("DRINK", "Heals itself by the damage it deals to you."),
    "hex": ("HEX", "A blow that lands scrambles one of your spells until you cast it."),
    "dirge": ("GRASP", "Its roots drag at you: longer DEFEND words."),
    "rally": ("TOLL", "Rings its bell: allies hurry. Alone, it costs sanity and a spell."),
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

# tint multiplies the scene art's colours so each act has its own mood
ACTS = {
    1: dict(name="The Whispering Woods", pool=["moth", "maw"], tint=None,
            sky=(22, 26, 44), fog=(70, 80, 110), tree=(10, 14, 22),
            ground=(24, 30, 28), encounters=4),
    2: dict(name="The Hollow Marsh", pool=["moth", "maw", "stag"], tint=(165, 235, 200),
            sky=(26, 34, 30), fog=(80, 100, 80), tree=(12, 20, 14),
            ground=(30, 36, 24), encounters=5),
    3: dict(name="The Starless Grove", pool=["maw", "stag", "pilgrim", "moth"],
            tint=(245, 150, 185),
            sky=(30, 14, 34), fog=(110, 60, 120), tree=(18, 8, 20),
            ground=(30, 18, 30), encounters=5),
}

FINAL_ACT = 3


def _with_art(data, kind):
    creature = creature_table.ENEMIES[kind]
    data["kind"] = kind
    data["art"] = kind
    data["attack_text"] = creature["attack_text"]
    return data


def _toughen(data, act_steps):
    """Apply the difficulty numbers from settings.py to one creature."""
    data["hp"] = round(data["hp"] * FOE_HEALTH * (1 + ACT_HEALTH_GROWTH * act_steps))
    data["dmg"] = round(data["dmg"] * FOE_DAMAGE * (1 + ACT_DAMAGE_GROWTH * act_steps))
    low, high = data["interval"]
    data["interval"] = (low / FOE_SPEED, high / FOE_SPEED)
    return data


def scaled_enemy(kind, act):
    """An ordinary creature's stats, scaled up for later acts."""
    data = dict(STATS[kind])
    data["name"] = creature_table.ENEMIES[kind]["name"]
    data["boss"] = False
    return _with_art(_toughen(data, act - 1), kind)


def boss_for(act):
    data = dict(BOSSES[act])
    data["boss"] = True
    return _with_art(_toughen(data, 0), data["kind"])   # bosses carry their act in their own numbers
