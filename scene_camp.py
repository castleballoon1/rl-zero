"""The campfire between acts: rest, study a spell, or take a relic."""
import math
import random

import pygame

import art
import ui
from relics import RELICS, offer
from settings import (WIDTH, HEIGHT, WHITE, GRAY, GOLD, BONE, GREEN,
                      SANITY_COL, ELEMENT_COLORS, REST_SANITY, GROUND_Y)

FIRE = (330, GROUND_Y - 4)


class CampScene:
    music = "woods"
    pausable = False
    show_sanity_fx = True

    def __init__(self, game):
        self.game = game
        self.run = game.run
        self.time = 0.0
        self.mode = "main"           # "main" or "study"
        self.selected = 0
        relic_keys = offer(self.run.relics, random.Random(), 2)
        self.options = [("rest", None), ("study", None)]
        self.options += [("relic", key) for key in relic_keys]
        self.hero = art.hero_frames(120)
        self.fire_frames = art.campfire_frames(art.CAMPFIRE_TALL)
        self.scene = art.forest_scene()
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((4, 2, 10, 170))
        game.sound.play("heal")

    def rows(self):
        """(title, detail, colour) for every row of the current list."""
        if self.mode == "study":
            rows = []
            for owned in self.run.grimoire:
                before = owned.strength()
                after = before / (1 + 0.3 * (owned.level - 1)) * (1 + 0.3 * owned.level)
                rows.append((f"{owned.defn.name}  Lv{owned.level + 1}",
                             f"{before:.0f} -> {after:.0f}",
                             ELEMENT_COLORS[owned.defn.element]))
            return rows
        rows = []
        for kind, key in self.options:
            if kind == "rest":
                rows.append(("Rest by the fire", f"Regain {REST_SANITY} sanity", GREEN))
            elif kind == "study":
                rows.append(("Study the grimoire", "Raise one spell by a level", SANITY_COL))
            else:
                name, desc = RELICS[key]
                rows.append((name, "Relic: " + desc, GOLD))
        return rows

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.time < 0.4:
            return
        count = len(self.rows())
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % count
            self.game.sound.play("select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % count
            self.game.sound.play("select")
        elif pygame.K_1 <= event.key <= pygame.K_9 and event.key - pygame.K_1 < count:
            self.selected = event.key - pygame.K_1
            self.choose()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.choose()
        elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) and self.mode == "study":
            self.mode = "main"
            self.selected = 1

    def choose(self):
        if self.mode == "study":
            self.run.grimoire[self.selected].level += 1
        else:
            kind, key = self.options[self.selected]
            if kind == "study":
                self.mode = "study"
                self.selected = 0
                self.game.sound.play("select")
                return
            if kind == "rest":
                self.run.change_sanity(REST_SANITY)
            else:
                self.run.add_relic(key)
        self.game.sound.play("page")
        self.game.leave_camp()

    def update(self, dt):
        self.time += dt

    def draw_world(self, surface):
        if self.scene:
            self.scene.draw(surface, self.run.act, 900, self.time)
            surface.blit(self.shade, (0, 0))     # night closes in around the fire
        else:
            surface.fill((8, 8, 14))
            pygame.draw.rect(surface, (16, 18, 16), (0, FIRE[1] + 8, WIDTH, HEIGHT))
        flicker = int(6 * math.sin(self.time * 9) + 3 * math.sin(self.time * 23))
        light = art.glow(230 + flicker, (255, 150, 60), 150)
        surface.blit(light, light.get_rect(center=FIRE))
        if self.fire_frames:
            fire = self.fire_frames[int(self.time / art.FIRE_FRAME_TIME) % len(self.fire_frames)]
        else:
            fire = art.campfire_surface(int(self.time * 10))
        surface.blit(fire, fire.get_rect(midbottom=(FIRE[0], FIRE[1] + 8)))
        boy = art.hero_poses(self.hero, self.run.sanity, self.run.max_sanity)["idle"]
        surface.blit(boy, boy.get_rect(midbottom=(FIRE[0] - 120, FIRE[1] + 10)))
        # sparks
        for i in range(12):
            life = (self.time * 0.5 + i / 12) % 1
            x = FIRE[0] + math.sin(i * 2.4 + self.time) * 30 * life
            y = FIRE[1] - 40 - life * 200
            pygame.draw.circle(surface, (255, 190, 90), (x, y), 2 if life < 0.5 else 1)

    def draw_ui(self, surface):
        self.game.draw_hud(surface)
        ui.draw_text(surface, ui.font(44), "A clearing. A fire. A moment.", BONE,
                     center=(WIDTH // 2, 110))
        head = ("Choose one before the woods close in again" if self.mode == "main"
                else "Which spell do you study?")
        ui.draw_text(surface, ui.font(24), head, GRAY, center=(WIDTH // 2, 145))
        rows = self.rows()
        tall = len(rows) <= 5
        row_h = 62 if tall else 44
        x, y = 500, 180
        for i, (title, detail, color) in enumerate(rows):
            box = pygame.Rect(x, y + i * row_h, 430, row_h - 6)
            sel = i == self.selected
            ui.panel(surface, box, 230 if sel else 150, border=GOLD if sel else None)
            ui.draw_text(surface, ui.font(26), f"[{i + 1}] {title}", color if sel else WHITE,
                         topleft=(box.x + 14, box.y + 6))
            if tall:
                ui.draw_text(surface, ui.font(19), ui.fit(detail, ui.font(19), 400), GRAY,
                             topleft=(box.x + 14, box.y + 35))
            else:
                ui.draw_text(surface, ui.font(19), detail, GRAY,
                             midright=(box.right - 14, box.centery))
        if self.run.relics:
            names = ", ".join(RELICS[k][0] for k in self.run.relics)
            ui.draw_text(surface, ui.font(20), ui.fit("Relics: " + names, ui.font(20), WIDTH - 40),
                         GOLD, center=(WIDTH // 2, HEIGHT - 44))
        hint = "Up/Down + Enter, or press a number"
        if self.mode == "study":
            hint += "   Esc: back"
        ui.draw_text(surface, ui.font(20), hint, GRAY, center=(WIDTH // 2, HEIGHT - 20))
