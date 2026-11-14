"""Seeded procedural generation of each act's woods (pure Python).

The same seed always builds the same woods, so players can share seeds.
"""
import random

from settings import GROUND_Y
from bestiary import ACTS


def make_rng(seed, act, salt=""):
    return random.Random(f"{seed}:{act}:{salt}")


def generate_act(seed, act):
    rng = make_rng(seed, act, "map")
    info = ACTS[act]
    length = 3600 + 500 * act

    # One-way platforms floating above the ground.
    platforms = []
    x = 420
    while x < length - 700:
        w = rng.randint(120, 230)
        h_above = rng.choice([92, 110, 128])   # all within one jump
        platforms.append((x, GROUND_Y - h_above, w, 16))
        # sometimes a second, higher step next to it
        if rng.random() < 0.35:
            platforms.append((x + w + rng.randint(30, 70),
                              GROUND_Y - h_above - rng.randint(70, 90),
                              rng.randint(100, 160), 16))
        x += w + rng.randint(260, 520)

    # Encounters spread evenly with jitter, never right at the start or gate.
    count = info["encounters"]
    lo, hi = 750, length - 650
    step = (hi - lo) / count
    encounters = []
    for i in range(count):
        ex = int(lo + step * i + rng.uniform(0.15, 0.85) * step)
        # act 1: one or two creatures; later acts: two or three
        size = rng.randint(1, 2) if act == 1 else rng.randint(2, 3)
        if i == 0:
            size = 1  # a gentle first fight
        kinds = [rng.choice(info["pool"]) for _ in range(size)]
        encounters.append(dict(x=ex, enemies=kinds))

    # Shrines: restore health and sanity once each. Often up on a platform.
    shrines = []
    for i in range(1 + (act >= 2)):
        if platforms and rng.random() < 0.6:
            px, py, pw, _ = rng.choice(platforms)
            shrines.append((px + pw // 2, py))
        else:
            shrines.append((rng.randint(900, length - 900), GROUND_Y))

    # Lore stones with short texts.
    lore = []
    for i in range(2):
        lore.append((rng.randint(500, length - 800), rng.choice(LORE[act])))

    # Brambles: thorn patches on the ground. Jump over them or bleed.
    blocked = ([e["x"] for e in encounters] + [x for x, _ in lore]
               + [x for x, y in shrines if y == GROUND_Y])
    brambles = []
    tries = 0
    while len(brambles) < 3 + act and tries < 80:
        tries += 1
        x = rng.randint(500, length - 600)
        if any(abs(x - b) < 160 for b in blocked):
            continue
        if any(abs(x - bx) < 220 for bx, _ in brambles):
            continue
        brambles.append((x, rng.choice([46, 60, 74])))

    # Motes of calm: small lights that restore a little sanity. Most sit on
    # platforms, a few hang in the air and need a jump.
    motes = []
    for (px, py, pw, _) in platforms:
        if rng.random() < 0.7:
            motes.append((px + pw // 2 + rng.randint(-pw // 4, pw // 4), py - 30))
    for _ in range(3):
        motes.append((rng.randint(400, length - 500),
                      GROUND_Y - rng.choice([105, 125])))

    return dict(act=act, name=info["name"], length=length, platforms=platforms,
                encounters=encounters, shrines=shrines, lore=lore,
                brambles=brambles, motes=motes, gate_x=length - 220)


LORE = {
    1: ["The trees lean in when you are not looking.",
        "A page, half burned: 'speak the words as you SEE them'.",
        "The grimoire is the only warm thing here.",
        "Someone carved names here. One of them is yours."],
    2: ["The water remembers every face that drowned in it.",
        "'The madder the reader, the stronger the page.'",
        "Mouths in the mud whisper your name, misspelled.",
        "Do not trust the words. Type them anyway."],
    3: ["There were stars here once. Something ate them.",
        "The Drowned Star waits at the bottom of the sky.",
        "Your grimoire grows heavier. Or your hands weaker.",
        "Dawn is on the other side. You are sure of it."],
}
