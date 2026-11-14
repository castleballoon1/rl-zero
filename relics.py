"""Relics: passive charms found at campfires between acts (pure data)."""

RELICS = {
    "lens": ("Cracked Lens", "Crits deal x2.5 instead of x2."),
    "ink": ("Ink of the Deep", "Spells cost 25% less sanity."),
    "scarf": ("Moth-eaten Scarf", "+0.7 s on every DEFEND word."),
    "charm": ("Bone Charm", "+25 maximum health."),
    "candle": ("Black Candle", "Pages read as if you had 15 less sanity."),
    "bell": ("Quiet Bell", "Foes wait 3 s longer before their first attack."),
    "thimble": ("Thorned Thimble", "Deflects return all the damage, not half."),
    "heartwood": ("Heartwood Splinter", "Heal 8 health after every fight."),
}


def offer(owned, rng, count):
    """Pick `count` relics the player does not have yet."""
    pool = [key for key in RELICS if key not in owned]
    rng.shuffle(pool)
    return pool[:count]
