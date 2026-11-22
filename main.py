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
                      BONE, SANITY_COL, SHIELD_COL, SANITY_LUCID, BREATH_SANITY, FADE_TIME,
                      SANITY_FRAYING, GAZE_UNLOCK_BELOW, MAX_SHIELD, DIFFICULTY)

pygame.mixer.pre_init(44100, -16, 2, 512)    # CD quality stereo, for the recorded music
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
    ui.draw_text(screen, ui.font(96), TITLE, BONE, center=(WIDTH // 2, HEIGHT // 2 - 50))
    ui.draw_text(screen, ui.font(30), text, GRAY, center=(WIDTH // 2, HEIGHT // 2 + 30))
    pygame.display.flip()
    pygame.event.pump()      # keeps the window responsive while loading


art.preload(show_loading)

from bestiary import FINAL_ACT, act_info  # noqa: E402
from entities import FloatingText  # noqa: E402
from relics import RELICS  # noqa: E402
from run_state import RunState, SaveData  # noqa: E402
from scene_camp import CampScene  # noqa: E402
from scene_combat import CombatScene  # noqa: E402
from scene_explore import ExploreScene  # noqa: E402
from scene_menus import TitleScene, EndScene, DeathScene, DawnScene  # noqa: E402
from scene_intro import IntroScene  # noqa: E402
from scene_page import PageScene  # noqa: E402
from sound import Sound  # noqa: E402
from spells import SPELLS  # noqa: E402
from words import sanity_tier, TIER_NAMES, UNEASY, FRAYING  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

BOSS_UNLOCKS = {1: ["drain", "echo"], 2: ["chain", "hourglass", "plague"], 3: ["hymn"]}
MADNESS_UNLOCK = "gaze"          # win a fight below GAZE_UNLOCK_BELOW sanity
FRAYING_UNLOCK = "bloodprice"    # win a fight while Fraying

# Hallucinated words. A few drift past while Uneasy; while Fraying they
# crowd the screen.
WHISPERS = ["turn back", "it sees you", "the words are wrong", "you were never here",
            "read it again", "who wrote this", "they are under the page",
            "do you remember your name", "keep typing", "it is behind you",
            "ignis ignis ignis", "your hands are not yours", "the trees are counting",
            "wake up", "it was always dark", "spell it wrong", "they want the book",
            "nobody is coming", "listen", "the page is lying"]


class Game:
    def __init__(self):
        self.screen = screen
        self.world = pygame.Surface((WIDTH, HEIGHT))
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))
        self.sound = Sound()
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
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((0, 0, 0, 225))
        # Scene changes fade through black: `fade` is how dark the screen is
        # (0 clear, 1 black) and `next_scene` is the scene waiting behind it.
        self.black = pygame.Surface((WIDTH, HEIGHT))
        self.fade = 1.0               # the game opens by fading in
        self.next_scene = None
        self.transitions = True       # set False to switch scenes at once
        self.heartbeat = 0.0          # seconds until the next heartbeat at low sanity
        self.scene = TitleScene(self, intro=True)   # opens with its animation
        self.sound.play_music(self.scene.music)

    # --- state changes ----------------------------------------------------------
    def change(self, scene):
        """Go to another scene: fade to black, swap, fade back in."""
        self.paused = False
        if self.transitions:
            self.next_scene = scene       # update() swaps it in once the screen is black
            self.sound.play("fade")
        else:
            self.scene = scene
        # the music changes over while the picture fades
        self.sound.play_music(scene.music)

    def start_run(self, name, seed, difficulty="normal"):
        self.run = RunState(name, seed, difficulty)
        self.save.runs += 1
        self.save.best_act = max(self.save.best_act, 1)
        self.save.difficulty = difficulty
        self.save.save()
        # the boy wakes in the woods and finds the grimoire (skippable)
        self.change(IntroScene(self))

    def enter_woods(self):
        """After the opening: the first act begins."""
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
            self.sound.play("unlock")
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
        if run.sanity < GAZE_UNLOCK_BELOW:
            unlocked += self.unlock(MADNESS_UNLOCK)
        if sanity_tier(run.sanity) == FRAYING:
            unlocked += self.unlock(FRAYING_UNLOCK)
        run.change_sanity(BREATH_SANITY)   # a breath after the fight
        if run.has("heartwood"):
            run.change_sanity(8)
        if combat.boss:
            for key in BOSS_UNLOCKS.get(act_info(run.act)["look"], []):
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
        if run.act == FINAL_ACT and not run.endless:
            # the story is over: walk out into the dawn, or go deeper
            run.won = True
            self.save.wins += 1
            self.finish_run()
            self.change(DawnScene(self))
            return
        self.change(CampScene(self))

    def leave_woods(self):
        """At dawn after act 3: he walks out. The run ends in victory."""
        self.finish_run()
        self.change(EndScene(self, "victory"))

    def go_deeper(self):
        """At dawn after act 3: he turns back into the endless woods."""
        self.run.endless = True
        self.change(CampScene(self))

    def game_over(self, cause):
        self.finish_run()
        if cause == "madness":
            self.change(DeathScene(self))      # his eyes go black, then the end screen
        else:
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
        if self.next_scene:
            return                    # no input while the screen fades out
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
            self.sound.play("confirm")
            if self.pause_selected == 0:
                self.paused = False
            elif self.pause_selected == 2:
                self.game_over("abandon")

    def update(self, dt):
        self.time += dt
        self.sound.update(dt)         # music fades
        self.shake = max(0.0, self.shake - dt)
        for f in self.ui_floaters:
            f.update(dt)
        self.ui_floaters = [f for f in self.ui_floaters if f.alive]
        if self.next_scene:
            # fading out: the old scene is frozen until the screen is black
            self.fade = min(1.0, self.fade + dt / FADE_TIME)
            if self.fade >= 1.0:
                self.scene = self.next_scene
                self.next_scene = None
            return
        self.fade = max(0.0, self.fade - dt / FADE_TIME)     # fading in
        if self.paused:
            return
        self.scene.update(dt)
        self.update_whispers(dt)
        self.update_heartbeat(dt)

    def update_heartbeat(self, dt):
        """While Fraying his heart is heard, faster the lower sanity falls."""
        if (not (self.run and self.scene.show_sanity_fx)
                or sanity_tier(self.run.sanity) != FRAYING):
            self.heartbeat = 0.0
            return
        self.heartbeat -= dt
        if self.heartbeat <= 0:
            self.sound.play("heartbeat")
            self.heartbeat = 0.45 + 0.8 * self.run.sanity / SANITY_FRAYING

    def update_whispers(self, dt):
        """Hallucinated words: a few while Uneasy, a crowd while Fraying."""
        for w in self.whispers:
            w[3] -= dt
            w[1] += w[4] * dt
        self.whispers = [w for w in self.whispers if w[3] > 0]
        if not (self.run and self.scene.show_sanity_fx):
            return
        tier = sanity_tier(self.run.sanity)
        if tier < UNEASY:
            self.whisper_timer = min(self.whisper_timer, 3.0)
            return
        self.whisper_timer -= dt
        if self.whisper_timer > 0:
            return
        if tier == UNEASY:
            self.whisper_timer = random.uniform(5.0, 9.0)
            size, alpha, color = 26, 80, (150, 120, 190)
        else:
            madness = 1 - self.run.sanity / SANITY_FRAYING        # 0 at 30, 1 at 0
            self.whisper_timer = random.uniform(0.5, 1.8) * (1.1 - 0.6 * madness)
            size = random.choice((26, 30, 36, 44))
            alpha = 150
            color = random.choice([(150, 120, 190), (200, 60, 70), (230, 200, 210)])
        # [text, x, y, life, speed, size, alpha, colour]
        text = random.choice(WHISPERS)
        width = ui.font(size).size(text)[0]
        self.whispers.append([text, random.randint(0, max(1, WIDTH - width)),
                              random.randint(60, 330), 3.0, random.choice((-24, -12, 12, 24)),
                              size, alpha, color])

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
        if self.fade > 0:
            self.black.set_alpha(int(255 * self.fade))
            self.screen.blit(self.black, (0, 0))
        pygame.display.flip()

    def draw_sanity_fx(self, surface):
        """Lucid: nothing. Uneasy: a slight black vignette. Fraying: a red,
        pulsing vignette that beats faster as sanity falls."""
        sanity = self.run.sanity
        tier = sanity_tier(sanity)
        if tier == UNEASY:
            # 0.2 at 70 sanity, up to 0.5 at 31
            t = (SANITY_LUCID - sanity) / (SANITY_LUCID - SANITY_FRAYING)
            surface.blit(art.vignette(0.2 + 0.3 * t), (0, 0))
        elif tier == FRAYING:
            madness = 1 - max(0.0, sanity) / SANITY_FRAYING      # 0 at 30, 1 at 0
            surface.blit(art.vignette(0.6 + 0.2 * madness), (0, 0))
            beat = 2.5 + 4.0 * madness
            pulse = (math.sin(self.time * beat) + 1) / 2
            red = art.vignette(0.7 + 0.3 * madness, (170, 0, 24))
            red.set_alpha(int(110 + 145 * pulse))
            surface.blit(red, (0, 0))
            red.set_alpha(255)
        for text, x, y, life, _, size, alpha, color in self.whispers:
            img = ui.font(size).render(text, True, color)
            img.set_alpha(int(min(1.0, life, 3.0 - life) * alpha))
            surface.blit(img, (x, y))

    def draw_hud(self, surface):
        """Name, act and the one bar that matters: sanity, which is also his health."""
        run = self.run
        tier = sanity_tier(run.sanity)
        panel = art.status_panel_surface(tier)
        panel_y = -38
        surface.blit(panel, (0, panel_y))

        head = f"{run.name} - Act {run.act}"
        if run.difficulty != "normal":
            head += f" ({DIFFICULTY[run.difficulty]['name']})"
        ui.draw_text(surface, ui.font(22),
                     ui.fit(head, ui.font(22), 280), BONE,
                     topleft=(16, 16))

        bar = pygame.Rect(16, 38, 220, 18)
        colours = [(55, 190, 205), (200, 160, 230), (235, 70, 80)]
        ui.draw_bar(surface, bar, run.sanity / run.max_sanity, colours[tier])
        if run.shield > 0:
            ui.draw_bar(surface, (bar.left, bar.top, bar.width, 5),
                        run.shield / MAX_SHIELD, SHIELD_COL,
                        border=SHIELD_COL)
        ui.draw_text(surface, ui.font(20), f"Sanity {run.sanity:.0f}",
                     WHITE, midleft=(22, 47))
        ui.draw_text(surface, ui.font(20), TIER_NAMES[tier],
                     colours[tier], midleft=(246, 47))

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
