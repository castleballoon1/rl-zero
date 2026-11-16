"""The state of one run, plus permanent unlocks saved between runs.

Permadeath: the RunState (health, sanity, grimoire) is thrown away on death.
Only the SaveData (unlocked spells, stats) survives.
"""
import json
import os
import random

from settings import (START_SANITY, MAX_SANITY, MAX_SHIELD,
                      GRIMOIRE_SIZE, SAVE_FILE)
from spells import OwnedSpell, STARTER_SPELLS, SPELLS, default_unlocked


class SaveData:
    def __init__(self, path=SAVE_FILE):
        self.path = path
        self.unlocked = default_unlocked()
        self.runs = 0
        self.wins = 0
        self.best_act = 0
        self.best_score = 0
        self.load()

    def load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for key in data.get("unlocked", []):
            if key in SPELLS and key not in self.unlocked:
                self.unlocked.append(key)
        self.runs = int(data.get("runs", 0))
        self.wins = int(data.get("wins", 0))
        self.best_act = int(data.get("best_act", 0))
        self.best_score = int(data.get("best_score", 0))

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(dict(unlocked=self.unlocked, runs=self.runs,
                               wins=self.wins, best_act=self.best_act,
                               best_score=self.best_score), f,
                          indent=2)
        except OSError:
            pass

    def unlock(self, key):
        """Unlock a spell. Returns True if it was new."""
        if key in SPELLS and key not in self.unlocked:
            self.unlocked.append(key)
            self.save()
            return True
        return False


class RunState:
    def __init__(self, name, seed):
        self.name = name or "Lost Boy"
        self.seed = seed if seed else str(random.randint(10000, 99999))
        self.max_sanity = MAX_SANITY
        self.sanity = START_SANITY     # his only health
        self.shield = 0.0
        self.act = 1
        self.grimoire = [OwnedSpell(k) for k in STARTER_SPELLS]
        self.cleared = set()       # encounter indices cleared in this act
        self.shrines_used = set()
        self.relics = []           # keys from relics.RELICS
        self.focus = 0             # streak of clean casts
        self.won = False
        # stats for the end screen
        self.kills = 0
        self.casts = 0
        self.keys_ok = 0
        self.keys_miss = 0
        self.best_hit = 0
        self.deflects = 0
        self.new_unlocks = []

    # --- helpers ---------------------------------------------------------
    def get(self, key):
        for s in self.grimoire:
            if s.key == key:
                return s
        return None

    def has(self, relic):
        return relic in self.relics

    def add_relic(self, key):
        if key not in self.relics:
            self.relics.append(key)
            if key == "charm":
                self.max_sanity += 20
                self.sanity += 20

    def score(self):
        return (self.kills * 40 + self.casts * 5 + self.deflects * 25
                + (self.act - 1) * 400 + int(self.accuracy * 200)
                + (1000 if self.won else 0))

    def has_room(self):
        return len(self.grimoire) < GRIMOIRE_SIZE

    def add_or_empower(self, key, potency):
        owned = self.get(key)
        if owned:
            owned.empower(potency)
        elif self.has_room():
            self.grimoire.append(OwnedSpell(key, 1, potency))

    def change_sanity(self, amount):
        """Gain sanity, or pay it. Paying can never kill: it stops at 1.

        Spell costs, a staring eye and a tolling bell all go through here.
        Only hurt() can take the last point.
        """
        floor = min(1.0, self.sanity)
        self.sanity = max(floor, min(self.max_sanity, self.sanity + amount))

    def add_shield(self, amount):
        self.shield = min(MAX_SHIELD, self.shield + amount)

    def hurt(self, amount):
        """A blow. The shield absorbs first. Returns the sanity actually lost."""
        absorbed = min(self.shield, amount)
        self.shield -= absorbed
        lost = min(self.sanity, amount - absorbed)
        self.sanity -= lost
        return lost

    @property
    def accuracy(self):
        total = self.keys_ok + self.keys_miss
        return self.keys_ok / total if total else 1.0

    @property
    def dead(self):
        return self.sanity <= 0

    def next_act(self):
        self.act += 1
        self.cleared = set()
        self.shrines_used = set()
