"""Choosing a spell from a dropped page (like Balatro's boss-blind rewards).

The page's power depends on your sanity when you read it:
    lower sanity -> stronger potency, more choices, forbidden spells appear.
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
        if run.get(key) is None and not run.has_room():
            continue
        pool.append(key)
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
        # cyan while calm, violet when shaken, crimson when mad
        self.look = art.HERO_LOOK[sanity_tier(self.sanity)]
        self.art = art.page_image(self.look, 250)
        game.sound.play("page")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.time < 0.4:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.options)
            self.game.sound.play("select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.options)
            self.game.sound.play("select")
        elif pygame.K_1 <= event.key <= pygame.K_9:
            i = event.key - pygame.K_1
            if i < len(self.options):
                self.selected = i
                self.choose()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.choose()

    def choose(self):
        kind, key = self.options[self.selected]
        if kind == "burn":
            self.run.change_sanity(BURN_SANITY)
        else:
            self.run.add_or_empower(key, self.potency)
        self.game.sound.play("heal")
        self.game.after_page(self.boss)

    def update(self, dt):
        self.time += dt

    def draw_world(self, surface):
        surface.fill((10, 8, 14))
        # drifting ash
        for i in range(40):
            x = (i * 97 + self.time * (10 + i % 7) * 3) % WIDTH
            y = (i * 53 + self.time * (15 + i % 5) * 4) % HEIGHT
            pygame.draw.circle(surface, (60, 50, 60), (int(x), int(y)), 1 + i % 2)

    def draw_ui(self, surface):
        run = self.run
        top = 20
        if self.unlocked_now:
            names = ", ".join(SPELLS[k].name for k in self.unlocked_now)
            ui.draw_text(surface, ui.font(28), f"Unlocked forever: {names}", GOLD,
                         center=(WIDTH // 2, top + 6))
            top += 22
        # torn parchment
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

        ink = (40, 30, 30)

        def on_page(*args, **where):
            """Text written on the parchment: plain ink, no outline."""
            return ui.draw_text(*args, outline=False, **where)

        title = (f"A page falls from {self.source_name}" if self.boss
                 else "A torn scrap drifts from the shadows")
        title = ui.fit(title, ui.font(36), rect.width - 30)
        on_page(surface, ui.font(36), title, ink, center=(rect.centerx, rect.top + 26))
        sub = (f"Your mind: {TIER_NAMES[tier]} ({self.sanity:.0f} sanity)   "
               f"potency x{self.potency:.2f}   {len(self.options) - 1} choices")
        on_page(surface, ui.font(22), sub, (90, 40, 110), center=(rect.centerx, rect.top + 52))

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
                        ink, topleft=(box.x + 10, box.y + 1))
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
                on_page(surface, ui.font(20), stats, ink, topright=(box.right - 10, box.y + 11))
                line = f"\"{spell.incantation}\"  ({spell.letters} letters) - {spell.desc}"
                line = ui.fit(line, ui.font(19), box.width - 20)
                on_page(surface, ui.font(19), line, (70, 60, 55),
                        topleft=(box.x + 10, box.y + 33))
            y += row_h
        hint = "Up/Down + Enter, or press a number"
        if not run.has_room():
            hint += "   (grimoire full: only upgrades)"
        on_page(surface, ui.font(20), hint, (90, 80, 70), center=(rect.centerx, rect.bottom - 14))
