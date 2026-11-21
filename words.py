"""Word corruption and defense words (pure Python, no pygame).

Lucid (71-100)   -> the incantation is shown spelled correctly.
Uneasy (31-70)   -> some letters are replaced, and you must type what you SEE.
Fraying (0-30)   -> the incantation becomes garbled nonsense.
"""
import random
import string

from settings import (SANITY_LUCID, SANITY_FRAYING, UNEASY_REPLACE, DEFEND_REACTION,
                      DEFEND_SPEED)

LETTERS = string.ascii_lowercase

TIER_NAMES = ["Lucid", "Uneasy", "Fraying"]
LUCID, UNEASY, FRAYING = 0, 1, 2


def sanity_tier(sanity):
    """0 = lucid (71-100), 1 = uneasy (31-70), 2 = fraying (0-30)."""
    if sanity > SANITY_LUCID:
        return LUCID
    if sanity > SANITY_FRAYING:
        return UNEASY
    return FRAYING


def replace_fraction(sanity):
    """Fraction of letters that get replaced at a given sanity."""
    tier = sanity_tier(sanity)
    if tier == LUCID:
        return 0.0
    if tier == FRAYING:
        return 1.0
    # 70 -> 15%, 31 -> 50%, straight line in between
    low, high = UNEASY_REPLACE
    t = (SANITY_LUCID - sanity) / (SANITY_LUCID - SANITY_FRAYING - 1)
    return low + (high - low) * max(0.0, min(1.0, t))


def corrupt(text, sanity, rng=random):
    """Return the version of `text` the player has to type at this sanity."""
    frac = replace_fraction(sanity)
    if frac <= 0:
        return text
    chars = list(text)
    letter_positions = [i for i, c in enumerate(chars) if c.isalpha()]
    if frac >= 1.0:
        # Garbled nonsense: every letter is random, and words split in odd
        # places, but the length stays the same so longer spells stay longer.
        out = [" " if c == " " else rng.choice(LETTERS) for c in chars]
        # move the gaps around: drop old spaces, add new ones elsewhere
        for i in range(1, len(out) - 1):
            if out[i] == " " and rng.random() < 0.5:
                out[i] = rng.choice(LETTERS)
            elif (out[i] != " " and out[i - 1] != " " and out[i + 1] != " "
                  and rng.random() < 0.06):
                out[i] = " "
        return "".join(out)
    count = max(1, round(len(letter_positions) * frac))
    for i in rng.sample(letter_positions, min(count, len(letter_positions))):
        original = chars[i]
        choice = rng.choice(LETTERS)
        while choice == original:
            choice = rng.choice(LETTERS)
        chars[i] = choice
    return "".join(chars)


# --- Defense words ----------------------------------------------------------
EASY_WORDS = ["duck", "roll", "dash", "dive", "hide", "veer", "slip", "bend",
              "jump", "flee", "turn", "move"]
MEDIUM_WORDS = ["deflect", "sidestep", "parry", "evade", "recoil", "swerve",
                "tumble", "shelter", "withdraw", "scramble", "brace"]
HARD_WORDS = ["hold fast my soul", "not today", "break the fang",
              "unravel the dark", "shield of ash", "turn the blade",
              "the light holds", "stay behind me", "i will not fall",
              "counterspell"]


def defense_prompt(hp_fraction, rng=random, time_scale=1.0):
    """Pick a (word, time_limit) pair. Lower health (sanity) = harder prompt.

    Longer words get more time, but the typing speed asked of you climbs as
    sanity drops (see DEFEND_SPEED in settings.py). time_scale stretches the
    time allowed (the difficulty level sets it).
    """
    if hp_fraction > 0.75:
        word, step = rng.choice(EASY_WORDS), 0
    elif hp_fraction > 0.45:
        word, step = rng.choice(MEDIUM_WORDS), 1
    else:
        word, step = rng.choice(HARD_WORDS), 2
        if hp_fraction <= 0.2:
            # near death: the words start to slip
            word = corrupt(word, 60, rng)
    return word, (DEFEND_REACTION + len(word) / DEFEND_SPEED[step]) * time_scale
