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
BURN_FRAME = 0.2          # seconds per picture as a burned page curls to ash
BURN_HOLD = 0.45          # ... and the pause on the ash before moving on
# how much of the page (from the top) is still unburnt in each burning picture;
# the writing is cut off at that line, so it burns away with the paper
BURN_LEFT = [1.0, 1.0, 0.85, 0.66, 0.38, 0.12, 0.0]

# The painted page keeps its own shape (art.PAGE_BOX is 306 x 394). Its purple
# corner brackets frame the writing: every word on the page stays inside this
# box, given as shares of the page's width and height (left, top, right, bottom).
PAGE_TEXT = (0.20, 0.155, 0.80, 0.865)
SIDE_GAP = 12             # between the page and the panel beside it


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
        if (event.type != pygame.KEYDOWN or self.stage_time < 0.4 or self.crossing
                or self.stage in ("burning", "burnt")):
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
            if self.parchment_ok():
                # it catches, burns up from the bottom, and is ash (update finishes it)
                self.set_stage("burning")
                self.game.sound.play("cast_fire")
                return
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

    def parchment_ok(self):
        return art.parchment_frames(*self.page_size()) is not None

    def update(self, dt):
        self.time += dt
        self.stage_time += dt
        if self.stage == "burning":
            done = BURN_FRAME * (art.PAGE_FRAMES - 1) + BURN_HOLD
            if self.stage_time >= done:
                self.stage = "burnt"            # once only
                self.run.change_sanity(BURN_SANITY)
                self.game.sound.play("heal")
                self.game.after_page(self.boss)
            return
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
        top = 12
        if self.unlocked_now:
            names = ", ".join(SPELLS[k].name for k in self.unlocked_now)
            ui.draw_text(surface, ui.font(28), f"Unlocked forever: {names}", GOLD,
                         center=(WIDTH // 2, top + 8))
            top += 24
        rect = self.page_rect(top + 56)
        # the heading and the line under it sit above the page and the panel
        tier = sanity_tier(self.sanity)
        title = (f"A page falls from {self.source_name}" if self.boss
                 else "A torn scrap drifts from the shadows")
        x_mid = (rect.left + WIDTH - 10) // 2
        span = WIDTH - 10 - rect.left
        ui.draw_text(surface, ui.font(36), ui.fit(title, ui.font(36), span), BONE,
                     center=(x_mid, top + 14))
        if self.stage in ("burning", "burnt"):
            sub = f"It curls to ash. +{BURN_SANITY} sanity."
        elif self.stage == "cross":
            sub = f"No room for {SPELLS[self.new_key].name}. Cross out a spell to write it in."
        elif self.stage == "lore":
            sub = "Something is written on it."
        else:
            sub = (f"Your mind: {TIER_NAMES[tier]} ({self.sanity:.0f} sanity)   "
                   f"potency x{self.potency:.2f}   {len(self.options) - 1} choices")
            if not self.run.has_room():
                sub += "   grimoire full"
        ui.draw_text(surface, ui.font(22), ui.fit(sub, ui.font(22), span), (200, 170, 230),
                     center=(x_mid, top + 40))
        self.draw_parchment(surface, rect)
        text = self.text_box(rect)
        side = pygame.Rect(rect.right + SIDE_GAP, rect.top + round(rect.height * 0.1),
                           WIDTH - 10 - rect.right - SIDE_GAP, round(rect.height * 0.8))
        if self.stage == "lore":
            self.draw_lore(surface, text)
            self.draw_side(surface, side, None, "Any key: turn the page" if self.stage_time >= 0.8 else "")
        elif self.stage == "cross":
            self.draw_cross(surface, text)
            pick = self.cross_pick
            owned = self.run.grimoire[pick] if pick < len(self.run.grimoire) else None
            self.draw_side(surface, side, ("owned", owned) if owned else ("back", None),
                           "Up/Down + Enter, or a number   Esc: back")
        elif self.stage in ("burning", "burnt"):
            # the writing burns away with the paper: only what is above the flames shows
            left = BURN_LEFT[min(len(BURN_LEFT) - 1, self.burn_index())]
            if left > 0:
                surface.set_clip(pygame.Rect(rect.left, rect.top, rect.width,
                                             round(rect.height * left)))
                self.draw_choices(surface, text)
                surface.set_clip(None)
        else:
            self.draw_choices(surface, text)
            self.draw_side(surface, side, self.options[self.selected],
                           "Up/Down + Enter, or a number")

    def burn_index(self):
        """Which burning picture shows now (1 to the last)."""
        return min(art.PAGE_FRAMES - 1, 1 + int(self.stage_time / BURN_FRAME))

    def page_size(self, top=None):
        """The page at its painted shape, as tall as the screen allows."""
        top = (12 + (24 if self.unlocked_now else 0) + 56) if top is None else top
        height = HEIGHT - top - 8
        _, _, w, h = art.PAGE_BOX
        return round(height * w / h), height

    def page_rect(self, top):
        w, h = self.page_size(top)
        return pygame.Rect(266 if self.art else 120, top, w, h)

    def text_box(self, rect):
        """Where words may go: inside the page's purple corner brackets."""
        l, t, r, b = PAGE_TEXT
        x0, x1 = rect.left + round(rect.width * l), rect.left + round(rect.width * r)
        y0, y1 = rect.top + round(rect.height * t), rect.top + round(rect.height * b)
        return pygame.Rect(x0, y0, x1 - x0, y1 - y0)

    def draw_parchment(self, surface, rect):
        """The page, and the dropped page's picture floating beside it."""
        if self.art:
            bob = int(math.sin(self.time * 2) * 8)
            center = (134, HEIGHT // 2 + bob)
            halo = art.glow(150, [(90, 230, 240), (190, 110, 255), (255, 70, 70)][self.look], 150)
            surface.blit(halo, halo.get_rect(center=center))
            surface.blit(self.art, self.art.get_rect(center=center))
        frames = art.parchment_frames(rect.width, rect.height)
        if frames:
            index = 0
            if self.stage in ("burning", "burnt"):
                index = self.burn_index()
                glow = art.glow(220, (255, 140, 50), int(10 * max(0.0, 1 - self.stage_time / 1.4)) * 15)
                surface.blit(glow, glow.get_rect(center=(rect.centerx, rect.bottom - 60)))
            surface.blit(frames[index], rect)
        else:
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
        # blood drips at low sanity (not once it is burning)
        if self.stage not in ("burning", "burnt"):
            tier = sanity_tier(self.sanity)
            edge = rect.top + round(rect.height * 0.04)
            for i in range(tier * 4):
                dx = rect.left + 50 + (i * 151) % (rect.width - 100)
                length = 10 + ((i * 37) % 40) * min(1.0, self.time)
                pygame.draw.line(surface, BLOOD, (dx, edge), (dx, edge + length), 3)

    # --- the panel beside the page: the chosen line in full, and the keys ----------
    def draw_side(self, surface, box, option, hint):
        ui.panel(surface, box, 225)
        x, width = box.x + 22, box.width - 44
        y = box.y + 22
        small = ui.font(19)

        def lines(text, color, gap=16):
            nonlocal y
            for line in ui.wrap(text, small, width):
                ui.draw_text(surface, small, line, color, topleft=(x, y))
                y += gap
            y += 6

        if option is None:              # the lore: no choice yet
            lines("Read the page. When you turn it over, you choose what to take "
                  "from it.", GRAY)
        else:
            kind, key = option
            if kind == "burn":
                ui.draw_text(surface, ui.font(26), "Burn the page", (255, 170, 90), topleft=(x, y))
                y += 34
                lines(f"Watch it curl to ash. +{BURN_SANITY} sanity, and no spell.", WHITE)
            elif kind == "back":
                ui.draw_text(surface, ui.font(26), "Never mind", WHITE, topleft=(x, y))
                y += 34
                lines("Keep every spell, and go back to the page.", GRAY)
            else:
                if kind == "owned":
                    owned = key
                    spell, key = owned.defn, owned.key
                    head = f"Lv{owned.level}"
                    stats = f"{effect_text(spell.kind, owned.strength())}   {cost_text(spell.sanity_cost)}"
                else:
                    spell = SPELLS[key]
                    owned = self.run.get(key)
                    if owned:
                        preview = OwnedSpell(key, owned.level + 1, max(owned.potency, self.potency))
                        head = f"Lv{owned.level} -> Lv{owned.level + 1}"
                        before = owned.strength()
                    else:
                        preview = OwnedSpell(key, 1, self.potency)
                        head = "New" if spell.tier != "forbidden" else "Forbidden"
                        if not self.run.has_room():
                            head += ", cross one out"
                        before = None
                    stats = (f"{effect_text(spell.kind, preview.strength(), before)}   "
                             f"{cost_text(spell.sanity_cost)}")
                col = ELEMENT_COLORS[spell.element]
                name = ui.fit(spell.name, ui.font(26), width)
                ui.draw_text(surface, ui.font(26), name, col, topleft=(x, y))
                y += 32
                lines(f"{head}   ({spell.element}, {spell.tier})",
                      MISS_COL if spell.tier == "forbidden" else GOLD)
                lines(stats, WHITE)
                lines(f'Type "{spell.incantation}" ({spell.letters} letters)', SANITY_COL)
                lines(spell.desc, GRAY)
                if kind == "owned":
                    lines("Crossed out, it is gone from the grimoire.", (230, 120, 120))
        if hint:
            for i, line in enumerate(reversed(ui.wrap(hint, ui.font(20), width))):
                ui.draw_text(surface, ui.font(20), line, GRAY,
                             midbottom=(box.centerx, box.bottom - 18 - i * 17))

    # --- the page -----------------------------------------------------------------
    def draw_lore(self, surface, text):
        """The grimoire's passage, and what is written beneath it if he can see it."""
        index, truth = self.lore
        name, said, beneath = LORE[index]
        y = text.top
        on_page(surface, ui.font(26), ui.fit(name, ui.font(26), text.width), (90, 40, 110),
                midtop=(text.centerx, y))
        y += 36
        body = ui.font(20)
        for line in ui.wrap(said, body, text.width):
            on_page(surface, body, line, INK, midtop=(text.centerx, y))
            y += 18
        y += 10
        pygame.draw.line(surface, (150, 130, 100), (text.centerx - 60, y), (text.centerx + 60, y), 1)
        y += 12
        if truth:
            # the other writing shows through, a letter at a time, shaky at low sanity
            shown = int(max(0.0, self.stage_time - 0.8) * TRUTH_SPEED)
            jitter = [0, 0.5, 1.2][sanity_tier(self.sanity)]
            left = beneath[:shown]
            for line in ui.wrap(beneath, body, text.width):
                part, left = left[:len(line)], left[len(line):].lstrip(" ")
                if part:
                    x = text.centerx - body.size(line)[0] // 2
                    dx = round(random.uniform(-jitter, jitter))
                    on_page(surface, body, part, RED_INK, topleft=(x + dx, y))
                y += 18
        else:
            for line in ui.wrap("Something else is written beneath, in other hands, too "
                                "faint to read while your mind is this clear. Below "
                                f"{LORE_TRUTH_BELOW} sanity it would show.", body, text.width):
                on_page(surface, body, line, (150, 136, 112), midtop=(text.centerx, y))
                y += 18

    def draw_choices(self, surface, text):
        """One line for each choice, its name and what typing it takes."""
        run = self.run
        row_h = min(64, text.height / len(self.options))
        y = text.top
        for i, (kind, key) in enumerate(self.options):
            box = pygame.Rect(text.left - 6, round(y), text.width + 12, round(row_h) - 4)
            if i == self.selected:
                pygame.draw.rect(surface, (230, 214, 170), box, border_radius=6)
                pygame.draw.rect(surface, (120, 60, 40), box, 2, border_radius=6)
            second = box.y + min(32, box.height - 15)
            if kind == "burn":
                on_page(surface, ui.font(26), ui.fit(f"[{i + 1}] Burn the page", ui.font(26),
                                                     text.width), INK, topleft=(text.left, box.y + 2))
                on_page(surface, ui.font(19), f"+{BURN_SANITY} sanity", (60, 50, 50),
                        topleft=(text.left, second))
            else:
                spell = SPELLS[key]
                owned = run.get(key)
                if owned:
                    tag = f"Lv{owned.level} -> Lv{owned.level + 1}"
                else:
                    tag = "New" if spell.tier != "forbidden" else "Forbidden"
                dark = tuple(int(c * 0.55) for c in ELEMENT_COLORS[spell.element])
                on_page(surface, ui.font(26), ui.fit(f"[{i + 1}] {spell.name}", ui.font(26),
                                                     text.width), dark, topleft=(text.left, box.y + 2))
                line = ui.fit(f'"{spell.incantation}"  {tag}', ui.font(19), text.width)
                on_page(surface, ui.font(19), line,
                        MISS_COL if spell.tier == "forbidden" else (90, 60, 40),
                        topleft=(text.left, second))
            y += row_h

    def draw_cross(self, surface, text):
        """The grimoire is full: pick the spell to strike out for the new one."""
        grimoire = self.run.grimoire
        count = len(grimoire) + 1
        row_h = min(48, text.height / count)
        y = text.top
        crossing_key = self.crossing[0] if self.crossing else None
        for i in range(count):
            box = pygame.Rect(text.left - 6, round(y), text.width + 12, round(row_h) - 4)
            if i == self.cross_pick:
                pygame.draw.rect(surface, (230, 214, 170), box, border_radius=6)
                pygame.draw.rect(surface, (120, 60, 40), box, 2, border_radius=6)
            if i == len(grimoire):
                on_page(surface, ui.font(26), f"[{i + 1}] Never mind", INK,
                        midleft=(text.left, box.centery))
                y += row_h
                continue
            owned = grimoire[i]
            spell = owned.defn
            dark = tuple(int(c * 0.55) for c in ELEMENT_COLORS[spell.element])
            on_page(surface, ui.font(26), ui.fit(f"[{i + 1}] {spell.name} Lv{owned.level}",
                                                 ui.font(26), text.width),
                    dark, midleft=(text.left, box.centery))
            if owned.key == crossing_key:
                # the pen strikes it out, left to right, in a shaky double line
                k = min(1.0, self.crossing[1] / CROSS_TIME)
                x0, x1 = box.x + 4, box.x + 4 + (box.width - 8) * k
                cy = box.centery
                pygame.draw.line(surface, RED_INK, (x0, cy - 2), (x1, cy + 1), 3)
                pygame.draw.line(surface, RED_INK, (x0 + 4, cy + 4), (x1, cy + 2), 2)
            y += row_h
