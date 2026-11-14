"""Title menu, how-to-play, naming the boy, and the end screens."""
import math
import random

import pygame

import art
import ui
from bestiary import ACTS, ENEMIES, TRAITS
from entities import Layer
from settings import WIDTH, HEIGHT, WHITE, GRAY, GOLD, BONE, SANITY_COL, BLOOD
from relics import RELICS
from settings import ELEMENT_COLORS, GREEN
from spells import SPELLS, SPELL_LIST, KIND_LABEL


class MenuBackdrop:
    """Slowly drifting woods behind every menu."""

    def __init__(self):
        self.scene = art.forest_scene()
        if self.scene is None:
            far, mid, trunks, near = art.parallax_layers(ACTS[1], "menu")
            self.layers = [Layer(far, 0.1), Layer(mid, 0.4), Layer(trunks, 0.8), Layer(near, 1.0)]
        self.x = 0.0
        self.time = 0.0

    def update(self, dt):
        self.x += 30 * dt
        self.time += dt

    def draw(self, surface):
        if self.scene:
            self.scene.draw(surface, 1, self.x, self.time)
        else:
            for layer in self.layers:
                layer.draw(surface, self.x)


class TitleScene:
    pausable = False
    show_sanity_fx = False

    def __init__(self, game):
        self.game = game
        self.backdrop = MenuBackdrop()
        self.selected = 0
        self.time = 0.0
        self.rng = random.Random()

    def options(self):
        return ["New Run", "Codex", "How to Play",
                f"Volume: < {self.game.sound.volume * 10}% >", "Quit"]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        n = len(self.options())
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % n
            self.game.sound.play("select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % n
            self.game.sound.play("select")
        elif self.selected == 3 and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            step = 1 if event.key == pygame.K_RIGHT else -1
            self.game.sound.set_volume(self.game.sound.volume + step)
            self.game.sound.play("select")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.selected == 0:
                self.game.change(NameScene(self.game))
            elif self.selected == 1:
                self.game.change(CodexScene(self.game))
            elif self.selected == 2:
                self.game.change(HowToScene(self.game))
            elif self.selected == 4:
                self.game.running = False
        elif event.key == pygame.K_ESCAPE:
            self.game.running = False

    def update(self, dt):
        self.time += dt
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)

    def draw_ui(self, surface):
        surface.blit(self.game.overlay, (0, 0))
        # the title trembles, one letter at a time
        title = "SPELL TYPER"
        big = ui.font(96)
        total = big.size(title)[0]
        x = WIDTH // 2 - total // 2
        for i, ch in enumerate(title):
            dy = math.sin(self.time * 2 + i * 0.6) * 4
            surface.blit(big.outlined(ch, BONE), (x - big.edge, 80 + dy - big.edge))
            x += big.size(ch)[0]
        ui.draw_text(surface, ui.font(28), "a lost boy, a dark wood, and a grimoire that lies",
                     GRAY, center=(WIDTH // 2, 175))
        ui.panel(surface, (WIDTH // 2 - 200, 206, 400, 246), 150)
        for i, label in enumerate(self.options()):
            col = GOLD if i == self.selected else (190, 186, 204)
            ui.draw_text(surface, ui.font(40), label, col, center=(WIDTH // 2, 236 + i * 46))
        save = self.game.save
        stats = (f"Runs: {save.runs}   Escapes: {save.wins}   Best score: {save.best_score}   "
                 f"Spells unlocked: {len(save.unlocked)}/{len(SPELL_LIST)}")
        ui.draw_text(surface, ui.font(22), stats, SANITY_COL, center=(WIDTH // 2, HEIGHT - 50))
        ui.draw_text(surface, ui.font(20), "Up/Down: choose   Left/Right: volume   Enter: select",
                     GRAY, center=(WIDTH // 2, HEIGHT - 22))


HOW_TO = [
    ("Goal", "Lead the lost boy through three cursed acts. Each ends at a gate; step "
             "through when you are ready for its boss. Jump the thorns, gather the lights."),
    ("Casting", "In battle, TYPE an incantation to cast it. The first letters choose the "
                "spell. Wrong keys do not advance; they lower accuracy. Damage x accuracy "
                "squared. Longer incantations hit harder."),
    ("Crits", "Crit chance rises the SLOWER you type (1 / letters-per-second), but the "
              "enemies' attack bars keep filling while you take your time."),
    ("Focus", "Each cast at 95%+ accuracy adds a point of Focus (+8% each, up to 5). "
              "A sloppy cast or a blow that lands breaks it."),
    ("Sanity", "Spells cost sanity and eldritch blows drain it. Below 70 some letters are "
               "replaced, below 40 many, below 15 the words are nonsense. Type what you "
               "SEE. At 0 your mind is lost."),
    ("Defense", "When an attack bar fills, type the DEFEND word in time to dodge; fast and "
                "clean deflects it back. The lower your health, the harder the words. "
                "A magenta bar means a HEAVY blow: a longer word, and it hits harder."),
    ("Pages", "Fights drop scraps, bosses drop pages. The LOWER your sanity when you read "
              "one, the stronger it is and the more choices you get. Or burn it for sanity."),
    ("Camps", "After a boss you rest at a fire: heal, study a spell, or take a relic."),
    ("Death", "Death is permanent and the grimoire is lost, but unlocked spells stay "
              "unlocked. See the Codex for how to unlock the rest."),
]


class HowToScene:
    pausable = False
    show_sanity_fx = False

    def __init__(self, game):
        self.game = game
        self.backdrop = MenuBackdrop()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                                          pygame.K_BACKSPACE):
            self.game.change(TitleScene(self.game))

    def update(self, dt):
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)

    def draw_ui(self, surface):
        ui.panel(surface, (40, 20, WIDTH - 80, HEIGHT - 40), 230)
        ui.draw_text(surface, ui.font(48), "How to Play", BONE, center=(WIDTH // 2, 50))
        y = 76
        body = ui.font(21)
        for head, text in HOW_TO:
            ui.draw_text(surface, ui.font(24), head, GOLD, topleft=(64, y))
            for line in ui.wrap(text, body, WIDTH - 230):
                ui.draw_text(surface, body, line, WHITE, topleft=(160, y))
                y += 19
            y += 6
        ui.draw_text(surface, ui.font(20), "Enter / Esc: back", GRAY, center=(WIDTH // 2, HEIGHT - 34))


class CodexScene:
    """Everything the player has learned: spells, relics, enemy traits."""
    pausable = False
    show_sanity_fx = False
    PAGES = ["Spells", "Relics & Foes"]

    def __init__(self, game):
        self.game = game
        self.backdrop = MenuBackdrop()
        self.page = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
            self.game.change(TitleScene(self.game))
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
            self.page = (self.page + 1) % len(self.PAGES)
            self.game.sound.play("select")

    def update(self, dt):
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)

    def draw_ui(self, surface):
        ui.panel(surface, (30, 16, WIDTH - 60, HEIGHT - 32), 235)
        ui.draw_text(surface, ui.font(42), f"Codex: {self.PAGES[self.page]}", BONE,
                     center=(WIDTH // 2, 42))
        if self.page == 0:
            self.draw_spells(surface)
        else:
            self.draw_lore(surface)
        ui.draw_text(surface, ui.font(20), "Left/Right: turn the page   Esc: back", GRAY,
                     center=(WIDTH // 2, HEIGHT - 30))

    def draw_spells(self, surface):
        unlocked = self.game.save.unlocked
        small = ui.font(20)
        y = 70
        for spell in SPELL_LIST:
            if spell.key in unlocked:
                ui.draw_text(surface, small, spell.name, ELEMENT_COLORS[spell.element],
                             topleft=(50, y))
                ui.draw_text(surface, small, f"{KIND_LABEL[spell.kind]} {spell.base_amount:.0f}",
                             WHITE, topleft=(200, y))
                ui.draw_text(surface, small, f"-{spell.sanity_cost} san", SANITY_COL,
                             topleft=(350, y))
                tag = "" if spell.tier != "forbidden" else "  (forbidden)"
                ui.draw_text(surface, small, ui.fit(f"\"{spell.incantation}\"{tag}", small, 480),
                             GRAY, topleft=(440, y))
            else:
                ui.draw_text(surface, small, "? ? ?", GRAY, topleft=(50, y))
                ui.draw_text(surface, small, ui.fit("Sealed: " + spell.unlock, small, 700),
                             GOLD, topleft=(200, y))
            y += 23

    def draw_lore(self, surface):
        small = ui.font(20)
        y = 70
        ui.draw_text(surface, ui.font(26), "Relics (found at campfires)", GOLD, topleft=(50, y))
        y += 26
        for name, desc in RELICS.values():
            ui.draw_text(surface, small, name, WHITE, topleft=(60, y))
            ui.draw_text(surface, small, desc, GRAY, topleft=(260, y))
            y += 21
        y += 12
        ui.draw_text(surface, ui.font(26), "Traits of the things in the woods", GOLD,
                     topleft=(50, y))
        y += 26
        for key, (label, desc) in TRAITS.items():
            who = [d["name"] for d in ENEMIES.values() if d.get("trait") == key]
            ui.draw_text(surface, small, label, (190, 150, 230), topleft=(60, y))
            ui.draw_text(surface, small, ui.fit(f"{desc}  ({', '.join(who)})", small, 780),
                         GRAY, topleft=(140, y))
            y += 21
        save = self.game.save
        ui.draw_text(surface, ui.font(24),
                     f"Runs {save.runs}    Escapes {save.wins}    Deepest act {save.best_act}"
                     f"    Best score {save.best_score}", GREEN, center=(WIDTH // 2, HEIGHT - 60))


class NameScene:
    """Name the boy and optionally type a seed for the woods."""
    pausable = False
    show_sanity_fx = False

    def __init__(self, game, name=""):
        self.game = game
        self.backdrop = MenuBackdrop()
        self.fields = {"name": name, "seed": ""}
        self.active = "name"
        self.time = 0.0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))
        elif event.key in (pygame.K_TAB, pygame.K_UP, pygame.K_DOWN):
            self.active = "seed" if self.active == "name" else "name"
        elif event.key == pygame.K_BACKSPACE:
            self.fields[self.active] = self.fields[self.active][:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.game.start_run(self.fields["name"].strip(), self.fields["seed"].strip())
        elif event.unicode and event.unicode.isprintable():
            limit = 14 if self.active == "name" else 12
            if len(self.fields[self.active]) < limit:
                ch = event.unicode
                if self.active == "seed" and not ch.isalnum():
                    return
                self.fields[self.active] += ch

    def update(self, dt):
        self.time += dt
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)

    def draw_ui(self, surface):
        surface.blit(self.game.overlay, (0, 0))
        ui.draw_text(surface, ui.font(44), "Who is lost in the woods?", BONE, center=(WIDTH // 2, 120))
        cursor = "_" if int(self.time * 2) % 2 == 0 else " "
        for i, (key, label) in enumerate((("name", "Name"), ("seed", "Seed (blank = random)"))):
            y = 200 + i * 90
            active = key == self.active
            ui.draw_text(surface, ui.font(26), label, GOLD if active else GRAY,
                         center=(WIDTH // 2, y))
            box = pygame.Rect(WIDTH // 2 - 200, y + 16, 400, 44)
            pygame.draw.rect(surface, (20, 18, 28), box)
            pygame.draw.rect(surface, GOLD if active else GRAY, box, 2)
            text = self.fields[key] + (cursor if active else "")
            ui.draw_text(surface, ui.font(36), text, WHITE, center=box.center)
        ui.draw_text(surface, ui.font(22), "Tab: switch field   Enter: begin   Esc: back",
                     GRAY, center=(WIDTH // 2, HEIGHT - 60))


class EndScene:
    """Game over or victory. Shows the run's stats."""
    pausable = False
    show_sanity_fx = False

    CAUSES = {
        "madness": ("Your mind unravels.", "The words were never words at all."),
        "wounds": ("The woods keep you.", "Your lantern gutters out."),
        "abandon": ("You stop walking.", "The trees close in."),
        "victory": ("Dawn breaks.", "The lost boy walks out of the woods."),
    }

    def __init__(self, game, cause):
        self.game = game
        self.cause = cause
        self.run = game.run
        self.time = 0.0
        self.backdrop = MenuBackdrop()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.time < 1.0:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.game.change(NameScene(self.game, self.run.name))
        elif event.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))

    def update(self, dt):
        self.time += dt
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)
        if self.cause != "victory":
            red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            red.fill((60, 0, 0, 120))
            surface.blit(red, (0, 0))
        else:
            dawn = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dawn.fill((255, 190, 120, int(min(90, self.time * 40))))
            surface.blit(dawn, (0, 0))

    def draw_ui(self, surface):
        surface.blit(self.game.overlay, (0, 0))
        title, sub = self.CAUSES[self.cause]
        ui.draw_text(surface, ui.font(72), title, GOLD if self.cause == "victory" else BLOOD,
                     center=(WIDTH // 2, 90))
        ui.draw_text(surface, ui.font(28), sub, GRAY, center=(WIDTH // 2, 140))
        run = self.run
        lines = [
            f"{run.name}   (seed {run.seed})",
            f"Reached act {run.act}: {ACTS[run.act]['name']}",
            f"Foes banished: {run.kills}    Spells cast: {run.casts}    Deflects: {run.deflects}",
            f"Typing accuracy: {run.accuracy * 100:.0f}%    Biggest hit: {run.best_hit}",
            "Grimoire: " + ", ".join(f"{s.defn.name} Lv{s.level}" for s in run.grimoire),
            "Relics: " + (", ".join(RELICS[k][0] for k in run.relics) or "none"),
        ]
        best = self.game.save.best_score
        score = run.score()
        record = "  -  a new record!" if score >= best and score > 0 else f"   (best {best})"
        ui.draw_text(surface, ui.font(36), f"Score {score}{record}", GOLD,
                     center=(WIDTH // 2, 186))
        for i, line in enumerate(lines):
            line = ui.fit(line, ui.font(24), WIDTH - 80)
            ui.draw_text(surface, ui.font(24), line, WHITE, center=(WIDTH // 2, 226 + i * 29))
        if run.new_unlocks:
            names = ", ".join(SPELLS[k].name for k in run.new_unlocks)
            ui.draw_text(surface, ui.font(26), ui.fit(f"Unlocked this run: {names}", ui.font(26),
                                                      WIDTH - 60), GOLD, center=(WIDTH // 2, 412))
        locked = [s for s in SPELL_LIST if s.key not in self.game.save.unlocked]
        if locked:
            hint = f"Still sealed: {locked[0].name} - {locked[0].unlock}"
            ui.draw_text(surface, ui.font(22), hint, SANITY_COL, center=(WIDTH // 2, 442))
        if self.time >= 1.0:
            ui.draw_text(surface, ui.font(24), "Enter: new run   Esc: title",
                         GRAY, center=(WIDTH // 2, HEIGHT - 40))
