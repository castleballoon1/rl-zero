"""Title menu, how-to-play, naming the boy, and the end screens."""
import math
import random

import pygame

import art
import ui
from bestiary import ACTS, ENEMIES, TRAITS, act_info, FINAL_ACT
from entities import Layer, Projectile, Ring, RuneCircle, burst
from settings import (WIDTH, HEIGHT, WHITE, GRAY, GOLD, BONE, SANITY_COL, BLOOD, GROUND_Y,
                      MISS_COL, DIFFICULTIES, DIFFICULTY)
from relics import RELICS
from settings import ELEMENT_COLORS, GREEN
from spells import SPELLS, SPELL_LIST, effect_text, cost_text


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
    """The title screen.

    It opens with a short animation: the letters of the name fall into place
    one by one while the boy walks in from the left with his grimoire. Then
    the menu fades in. Every choice is a word you TYPE (type 'start' to
    begin); Up/Down and Enter work too. When you start, he casts a spell
    at the title before the screen fades.
    """
    music = "woods"
    pausable = False
    show_sanity_fx = False
    WORDS = ["start", "codex", "guide", "quit"]
    HINTS = ["Begin a new run", "Spells, relics, creatures", "How to play", "Leave the woods"]
    HERO_X = 170                 # where he stops walking
    WALK = (0.6, 2.9)            # he walks in between these seconds ...
    MENU_AT = 2.7                # ... and the menu fades in from here
    CAST_TIME = 1.5              # seconds from casting to the next screen

    def __init__(self, game, intro=False):
        self.game = game
        self.backdrop = MenuBackdrop()
        self.selected = 0
        self.time = 0.0 if intro else 10.0      # 10 s = the opening is already over
        self.rng = random.Random()
        self.hero = art.hero_frames(120)
        self.walk_anim = 0.0
        self.buffer = ""                         # letters typed towards a word
        self.miss = 0.0                          # red flash after a wrong letter
        self.casting = None                      # seconds since he began to cast
        self.chosen = None
        self.effects = []
        self.particles = pygame.sprite.Group()
        self.bolt = None
        self.flash = 0.0                         # the title lights up when the bolt lands
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((0, 0, 0, 110))

    # --- the animation clock -----------------------------------------------------
    def intro_done(self):
        return self.time >= self.WALK[1]

    def hero_x(self):
        a, b = self.WALK
        t = max(0.0, min(1.0, (self.time - a) / (b - a)))
        t = 1 - (1 - t) ** 2                     # eases to a stop
        return -60 + (self.HERO_X + 60) * t

    def menu_alpha(self):
        return max(0.0, min(1.0, (self.time - self.MENU_AT) / 0.6))

    # --- input ----------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.casting is not None:
            return
        if not self.intro_done():
            self.time = 10.0                     # any key skips the opening
            return
        n = len(self.WORDS)
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            step = -1 if event.key == pygame.K_UP else 1
            self.selected = (self.selected + step) % n
            self.buffer = ""
            self.game.sound.play("select")
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            step = 1 if event.key == pygame.K_RIGHT else -1
            self.game.sound.set_volume(self.game.sound.volume + step)
            self.game.sound.play("select")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.choose(self.WORDS[self.selected])
        elif event.key == pygame.K_BACKSPACE:
            self.buffer = ""
        elif event.key == pygame.K_ESCAPE:
            self.game.running = False
        else:
            ch = event.unicode.lower() if event.unicode else ""
            if len(ch) == 1 and ch.isalpha():
                self.type_letter(ch)

    def type_letter(self, ch):
        new = self.buffer + ch
        matching = [w for w in self.WORDS if w.startswith(new)]
        if not matching:
            self.buffer = ""
            self.miss = 0.25
            self.game.sound.play("miss")
            return
        self.buffer = new
        self.selected = self.WORDS.index(matching[0])
        self.game.sound.play_key(len(new) / len(matching[0]))
        if new in self.WORDS:
            self.choose(new)

    def choose(self, word):
        self.game.sound.play("confirm")
        self.buffer = word
        if word == "start":
            self.cast()
        elif word == "codex":
            self.game.change(CodexScene(self.game))
        elif word == "guide":
            self.game.change(HowToScene(self.game))
        else:
            self.game.running = False

    def cast(self):
        """He raises the grimoire and throws a spell at the title."""
        self.casting = 0.0
        feet = (round(self.hero_x()), GROUND_Y)
        self.effects.append(RuneCircle(feet, ELEMENT_COLORS["fire"]))
        self.game.sound.play_cast("fire")
        hand = (feet[0] + 22, feet[1] - 82)
        burst(self.particles, hand, ELEMENT_COLORS["fire"], 20, speed=(40, 180))
        self.bolt = Projectile(hand, _Spot((WIDTH // 2, 95)), ELEMENT_COLORS["fire"],
                               self.bolt_lands, speed=780, size=12, delay=0.18)

    def bolt_lands(self, spot):
        self.flash = 0.6
        self.effects.append(Ring(spot.center, (255, 200, 120), radius=170, life=0.6, width=6))
        burst(self.particles, spot.center, (255, 170, 80), 50, speed=(80, 360), life=(0.4, 1.1))
        self.game.sound.play("crit")
        self.game.add_shake(0.35, 7)

    # --- update ---------------------------------------------------------------------
    def update(self, dt):
        self.time += dt
        walking = self.WALK[0] <= self.time < self.WALK[1]
        # the woods slide by while he walks in, then hold still (only the mist drifts)
        self.backdrop.update(dt * (1.4 if walking else 0.0))
        self.backdrop.time += 0 if walking else dt
        if walking:
            self.walk_anim += dt
        self.miss = max(0.0, self.miss - dt)
        self.flash = max(0.0, self.flash - dt)
        self.particles.update(dt)
        for effect in self.effects:
            effect.update(dt)
        self.effects = [e for e in self.effects if e.alive]
        if self.bolt:
            self.bolt.update(dt)
            if self.bolt.done:
                self.bolt = None
        if self.casting is not None:
            self.casting += dt
            if self.casting >= self.CAST_TIME and self.chosen is None:
                self.chosen = "start"
                self.game.change(NameScene(self.game))

    # --- drawing --------------------------------------------------------------------
    def draw_world(self, surface):
        self.backdrop.draw(surface)
        surface.blit(self.shade, (0, 0))
        x = round(self.hero_x())
        poses = art.hero_poses(self.hero, 100)
        walking = self.WALK[0] <= self.time < self.WALK[1]
        if self.casting is not None and self.casting < 0.9:
            img = poses["cast"]
        elif walking:
            img = poses["walk"][int(self.walk_anim / 0.14) % len(poses["walk"])]
        else:
            img = poses["idle"]
        if x > -50:
            shade = art.shadow(70)
            surface.blit(shade, shade.get_rect(center=(x, GROUND_Y - 2)))
            flicker = 4 * math.sin(self.time * 9) + 2 * math.sin(self.time * 23)
            charge = 0.0 if self.casting is None else max(0.0, 1 - self.casting / 0.6)
            light = art.glow(int(90 + flicker + 60 * charge), (150, 220, 255), 90)
            surface.blit(light, light.get_rect(center=(x + 10, GROUND_Y - 60)))
            for effect in self.effects:
                if isinstance(effect, RuneCircle):
                    effect.draw(surface)
            lift = 0
            if self.casting is not None and self.casting < 0.55:
                lift = int(math.sin(self.casting / 0.55 * math.pi) * 10)
            surface.blit(img, img.get_rect(midbottom=(x, GROUND_Y - lift)))

    def draw_ui(self, surface):
        self.draw_title(surface)
        for effect in self.effects:
            if not isinstance(effect, RuneCircle):
                effect.draw(surface)
        if self.bolt:
            self.bolt.draw(surface)
        self.particles.draw(surface)
        alpha = self.menu_alpha()
        if alpha <= 0:
            if self.time > 0.3:
                ui.draw_text(surface, ui.font(18), "any key to skip", GRAY,
                             center=(WIDTH // 2, HEIGHT - 16))
            return
        menu = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.draw_menu(menu)
        menu.set_alpha(int(255 * alpha))
        surface.blit(menu, (0, 0))

    def draw_title(self, surface):
        """The name falls into place, letter by letter, then trembles."""
        title = "Spell Typer"
        big = ui.font(96)
        total = big.size(title)[0]
        x = WIDTH // 2 - total // 2
        color = BONE
        if self.flash > 0:
            k = self.flash / 0.6
            color = tuple(int(c + (255 - c) * k) for c in BONE)
        for i, ch in enumerate(title):
            appear = 0.2 + i * 0.09
            t = max(0.0, min(1.0, (self.time - appear) / 0.45))
            if t <= 0:
                x += big.size(ch)[0]
                continue
            fall = (1 - t) ** 3 * -90                       # drops in and settles
            dy = math.sin(self.time * 2 + i * 0.6) * 4 + fall
            img = big.outlined(ch, color)
            img.set_alpha(int(255 * t))
            surface.blit(img, (x - big.edge, 60 + dy - big.edge))
            x += big.size(ch)[0]
        sub_alpha = max(0.0, min(1.0, (self.time - 1.4) / 0.8))
        if sub_alpha > 0:
            line = ui.font(28).outlined("a lost boy, a dark wood, and a grimoire that lies", GRAY)
            line.set_alpha(int(255 * sub_alpha))
            surface.blit(line, line.get_rect(center=(WIDTH // 2, 158)))

    def draw_menu(self, surface):
        box = pygame.Rect(WIDTH // 2 - 150, 196, 420, 236)
        ui.panel(surface, box, 160)
        ui.draw_text(surface, ui.font(22), "Type a word to choose", GOLD,
                     center=(box.centerx, box.y + 18))
        for i, word in enumerate(self.WORDS):
            y = box.y + 42 + i * 44
            sel = i == self.selected
            typed = -1                       # -1: no cursor under an unchosen word
            if sel:
                typed = len(self.buffer) if word.startswith(self.buffer) else 0
            color = WHITE if sel else (150, 146, 164)
            ui.draw_incantation(surface, word, typed, (box.x + 30, y), 40, color=color)
            ui.draw_text(surface, ui.font(18), self.HINTS[i], GOLD if sel else GRAY,
                         midleft=(box.x + 160, y + 13))
            if sel:
                pygame.draw.polygon(surface, GOLD, [(box.x + 10, y + 6), (box.x + 10, y + 20),
                                                    (box.x + 19, y + 13)])
        if self.miss > 0:
            pygame.draw.rect(surface, MISS_COL, box, 3)
        ui.draw_text(surface, ui.font(20), f"Volume {self.game.sound.volume * 10}%  (Left/Right)",
                     GRAY, center=(box.centerx, box.bottom - 14))
        save = self.game.save
        stats = (f"Runs: {save.runs}   Escapes: {save.wins}   Best score: {save.best_score}   "
                 f"Spells unlocked: {len(save.unlocked)}/{len(SPELL_LIST)}")
        ui.draw_text(surface, ui.font(22), stats, SANITY_COL, center=(WIDTH // 2, HEIGHT - 50))
        ui.draw_text(surface, ui.font(20), "Type START to begin    Up/Down + Enter also work",
                     GRAY, center=(WIDTH // 2, HEIGHT - 22))


class _Spot:
    """A fixed point a bolt can fly to (Projectile wants something with .center)."""

    def __init__(self, center):
        self.center = center


HOW_TO = [
    ("Goal", "Lead the lost boy through three cursed acts, each harder than the last. "
             "Each ends at a gate and its boss. After the third you may walk on, deeper."),
    ("Sanity", "Sanity is your only health: spells cost it, blows take it, at 0 your mind "
               "is lost. 71-100 Lucid: words are true. 31-70 Uneasy: some letters are "
               "replaced and the edges darken. 0-30 Fraying: the words are nonsense and "
               "the edges bleed. Type what you see."),
    ("Casting", "In battle, type an incantation to cast it. The first letters choose the "
                "spell. Wrong keys do not advance; they lower accuracy. Damage x accuracy "
                "squared. Longer incantations hit harder."),
    ("Burnout", "Cast the same spell 3 times in quick succession and it burns out for 8 "
                "seconds. The orange pips by its name show the heat. Vary your spells."),
    ("Crits", "Crit chance rises the slower you type (1 / letters-per-second), but the "
              "enemies' attack bars keep filling while you take your time."),
    ("Focus", "Each cast at 95%+ accuracy adds a point of Focus (+8% each, up to 5). "
              "A sloppy cast or a blow that lands breaks it."),
    ("Defense", "When an attack bar fills, type the Defend word in time to dodge; fast and "
                "clean deflects it. Foes keep no beat: some strike early, feint, or come "
                "twice. A bar turning magenta warns of a heavy blow."),
    ("Pages", "Fights drop scraps, bosses drop pages. The lower your sanity when you read "
              "one, the stronger it is and the more choices you get. Or burn it for sanity."),
    ("Camps", "After a boss you rest at a fire: regain sanity, study a spell, or take a relic."),
    ("Death", "Death is permanent and the grimoire is lost, but unlocked spells stay "
              "unlocked. See the Codex for how to unlock the rest."),
]


class HowToScene:
    music = "woods"
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
    music = "woods"
    pausable = False
    show_sanity_fx = False
    PAGES = ["Spells", "More spells", "Relics & Foes"]
    PER_PAGE = 13

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
            step = -1 if event.key == pygame.K_LEFT else 1
            self.page = (self.page + step) % len(self.PAGES)
            self.game.sound.play("select")

    def update(self, dt):
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)

    def draw_ui(self, surface):
        ui.panel(surface, (30, 16, WIDTH - 60, HEIGHT - 32), 235)
        ui.draw_text(surface, ui.font(42), f"Codex: {self.PAGES[self.page]}", BONE,
                     center=(WIDTH // 2, 42))
        if self.page < 2:
            self.draw_spells(surface, self.page)
        else:
            self.draw_lore(surface)
        ui.draw_text(surface, ui.font(20), "Left/Right: turn the page   Esc: back", GRAY,
                     center=(WIDTH // 2, HEIGHT - 30))

    def draw_spells(self, surface, page):
        unlocked = self.game.save.unlocked
        small = ui.font(20)
        y = 70
        first = page * self.PER_PAGE
        for spell in SPELL_LIST[first:first + self.PER_PAGE]:
            if spell.key in unlocked:
                ui.draw_text(surface, small, spell.name, ELEMENT_COLORS[spell.element],
                             topleft=(50, y))
                ui.draw_text(surface, small, effect_text(spell.kind, spell.base_amount),
                             WHITE, topleft=(200, y))
                ui.draw_text(surface, small, cost_text(spell.sanity_cost), SANITY_COL,
                             topleft=(350, y))
                tag = "" if spell.tier != "forbidden" else "  (forbidden)"
                ui.draw_text(surface, small, ui.fit(f"\"{spell.incantation}\"{tag}", small, 480),
                             GRAY, topleft=(440, y))
                ui.draw_text(surface, ui.font(18), ui.fit(spell.desc, ui.font(18), 700),
                             (150, 146, 164), topleft=(200, y + 18))
            else:
                ui.draw_text(surface, small, "? ? ?", GRAY, topleft=(50, y))
                ui.draw_text(surface, small, ui.fit("Sealed: " + spell.unlock, small, 700),
                             GOLD, topleft=(200, y))
            y += 38

    def draw_lore(self, surface):
        small = ui.font(20)
        y = 70
        ui.draw_text(surface, ui.font(26), "Relics (found at campfires)", GOLD, topleft=(50, y))
        y += 36
        for name, desc in RELICS.values():
            ui.draw_text(surface, small, name, WHITE, topleft=(60, y))
            ui.draw_text(surface, small, desc, GRAY, topleft=(260, y))
            y += 21
        y += 12
        ui.draw_text(surface, ui.font(26), "Traits of the things in the woods", GOLD,
                     topleft=(50, y))
        y += 36
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
    """Name the boy, optionally type a seed for the woods, and pick a difficulty."""
    music = "woods"
    pausable = False
    show_sanity_fx = False
    FIELDS = ["name", "seed", "difficulty"]

    def __init__(self, game, name=""):
        self.game = game
        self.backdrop = MenuBackdrop()
        self.fields = {"name": name, "seed": ""}
        keys = [d["key"] for d in DIFFICULTIES]
        self.level = keys.index(game.save.difficulty) if game.save.difficulty in keys else 1
        self.active = "name"
        self.time = 0.0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.change(TitleScene(self.game))
        elif event.key in (pygame.K_TAB, pygame.K_UP, pygame.K_DOWN):
            step = -1 if event.key == pygame.K_UP else 1
            i = self.FIELDS.index(self.active)
            self.active = self.FIELDS[(i + step) % len(self.FIELDS)]
            self.game.sound.play("select")
        elif self.active == "difficulty" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            step = 1 if event.key == pygame.K_RIGHT else -1
            self.level = (self.level + step) % len(DIFFICULTIES)
            self.game.sound.play("select")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.game.sound.play("confirm")
            self.game.start_run(self.fields["name"].strip(), self.fields["seed"].strip(),
                                DIFFICULTIES[self.level]["key"])
        elif self.active == "difficulty":
            return
        elif event.key == pygame.K_BACKSPACE:
            self.fields[self.active] = self.fields[self.active][:-1]
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
        ui.draw_text(surface, ui.font(44), "Who is lost in the woods?", BONE, center=(WIDTH // 2, 90))
        cursor = "_" if int(self.time * 2) % 2 == 0 else " "
        labels = (("name", "Name"), ("seed", "Seed (blank = random)"),
                  ("difficulty", "Difficulty"))
        for i, (key, label) in enumerate(labels):
            y = 160 + i * 90
            active = key == self.active
            ui.draw_text(surface, ui.font(26), label, GOLD if active else GRAY,
                         center=(WIDTH // 2, y))
            box = pygame.Rect(WIDTH // 2 - 200, y + 16, 400, 44)
            pygame.draw.rect(surface, (20, 18, 28), box)
            pygame.draw.rect(surface, GOLD if active else GRAY, box, 2)
            if key == "difficulty":
                level = DIFFICULTIES[self.level]
                text = f"<  {level['name']}  >" if active else level["name"]
                ui.draw_text(surface, ui.font(36), text, WHITE, center=box.center)
                ui.draw_text(surface, ui.font(20), level["desc"], (180, 170, 200),
                             center=(WIDTH // 2, box.bottom + 16))
            else:
                text = self.fields[key] + (cursor if active else "")
                ui.draw_text(surface, ui.font(36), text, WHITE, center=box.center)
        ui.draw_text(surface, ui.font(22),
                     "Tab / Up / Down: switch field   Left/Right: difficulty   Enter: begin   Esc: back",
                     GRAY, center=(WIDTH // 2, HEIGHT - 60))


class DawnScene:
    """After the third boss: the woods thin and dawn shows through.

    Walk out and the run ends in victory, or turn back into the endless woods,
    where every act is a little crueler than the last.
    """
    music = "victory"
    pausable = False
    show_sanity_fx = False

    def __init__(self, game):
        self.game = game
        self.time = 0.0
        self.backdrop = MenuBackdrop()
        self.selected = 0
        self.hero = art.hero_frames(120)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.time < 1.0:
            return
        if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            self.selected = 1 - self.selected
            self.game.sound.play("select")
        elif event.key in (pygame.K_1, pygame.K_2):
            self.selected = event.key - pygame.K_1
            self.choose()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.choose()

    def choose(self):
        self.game.sound.play("confirm")
        if self.selected == 0:
            self.game.leave_woods()
        else:
            self.game.go_deeper()

    def update(self, dt):
        self.time += dt
        self.backdrop.update(dt)

    def draw_world(self, surface):
        self.backdrop.draw(surface)
        dawn = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dawn.fill((255, 190, 120, int(min(80, self.time * 40))))
        surface.blit(dawn, (0, 0))
        boy = art.hero_poses(self.hero, self.game.run.sanity, self.game.run.max_sanity)["idle"]
        surface.blit(boy, boy.get_rect(midbottom=(220, GROUND_Y)))

    def draw_ui(self, surface):
        surface.blit(self.game.overlay, (0, 0))
        ui.draw_text(surface, ui.font(72), "Dawn breaks.", GOLD, center=(WIDTH // 2, 100))
        ui.draw_text(surface, ui.font(26), "The trees thin. Beyond them, a road and the morning.",
                     GRAY, center=(WIDTH // 2, 155))
        ui.draw_text(surface, ui.font(26), "Behind you, the woods go on. Something there still calls.",
                     GRAY, center=(WIDTH // 2, 182))
        rows = [("Walk out of the woods", "The run ends. You escaped."),
                ("Turn back into the dark", "Endless woods: every act deeper and crueler. "
                                            "Your grimoire and sanity carry on.")]
        for i, (title, detail) in enumerate(rows):
            box = pygame.Rect(WIDTH // 2 - 260, 240 + i * 90, 520, 76)
            sel = i == self.selected
            ui.panel(surface, box, 230 if sel else 150, border=GOLD if sel else (70, 64, 80))
            ui.draw_text(surface, ui.font(32), f"[{i + 1}] {title}", GOLD if sel else WHITE,
                         topleft=(box.x + 14, box.y + 8))
            for k, line in enumerate(ui.wrap(detail, ui.font(19), box.width - 28)):
                ui.draw_text(surface, ui.font(19), line, GRAY, topleft=(box.x + 14, box.y + 42 + k * 16))
        if self.time >= 1.0:
            ui.draw_text(surface, ui.font(20), "Up/Down + Enter, or press a number", GRAY,
                         center=(WIDTH // 2, HEIGHT - 30))


class DeathScene:
    """His mind is gone.

    On a black screen, alone in the middle, the boy's eye burns to full red
    and then drains to black. Then the end screen follows.
    """
    music = "defeat"         # the sombre stinger; it plays on into the end screen
    pausable = False
    show_sanity_fx = False
    REDDEN = (0.5, 1.8)      # between these seconds the eye climbs to full red
    BLACKEN = (2.3, 3.4)     # ... and between these it goes black
    LENGTH = 5.6

    def __init__(self, game):
        self.game = game
        self.time = 0.0
        self.leaving = False
        self.gone_black = False
        # the mad look, in every eye colour from brown to red to black
        self.frames = art.hero_frames(art.DEATH_TALL)["looks"][2]
        game.sound.play("death")

    def eye(self):
        """Which eye colour to show now."""
        def along(span):
            return max(0.0, min(1.0, (self.time - span[0]) / (span[1] - span[0])))
        if self.time < self.BLACKEN[0]:
            return 2 + round(along(self.REDDEN) * (art.EYE_RED - 2))
        if not self.gone_black:
            self.gone_black = True
            self.game.sound.play("black")      # a low boom as the light goes out
        return art.EYE_RED + round(along(self.BLACKEN) * (art.EYE_BLACK - art.EYE_RED))

    def leave(self):
        if not self.leaving:
            self.leaving = True
            self.game.change(EndScene(self.game, "madness"))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.time > 1.0:
            self.leave()             # any key skips ahead

    def update(self, dt):
        self.time += dt
        if self.time >= self.LENGTH:
            self.leave()

    def draw_world(self, surface):
        surface.fill((0, 0, 0))
        boy = self.frames[self.eye()]["right"]["idle"]
        shake = 0
        if self.REDDEN[0] < self.time < self.BLACKEN[0]:
            shake = round(math.sin(self.time * 70) * 2)     # he trembles as it takes him
        surface.blit(boy, boy.get_rect(center=(WIDTH // 2 + shake, HEIGHT // 2 - 10)))

    def draw_ui(self, surface):
        after = self.time - self.BLACKEN[1] - 0.3
        if after > 0:
            line = ui.font(40).outlined("Your mind unravels.", BLOOD)
            line.set_alpha(int(255 * min(1.0, after / 0.8)))
            surface.blit(line, line.get_rect(center=(WIDTH // 2, HEIGHT - 60)))


class EndScene:
    """Game over or victory. Shows the run's stats."""
    pausable = False
    show_sanity_fx = False

    CAUSES = {
        "madness": ("Your mind unravels.", "The words were never words at all."),
        "abandon": ("You stop walking.", "The trees close in."),
        "victory": ("Dawn breaks.", "The lost boy walks out of the woods."),
    }

    def __init__(self, game, cause):
        self.game = game
        self.cause = cause
        self.run = game.run
        self.time = 0.0
        self.backdrop = MenuBackdrop()
        # death keeps its stinger, an escape gets its fanfare, giving up is quiet woods
        self.music = {"madness": "defeat", "victory": "victory"}.get(cause, "woods")

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
            f"{run.name}   (seed {run.seed}, {DIFFICULTY[run.difficulty]['name']})",
            (f"Escaped the woods, then went {run.act - FINAL_ACT} "
             f"act{'s' if run.act - FINAL_ACT != 1 else ''} deeper: "
             f"{act_info(run.act)['name']}" if run.endless
             else f"Reached act {run.act}: {act_info(run.act)['name']}"),
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
