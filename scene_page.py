"""Choosing a spell from a dropped page (like Balatro's boss-blind rewards).

The page's power depends on your sanity when you read it:
    lower sanity -> stronger potency, more choices, forbidden spells appear.

A boss's page is read first: one passage of the grimoire's story (lore.py),
with what earlier readers wrote beneath it if your sanity is low enough.
Then you turn it over and choose. When the grimoire is full, a new spell
can still be taken by crossing an old one out.
"""
import math
import random

import pygame

import art
import ui
from settings import (WIDTH, HEIGHT, WHITE, GRAY, GOLD, BONE, SANITY_COL,
                      ELEMENT_COLORS, FORBIDDEN_BELOW, MISS_COL, BLOOD)
from spells import (SPELLS, TIER_WEIGHT, effect_text, cost_text, OwnedSpell, page_potency,
                    page_choice_count)
from words import sanity_tier, TIER_NAMES
from lore import LORE, lore_index, truth_visible, LORE_TRUTH_BELOW


BURN_SANITY = 20


def weighted_sample(rng, items, weights, n):
    items, weights = list(items), list(weights)
    chosen = []
    while items and len(chosen) < n:
        pick = rng.choices(range(len(items)), weights=weights)[0]
        chosen.append(items.pop(pick))
        weights.pop(pick)
    return chosen


def effective_sanity(run):
    """The Black Candle makes pages read as if you were 15 sanity lower."""
    return max(0.0, run.sanity - (15 if run.has("candle") else 0))


def build_choices(run, unlocked, boss, rng):
    sanity = effective_sanity(run)
    potency = page_potency(sanity, boss)
    count = page_choice_count(sanity, boss)
    pool = []
    for key in unlocked:
        spell = SPELLS[key]
        if spell.tier == "forbidden" and sanity >= FORBIDDEN_BELOW:
            continue
        pool.append(key)        # a full grimoire can still take it: one is crossed out
    weights = []
    for key in pool:
        w = TIER_WEIGHT[SPELLS[key].tier]
        if boss and SPELLS[key].tier != "common":
            w += 2
        if run.get(key) is None:
            w += 1           # new spells are a little more likely than upgrades
        weights.append(w)
    keys = weighted_sample(rng, pool, weights, count)
    return potency, keys


INK = (40, 30, 30)
RED_INK = (120, 22, 26)
CROSS_TIME = 0.7          # seconds the pen takes to strike a spell out
TRUTH_SPEED = 45          # letters a second as the hidden writing shows through


def on_page(*args, **where):
    """Text written on the parchment: plain ink, no outline."""
    return ui.draw_text(*args, outline=False, **where)


