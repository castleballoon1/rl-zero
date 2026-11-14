"""Word corruption and defense words (pure Python, no pygame).

High sanity -> the incantation is shown spelled correctly.
Lower sanity -> some letters are replaced, and you must type what you SEE.
Extremely low sanity -> the incantation becomes garbled nonsense.
"""
import random
import string

from settings import SANITY_LUCID, SANITY_FRAYING, SANITY_MAD

LETTERS = string.ascii_lowercase

TIER_NAMES = ["Lucid", "Uneasy", "Fraying", "Mad"]


def sanity_tier(sanity):
    """0 = lucid, 1 = uneasy, 2 = fraying, 3 = mad."""
    if sanity >= SANITY_LUCID:
        return 0
    if sanity >= SANITY_FRAYING:
        return 1
    if sanity >= SANITY_MAD:
        return 2
    return 3


def replace_fraction(sanity):
    """Fraction of letters that get replaced at a given sanity."""
    if sanity >= SANITY_LUCID:
        return 0.0
    if sanity < SANITY_MAD:
        return 1.0
    # 70 -> 10%, 15 -> 55%, straight line in between
    t = (SANITY_LUCID - sanity) / (SANITY_LUCID - SANITY_MAD)
    return 0.10 + 0.45 * t


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


def defense_prompt(hp_fraction, rng=random):
    """Pick a (word, time_limit) pair. Lower health = harder prompt.

    The time limit grows a little for long words but much less than the
    word length does, so the needed typing speed climbs as health drops.
    """
    if hp_fraction > 0.66:
        return rng.choice(EASY_WORDS), 2.4
    if hp_fraction > 0.33:
        return rng.choice(MEDIUM_WORDS), 2.6
    word = rng.choice(HARD_WORDS)
    if hp_fraction <= 0.15:
        # near death: the words start to slip
        word = corrupt(word, 60, rng)
    return word, 3.4
