"""Spell Typer - entry point.

Run with:  python main.py

The Game object owns the window, the clock, the current scene and the run.
Each scene (title, woods, combat, page, end) is one state of a finite state
machine and has the same four methods: handle_event, update, draw_world and
draw_ui. The main loop is: read input -> update -> draw -> flip and wait.
"""
import math
import os
import random

import pygame

from settings import (WIDTH, HEIGHT, FPS, MAX_DT, TITLE, WHITE, GRAY, GOLD,
                      BONE, HP_COL, SANITY_COL, SHIELD_COL, SANITY_LUCID,
                      SANITY_FRAYING, SANITY_MAD, MAX_SANITY, MAX_SHIELD)

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# These imports need the display to exist (images are converted on load).
import art  # noqa: E402
import ui  # noqa: E402


def show_loading(text):
    """Cutting the creature sheets takes a moment, so say what is happening."""
    screen.fill((14, 10, 22))
    ui.draw_text(screen, ui.font(56), TITLE, BONE, center=(WIDTH // 2, HEIGHT // 2 - 40))
    ui.draw_text(screen, ui.font(28), text, GRAY, center=(WIDTH // 2, HEIGHT // 2 + 20))
    pygame.display.flip()
    pygame.event.pump()      # keeps the window responsive while loading


art.preload(show_loading)

from bestiary import ACTS, FINAL_ACT  # noqa: E402
from entities import FloatingText  # noqa: E402
from relics import RELICS  # noqa: E402
from run_state import RunState, SaveData  # noqa: E402
from scene_camp import CampScene  # noqa: E402
from scene_combat import CombatScene  # noqa: E402
from scene_explore import ExploreScene  # noqa: E402
from scene_menus import TitleScene, EndScene  # noqa: E402
from scene_page import PageScene  # noqa: E402
from sound import Sound  # noqa: E402
from spells import SPELLS  # noqa: E402
from words import sanity_tier, TIER_NAMES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

BOSS_UNLOCKS = {1: ["drain"], 2: ["chain", "hourglass"], 3: ["hymn"]}
MADNESS_UNLOCK = "gaze"

WHISPERS = ["turn back", "it sees you", "the words are wrong", "you were never here",
            "read it again", "who wrote this", "they are under the page",
            "do you remember your name", "keep typing", "it is behind you"]


class Game:
    def __init__(self):
        self.screen = screen
        self.world = pygame.Surface((WIDTH, HEIGHT))
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))
        self.sound = Sound()
        self.sound.start_music()
        self.save = SaveData(os.path.join(HERE, "save.json"))
        self.run = None
        self.explore = None
        self.running = True
        self.paused = False
        self.pause_selected = 0
        self.shake = 0.0
        self.shake_power = 0.0
        self.time = 0.0
        self.whispers = []
        self.whisper_timer = 2.0
        self.ui_floaters = []
        self.red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((0, 0, 0, 225))
        self.scene = TitleScene(self)

    # --- state changes ----------------------------------------------------------
    def change(self, scene):
        self.scene = scene
        self.paused = False

    def start_run(self, name, seed):
        self.run = RunState(name, seed)
        self.save.runs += 1
        self.save.best_act = max(self.save.best_act, 1)
        self.save.save()
        self.explore = ExploreScene(self)
        self.change(self.explore)

    def start_combat(self, enemy_datas, boss, encounter_index):
        self.change(CombatScene(self, enemy_datas, boss, encounter_index))

    def unlock(self, key):
        if self.save.unlock(key):
            self.run.new_unlocks.append(key)
            return [key]
        return []

    def achieve(self, key):
        """Unlock a spell in the middle of play and announce it."""
        if self.unlock(key):
            self.sound.play("page")
            self.ui_floaters.append(FloatingText(
                f"Spell unlocked forever: {SPELLS[key].name}", (WIDTH // 2, 250), GOLD,
                34, 3.0, 12))

    def finish_run(self):
        """Record the score when a run ends, however it ends."""
        self.save.best_score = max(self.save.best_score, self.run.score())
        self.save.save()

    def leave_camp(self):
        run = self.run
        run.next_act()
        self.save.best_act = max(self.save.best_act, run.act)
        self.save.save()
        self.explore = ExploreScene(self)
        self.change(self.explore)

    def combat_won(self, combat):
        run = self.run
        run.shield = 0.0
        unlocked = []
        if run.sanity < SANITY_MAD:
            unlocked += self.unlock(MADNESS_UNLOCK)
        run.change_sanity(4)   # a breath after the fight
        if run.has("heartwood"):
            run.heal(8)
        if combat.boss:
            for key in BOSS_UNLOCKS[run.act]:
                unlocked += self.unlock(key)
            self.change(PageScene(self, True, combat.enemies[0].name, unlocked))
        else:
            run.cleared.add(combat.encounter_index)
            self.explore.on_cleared(combat.encounter_index)
            self.change(PageScene(self, False, "", unlocked))

    def after_page(self, boss):
        run = self.run
        if not boss:
            self.change(self.explore)
            return
        if run.act >= FINAL_ACT:
            run.won = True
            self.save.wins += 1
            self.finish_run()
            self.change(EndScene(self, "victory"))
            return
        self.change(CampScene(self))

    def game_over(self, cause):
        self.finish_run()
        self.change(EndScene(self, cause))

    # --- effects -------------------------------------------------------------
    def add_shake(self, seconds, power):
        self.shake = max(self.shake, seconds)
        self.shake_power = max(self.shake_power if self.shake > 0 else 0, power)

    def float_text(self, text, pos, color):
        self.ui_floaters.append(FloatingText(text, pos, color, 32, 1.6, 30))

    # --- loop pieces ----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if self.paused:
            self.handle_pause_key(event)
            return
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                and self.scene.pausable):
            self.paused = True
            self.pause_selected = 0
            return
        self.scene.handle_event(event)

    def handle_pause_key(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.paused = False
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.pause_selected = (self.pause_selected - 1) % 3
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.pause_selected = (self.pause_selected + 1) % 3
        elif self.pause_selected == 1 and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            step = 1 if event.key == pygame.K_RIGHT else -1
            self.sound.set_volume(self.sound.volume + step)
            self.sound.play("select")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.pause_selected == 0:
                self.paused = False
            elif self.pause_selected == 2:
                self.game_over("abandon")

    def update(self, dt):
        self.time += dt
        self.shake = max(0.0, self.shake - dt)
        for f in self.ui_floaters:
            f.update(dt)
        self.ui_floaters = [f for f in self.ui_floaters if f.alive]
        if self.paused:
            return
        self.scene.update(dt)
        self.update_whispers(dt)

    def update_whispers(self, dt):
        """Below 40 sanity, words drift across the screen."""
        for w in self.whispers:
            w[3] -= dt
            w[1] += w[4] * dt
        self.whispers = [w for w in self.whispers if w[3] > 0]
        if not (self.run and self.scene.show_sanity_fx):
            return
        if self.run.sanity >= SANITY_FRAYING:
            return
        self.whisper_timer -= dt
        if self.whisper_timer <= 0:
            madness = 1 - self.run.sanity / SANITY_FRAYING
            self.whisper_timer = random.uniform(1.5, 4.0) * (1.2 - madness)
            # [text, x, y, life, speed]
            self.whispers.append([random.choice(WHISPERS),
                                  random.randint(0, WIDTH - 200), random.randint(60, 300),
                                  3.0, random.choice((-20, 20))])

    def draw(self):
        self.world.fill((0, 0, 0))
        self.scene.draw_world(self.world)
        offset = (0, 0)
        if self.shake > 0:
            p = self.shake_power * min(1.0, self.shake / 0.35)
            offset = (random.uniform(-p, p), random.uniform(-p, p))
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.world, offset)
        if self.run and self.scene.show_sanity_fx:
            self.draw_sanity_fx(self.screen)
        self.scene.draw_ui(self.screen)
        for f in self.ui_floaters:
            f.draw(self.screen)
        if self.paused:
            self.draw_pause(self.screen)
        pygame.display.flip()

    def draw_sanity_fx(self, surface):
        sanity = self.run.sanity
        if sanity < 85:
            surface.blit(art.vignette(1 - sanity / 85), (0, 0))
        if sanity < SANITY_MAD:
            pulse = (math.sin(self.time * 3) + 1) / 2
            self.red.fill((120, 0, 20, int(20 + 40 * pulse)))
            surface.blit(self.red, (0, 0))
        for text, x, y, life, _ in self.whispers:
            img = ui.font(26).render(text, True, (150, 120, 190))
            img.set_alpha(int(min(1.0, life, 3.0 - life) * 110))
            surface.blit(img, (x, y))

    def draw_hud(self, surface):
        run = self.run
        ui.panel(surface, (8, 8, 286, 66), 170)
        ui.draw_text(surface, ui.font(22), f"{run.name}  -  Act {run.act}", BONE, topleft=(16, 11))
        ui.draw_bar(surface, (16, 32, 160, 12), run.hp / run.max_hp, HP_COL)
        if run.shield > 0:
            ui.draw_bar(surface, (16, 32, 160, 4), run.shield / MAX_SHIELD, SHIELD_COL,
                        border=SHIELD_COL)
        ui.draw_text(surface, ui.font(20), f"HP {run.hp:.0f}", WHITE, topleft=(184, 29))
        ui.draw_bar(surface, (16, 52, 160, 12), run.sanity / MAX_SANITY, SANITY_COL)
        for mark in (SANITY_LUCID, SANITY_FRAYING, SANITY_MAD):
            x = 16 + int(160 * mark / MAX_SANITY)
            pygame.draw.line(surface, GRAY, (x, 50), (x, 66), 1)
        tier = TIER_NAMES[sanity_tier(run.sanity)]
        ui.draw_text(surface, ui.font(20), f"{tier} {run.sanity:.0f}", SANITY_COL, topleft=(184, 49))

    def draw_pause(self, surface):
        surface.blit(self.shade, (0, 0))
        ui.draw_text(surface, ui.font(64), "Paused", BONE, center=(WIDTH // 2, 130))
        labels = ["Resume", f"Volume: < {self.sound.volume * 10}% >", "Abandon run"]
        for i, label in enumerate(labels):
            col = GOLD if i == self.pause_selected else GRAY
            ui.draw_text(surface, ui.font(40), label, col, center=(WIDTH // 2, 230 + i * 50))
        if self.run:
            spells = ", ".join(f"{s.defn.name} Lv{s.level}" for s in self.run.grimoire)
            ui.draw_text(surface, ui.font(22), ui.fit("Grimoire: " + spells, ui.font(22), WIDTH - 60),
                         WHITE, center=(WIDTH // 2, 410))
            relics = ", ".join(RELICS[k][0] for k in self.run.relics) or "none"
            ui.draw_text(surface, ui.font(22), ui.fit("Relics: " + relics, ui.font(22), WIDTH - 60),
                         GOLD, center=(WIDTH // 2, 436))
            ui.draw_text(surface, ui.font(22), f"Seed: {self.run.seed}", GRAY,
                         center=(WIDTH // 2, 462))
        ui.draw_text(surface, ui.font(20), "Esc: resume   Enter: select", GRAY,
                     center=(WIDTH // 2, HEIGHT - 30))


def main():
    game = Game()
    while game.running:
        dt = min(clock.tick(FPS) / 1000, MAX_DT)
        for event in pygame.event.get():
            game.handle_event(event)
        game.update(dt)
        game.draw()
    pygame.quit()


if __name__ == "__main__":
    main()