class PageScene:
    music = "woods"
    pausable = False
    show_sanity_fx = True

    def __init__(self, game, boss, source_name, unlocked_now):
        self.game = game
        self.run = game.run
        self.boss = boss
        self.source_name = source_name
        self.unlocked_now = unlocked_now
        self.sanity = effective_sanity(self.run)
        self.potency, keys = build_choices(self.run, game.save.unlocked, boss, random.Random())
        self.options = [("spell", k) for k in keys] + [("burn", None)]
        self.selected = 0
        self.time = 0.0
        self.stage_time = 0.0
        # a boss page is read before it is used
        self.stage = "choose"
        self.lore = None
        if boss:
            index = lore_index(self.run.act)
            self.lore = (index, truth_visible(self.sanity))
            game.save.read_lore(index, self.lore[1])
            self.stage = "lore"
        self.new_key = None        # the spell waiting for a crossed-out slot
        self.cross_pick = 0
        self.crossing = None       # (key struck out, seconds the pen has been moving)
        # cyan while lucid, violet when uneasy, crimson when fraying
        self.look = art.HERO_LOOK[sanity_tier(self.sanity)]
        self.art = art.page_image(self.look, 250)
        game.sound.play("page")

    # --- input -------------------------------------------------------------------
    def menu_keys(self, event, count):
        """Up/Down/number/Enter on a list. Returns the chosen index, or None."""
        if event.key in (pygame.K_UP, pygame.K_w):
            self.game.sound.play("select")
            return ("move", -1)
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self.game.sound.play("select")
            return ("move", 1)
        if pygame.K_1 <= event.key <= pygame.K_9 and event.key - pygame.K_1 < count:
            return ("pick", event.key - pygame.K_1)
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return ("enter", None)
        return None

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.stage_time < 0.4 or self.crossing:
            return
        if self.stage == "lore":
            if self.stage_time < 0.8:
                return
            self.set_stage("choose")
            self.game.sound.play("page")
            return
        if self.stage == "cross":
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.set_stage("choose")
                self.game.sound.play("select")
                return
            count = len(self.run.grimoire) + 1          # the spells, then "never mind"
            action = self.menu_keys(event, count)
            if action is None:
                return
            kind, value = action
            if kind == "move":
                self.cross_pick = (self.cross_pick + value) % count
                return
            if kind == "pick":
                self.cross_pick = value
            self.cross_choose()
            return
        action = self.menu_keys(event, len(self.options))
        if action is None:
            return
        kind, value = action
        if kind == "move":
            self.selected = (self.selected + value) % len(self.options)
            return
        if kind == "pick":
            self.selected = value
        self.choose()

    def set_stage(self, stage):
        self.stage = stage
        self.stage_time = 0.0

    def choose(self):
        kind, key = self.options[self.selected]
        if kind == "burn":
            self.run.change_sanity(BURN_SANITY)
        elif self.run.get(key) is None and not self.run.has_room():
            # no room: he has to strike one out first
            self.new_key = key
            self.cross_pick = 0
            self.set_stage("cross")
            self.game.sound.play("page")
            return
        else:
            self.run.add_or_empower(key, self.potency)
        self.game.sound.play("heal")
        self.game.after_page(self.boss)

    def cross_choose(self):
        if self.cross_pick >= len(self.run.grimoire):        # never mind
            self.set_stage("choose")
            self.game.sound.play("select")
            return
        old = self.run.grimoire[self.cross_pick].key
        self.crossing = (old, 0.0)
        self.game.sound.play("burnout")                     # the scratch of the pen

    def update(self, dt):
        self.time += dt
        self.stage_time += dt
        if self.crossing:
            old, t = self.crossing
            t += dt
            self.crossing = (old, t)
            if t >= CROSS_TIME + 0.35:                        # a beat to see it struck out
                self.crossing = None
                self.run.cross_out(old, self.new_key, self.potency)
                self.game.sound.play("heal")
                self.game.after_page(self.boss)

    def draw_world(self, surface):
        surface.fill((10, 8, 14))
        # drifting ash
        for i in range(40):
            x = (i * 97 + self.time * (10 + i % 7) * 3) % WIDTH
            y = (i * 53 + self.time * (15 + i % 5) * 4) % HEIGHT
            pygame.draw.circle(surface, (60, 50, 60), (int(x), int(y)), 1 + i % 2)

    # --- drawing -----------------------------------------------------------------
    def draw_ui(self, surface):
        top = 20
        if self.unlocked_now:
            names = ", ".join(SPELLS[k].name for k in self.unlocked_now)
            ui.draw_text(surface, ui.font(28), f"Unlocked forever: {names}", GOLD,
                         center=(WIDTH // 2, top + 6))
            top += 22
        rect = self.draw_parchment(surface, top)
        tier = sanity_tier(self.sanity)
        title = (f"A page falls from {self.source_name}" if self.boss
                 else "A torn scrap drifts from the shadows")
        title = ui.fit(title, ui.font(36), rect.width - 30)
        on_page(surface, ui.font(36), title, INK, center=(rect.centerx, rect.top + 26))
        if self.stage == "lore":
            self.draw_lore(surface, rect)
        elif self.stage == "cross":
            self.draw_cross(surface, rect)
        else:
            sub = (f"Your mind: {TIER_NAMES[tier]} ({self.sanity:.0f} sanity)   "
                   f"potency x{self.potency:.2f}   {len(self.options) - 1} choices")
            on_page(surface, ui.font(22), sub, (90, 40, 110), center=(rect.centerx, rect.top + 52))
            self.draw_choices(surface, rect)

    def draw_parchment(self, surface, top):
        """The torn page, the dropped page's picture beside it. Returns the page's rect."""
        rect = pygame.Rect(WIDTH // 2 - 340, top + 14, 680, HEIGHT - top - 30)
        if self.art:
            # the dropped page floats on the left; the choices move right
            rect = pygame.Rect(266, top + 14, 680, HEIGHT - top - 30)
            bob = int(math.sin(self.time * 2) * 8)
            center = (134, HEIGHT // 2 + bob)
            halo = art.glow(150, [(90, 230, 240), (190, 110, 255), (255, 70, 70)][self.look], 150)
            surface.blit(halo, halo.get_rect(center=center))
            surface.blit(self.art, self.art.get_rect(center=center))
        rng = random.Random(7)
        pts = []
        for i in range(21):
            pts.append((rect.left + rect.width * i / 20, rect.top + rng.randint(-6, 6)))
        for i in range(21):
            pts.append((rect.right + rng.randint(-6, 4), rect.top + rect.height * i / 20))
        for i in range(21):
            pts.append((rect.right - rect.width * i / 20, rect.bottom + rng.randint(-6, 6)))
        for i in range(21):
            pts.append((rect.left + rng.randint(-4, 6), rect.bottom - rect.height * i / 20))
        pygame.draw.polygon(surface, (196, 182, 150), pts)
        pygame.draw.polygon(surface, (120, 100, 80), pts, 2)
        # blood drips at low sanity
        tier = sanity_tier(self.sanity)
        for i in range(tier * 4):
            dx = rect.left + 30 + (i * 151) % (rect.width - 60)
            length = 10 + ((i * 37) % 40) * min(1.0, self.time)
            pygame.draw.line(surface, BLOOD, (dx, rect.top), (dx, rect.top + length), 3)
        return rect

    def draw_lore(self, surface, rect):
        """The grimoire's passage, and what is written beneath it if he can see it."""
        index, truth = self.lore
        name, said, beneath = LORE[index]
        on_page(surface, ui.font(28), f"- {name} -", (90, 40, 110),
                center=(rect.centerx, rect.top + 60))
        width = rect.width - 90
        body = ui.font(26)
        y = rect.top + 92
        for line in ui.wrap(said, body, width):
            on_page(surface, body, line, INK, midtop=(rect.centerx, y))
            y += 28
        y += 14
        pygame.draw.line(surface, (150, 130, 100), (rect.centerx - 120, y), (rect.centerx + 120, y), 1)
        y += 18
        if truth:
            # the other writing shows through, a letter at a time, shaky at low sanity
            shown = int(max(0.0, self.stage_time - 0.8) * TRUTH_SPEED)
            jitter = [0, 0.5, 1.2][sanity_tier(self.sanity)]
            left = beneath[:shown]
            for line in ui.wrap(beneath, body, width):
                part, left = left[:len(line)], left[len(line):].lstrip(" ")
                if part:
                    x = rect.centerx - body.size(line)[0] // 2
                    dx = round(random.uniform(-jitter, jitter))
                    on_page(surface, body, part, RED_INK, topleft=(x + dx, y))
                y += 28
        else:
            faint = (150, 136, 112)
            for line in ui.wrap("Something else is written beneath, in other hands, too faint "
                                f"to read while your mind is this clear (below {LORE_TRUTH_BELOW} "
                                "sanity it would show).", ui.font(20), width):
                on_page(surface, ui.font(20), line, faint, midtop=(rect.centerx, y))
                y += 18
        if self.stage_time >= 0.8:
            on_page(surface, ui.font(20), "Any key: turn the page   (read it again in the codex)",
                    (90, 80, 70), center=(rect.centerx, rect.bottom - 14))

    def draw_choices(self, surface, rect):
        run = self.run
        y = rect.top + 72
        space = (rect.bottom - 30 - y) / len(self.options)
        row_h = min(66, space)
        for i, (kind, key) in enumerate(self.options):
            sel = i == self.selected
            box = pygame.Rect(rect.left + 24, y, rect.width - 48, row_h - 6)
            if sel:
                pygame.draw.rect(surface, (230, 214, 170), box, border_radius=6)
                pygame.draw.rect(surface, (120, 60, 40), box, 2, border_radius=6)
            if kind == "burn":
                on_page(surface, ui.font(26), f"[{i + 1}] Burn the page",
                        INK, topleft=(box.x + 10, box.y + 1))
                on_page(surface, ui.font(20),
                        f"Watch it curl to ash. +{BURN_SANITY} sanity.",
                        (60, 50, 50), topleft=(box.x + 10, box.y + 33))
            else:
                spell = SPELLS[key]
                owned = run.get(key)
                if owned:
                    preview = OwnedSpell(key, owned.level + 1, max(owned.potency, self.potency))
                    tag = f"Lv{owned.level} -> Lv{owned.level + 1}"
                    before = owned.strength()
                else:
                    preview = OwnedSpell(key, 1, self.potency)
                    tag = "New" if spell.tier != "forbidden" else "Forbidden"
                    if not run.has_room():
                        tag += ", cross one out"
                    before = None
                col = ELEMENT_COLORS[spell.element]
                dark = tuple(int(c * 0.55) for c in col)
                name = on_page(surface, ui.font(26), f"[{i + 1}] {spell.name}", dark,
                               topleft=(box.x + 10, box.y + 1))
                on_page(surface, ui.font(20), tag,
                        MISS_COL if spell.tier == "forbidden" else (120, 80, 30),
                        topleft=(name.right + 14, box.y + 11))
                stats = (f"{effect_text(spell.kind, preview.strength(), before)}   "
                         f"{cost_text(spell.sanity_cost)}")
                on_page(surface, ui.font(20), stats, INK, topright=(box.right - 10, box.y + 11))
                line = f"\"{spell.incantation}\"  ({spell.letters} letters) - {spell.desc}"
                line = ui.fit(line, ui.font(19), box.width - 20)
                on_page(surface, ui.font(19), line, (70, 60, 55),
                        topleft=(box.x + 10, box.y + 33))
            y += row_h
        hint = "Up/Down + Enter, or press a number"
        if not run.has_room():
            hint += "   (grimoire full: a new spell crosses one out)"
        on_page(surface, ui.font(20), hint, (90, 80, 70), center=(rect.centerx, rect.bottom - 14))

    def draw_cross(self, surface, rect):
        """The grimoire is full: pick the spell to strike out for the new one."""
        new = SPELLS[self.new_key]
        on_page(surface, ui.font(22),
                ui.fit(f"No room for {new.name}. Cross out a spell to write it in.",
                       ui.font(22), rect.width - 40),
                (90, 40, 110), center=(rect.centerx, rect.top + 52))
        grimoire = self.run.grimoire
        y = rect.top + 72
        count = len(grimoire) + 1
        row_h = min(48, (rect.bottom - 34 - y) / count)
        crossing_key = self.crossing[0] if self.crossing else None
        for i in range(count):
            sel = i == self.cross_pick
            box = pygame.Rect(rect.left + 24, round(y), rect.width - 48, round(row_h) - 6)
            if sel:
                pygame.draw.rect(surface, (230, 214, 170), box, border_radius=6)
                pygame.draw.rect(surface, (120, 60, 40), box, 2, border_radius=6)
            if i == len(grimoire):
                on_page(surface, ui.font(26), f"[{i + 1}] Never mind",
                        INK, midleft=(box.x + 10, box.centery))
                on_page(surface, ui.font(20), "Back to the page (Esc)", (90, 80, 70),
                        midright=(box.right - 10, box.centery))
                y += row_h
                continue
            owned = grimoire[i]
            spell = owned.defn
            dark = tuple(int(c * 0.55) for c in ELEMENT_COLORS[spell.element])
            name = on_page(surface, ui.font(26), f"[{i + 1}] {spell.name}  Lv{owned.level}", dark,
                           midleft=(box.x + 10, box.centery))
            on_page(surface, ui.font(19), ui.fit(f"\"{spell.incantation}\"", ui.font(19),
                                                 box.right - 10 - name.right - 20),
                    (70, 60, 55), midright=(box.right - 10, box.centery))
            if owned.key == crossing_key:
                # the pen strikes it out, left to right, in a shaky double line
                k = min(1.0, self.crossing[1] / CROSS_TIME)
                x0, x1 = box.x + 6, box.x + 6 + (box.width - 12) * k
                cy = box.centery
                pygame.draw.line(surface, RED_INK, (x0, cy - 2), (x1, cy + 1), 3)
                pygame.draw.line(surface, RED_INK, (x0 + 4, cy + 4), (x1, cy + 2), 2)
            y += row_h
        if not self.crossing:
            on_page(surface, ui.font(20), "Up/Down + Enter, or press a number   Esc: back",
                    (90, 80, 70), center=(rect.centerx, rect.bottom - 14))
