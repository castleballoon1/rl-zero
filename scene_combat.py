"""Stationary typing combat.

* Type an incantation from your grimoire to cast it. The first letters pick
  the spell (like Typing of the Dead); after that, each wrong key is a
  mistake and does not move you forward.
* Accuracy squared multiplies the effect: sloppy casting is weak casting.
* Crit chance is inversely proportional to how fast you typed.
* Your sanity changes the letters you must type (see words.corrupt).
* Clean casts build Focus (a damage streak); getting hit breaks it.
* Some enemies have a trait (HEX, STARE, DRINK, TOLL, DIRGE; see bestiary).
* When an enemy's attack bar fills, a DEFEND word appears. Type it in time to
  dodge, type it fast and clean to deflect. Lower health = harder words.
"""
import math
import random

import pygame

import art
import ui
from bestiary import ACTS
from entities import Layer, CombatEnemy, Projectile, FloatingText, burst, HERO_LOOK
from settings import (WIDTH, HEIGHT, GROUND_Y, WHITE, GRAY, GOLD, BONE, MISS_COL,
                      ELEMENT_COLORS, SANITY_COL, DEFLECT_ACCURACY,
                      DEFLECT_TIME_FRACTION, REFLECT_FRACTION, GREEN, SHIELD_COL)
from settings import (CRIT_MULT, FOCUS_MAX, FOCUS_ACCURACY, FOCUS_BREAK,
                      FOCUS_BONUS, HEAVY_DAMAGE)
from spells import cast_amount, crit_chance, KIND_LABEL
from typing_engine import TypingSession
from words import corrupt, sanity_tier, defense_prompt, TIER_NAMES, LETTERS

PANEL_Y = HEIGHT - 195            # top of the grimoire panel
STAGE_GROUND = PANEL_Y - 15       # where everyone's feet stand
PLAYER_X = 150
HERO_TALL = 120
BOSS_TALL = 205
# ordinary creatures shrink a little when several share the stage
FOE_TALL = {1: 170, 2: 140, 3: 112}
FOE_X = {1: [740], 2: [640, 840], 3: [555, 712, 870]}


class CombatScene:
    pausable = True
    show_sanity_fx = True

    def __init__(self, game, enemy_datas, boss, encounter_index):
        self.game = game
        self.run = game.run
        self.boss = boss
        self.encounter_index = encounter_index
        self.rng = random.Random()
        info = ACTS[self.run.act]
        self.scene = art.forest_scene()
        if self.scene:
            # a fixed spot in the woods, different for each fight
            self.camera = 400 + 730 * (encounter_index if encounter_index is not None else 5)
            self.dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            self.dim.fill((6, 2, 14, 90))    # darken the scene so the fighters stand out
        else:
            far, mid, trunks, near = art.parallax_layers(info, self.run.seed)
            self.layers = [Layer(far, 0.05), Layer(mid, 0.3)]
            self.ground = art.ground_tile(info["ground"])

        # enemies stand on the right, spread out
        self.enemies = []
        count = len(enemy_datas)
        for data, x in zip(enemy_datas, FOE_X[count]):
            tall = BOSS_TALL if boss else FOE_TALL[count]
            self.enemies.append(CombatEnemy(data, x, STAGE_GROUND, tall, self.rng))
        self.target = 0
        if self.run.has("bell"):
            for e in self.enemies:
                e.timer += 3.0
                e.timer_max = e.timer
        self.hexed = set()           # spell keys scrambled by a HEX

        self.hero = art.hero_frames(HERO_TALL)
        self.player_anim = 0.0
        self.cast_anim = 0.0
        self.hurt_flash = 0.0

        self.t = 0.0                 # combat clock; stops during DEFEND prompts
        self.texts = {}
        self.last_tier = sanity_tier(self.run.sanity)
        self.roll_all_texts()
        self.clear_input()

        self.defense = None
        self.defense_queue = []
        self.projectiles = []
        self.particles = pygame.sprite.Group()
        self.floaters = []
        self.intro = 1.6
        self.outcome = None
        self.outcome_timer = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.miss_flash = 0.0
        self.jitter_rng = random.Random()

    # --- word handling ---------------------------------------------------------
    def roll_text(self, key):
        """Pick the text the player must type for one spell.

        Two spells must never look identical or be a prefix of one another,
        so a clashing roll is thrown away and rolled again.
        """
        spell = self.run.get(key)
        sanity = self.run.sanity - (30 if key in self.hexed else 0)
        others = [v for k, v in self.texts.items() if k != key]
        text = spell.defn.incantation
        for _ in range(20):
            text = corrupt(spell.defn.incantation, sanity, self.rng)
            if not any(o.startswith(text) or text.startswith(o) for o in others):
                break
        self.texts[key] = text

    def roll_all_texts(self):
        self.texts = {}
        for spell in self.run.grimoire:
            self.roll_text(spell.key)

    def cost(self, spell):
        return spell.sanity_cost * (0.75 if self.run.has("ink") else 1.0)

    def clear_input(self):
        self.buffer = ""
        self.buffer_errors = 0
        self.buffer_start = None
        self.session = None
        self.locked = None

    def typed_count(self, key):
        if self.locked == key and self.session:
            return self.session.pos
        if self.buffer and self.texts[key].startswith(self.buffer):
            return len(self.buffer)
        return 0

    # --- targeting -------------------------------------------------------------
    def alive(self):
        return [e for e in self.enemies if not e.dead]

    def current_target(self):
        alive = self.alive()
        if not alive:
            return None
        if self.target >= len(self.enemies) or self.enemies[self.target].dead:
            self.target = self.enemies.index(alive[0])
        return self.enemies[self.target]

    def cycle_target(self, step):
        alive = self.alive()
        if len(alive) < 2:
            return
        current = self.current_target()
        i = alive.index(current)
        self.target = self.enemies.index(alive[(i + step) % len(alive)])
        self.game.sound.play("select")

    # --- input -----------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.intro > 0 or self.outcome:
            return
        if event.key in (pygame.K_TAB, pygame.K_RIGHT):
            self.cycle_target(1)
            return
        if event.key == pygame.K_LEFT:
            self.cycle_target(-1)
            return
        if event.key == pygame.K_BACKSPACE:
            if not self.defense and (self.session or self.buffer):
                self.clear_input()
                self.game.sound.play("select")
            return
        ch = event.unicode.lower() if event.unicode else ""
        if len(ch) != 1 or (ch not in LETTERS and ch != " "):
            return
        if self.defense:
            self.type_defense(ch)
        else:
            self.type_spell(ch)

    def count_key(self, ok):
        if ok:
            self.run.keys_ok += 1
            self.game.sound.play("key")
        else:
            self.run.keys_miss += 1
            self.miss_flash = 0.15
            self.game.sound.play("miss")

    def type_spell(self, ch):
        if not self.session and not self.buffer and ch == " ":
            return  # a stray space between spells is not a mistake
        if self.session:
            result = self.session.feed(ch, self.t)
            self.count_key(result != "miss")
            if result == "done":
                self.cast(self.locked, self.session)
            return
        new = self.buffer + ch
        order = [s.key for s in self.run.grimoire]
        candidates = [k for k in order if self.texts[k].startswith(new)]
        if not candidates:
            self.count_key(False)
            if self.buffer:
                self.buffer_errors += 1
            elif ch != " ":
                self.say(f"No incantation begins with '{ch}'", 1.0)
            return
        self.count_key(True)
        if self.buffer_start is None:
            self.buffer_start = self.t
        self.buffer = new
        exact = [k for k in candidates if self.texts[k] == new]
        if len(candidates) == 1 or exact:
            key = exact[0] if exact else candidates[0]
            session = TypingSession(self.texts[key], self.buffer_start)
            session.pos = len(new)
            session.errors = self.buffer_errors
            self.buffer = ""
            self.buffer_errors = 0
            self.buffer_start = None
            self.session = session
            self.locked = key
            self.game.sound.play("lock")
            if session.done:
                session.end = self.t
                self.cast(key, session)

    # --- casting ---------------------------------------------------------------
    def player_center(self):
        return (PLAYER_X, STAGE_GROUND - 60)

    def cast(self, key, session):
        run = self.run
        owned = run.get(key)
        spell = owned.defn
        accuracy = session.accuracy()
        cps = session.cps(self.t)
        amount, crit = cast_amount(owned, accuracy, cps, self.rng.random(), run.focus,
                                   2.5 if run.has("lens") else CRIT_MULT)
        cost = self.cost(spell)
        run.change_sanity(-cost)
        run.casts += 1
        # focus: clean casts build a streak, sloppy ones break it
        if accuracy >= FOCUS_ACCURACY:
            run.focus = min(FOCUS_MAX, run.focus + 1)
        elif accuracy < FOCUS_BREAK:
            run.focus = 0
        if accuracy >= 1.0 and spell.letters >= 20:
            self.game.achieve("finalword")
        if run.casts >= 40:
            self.game.achieve("flare")
        self.clear_input()
        self.cast_anim = 0.4
        color = ELEMENT_COLORS[spell.element]
        px, py = self.player_center()
        line = f"{spell.name}  {accuracy * 100:.0f}%  {cps:.1f} c/s"
        self.floaters.append(FloatingText(line, (px + 40, py - 70), WHITE, 22, 1.6, 25))
        if crit:
            self.floaters.append(FloatingText("CRIT!", (px + 40, py - 95), GOLD, 34, 1.4, 30))
            self.game.sound.play("crit")
        else:
            self.game.sound.play("cast")
        burst(self.particles, (px + 20, py - 20), color, 14, speed=(40, 160))

        kind = spell.kind
        start = (px + 22, py - 22)
        if kind in ("damage", "drain", "dot", "execute"):
            target = self.current_target()
            if target:
                self.projectiles.append(Projectile(
                    start, target, color,
                    lambda e, s=spell, a=amount, c=crit: self.hit(e, s, a, c),
                    size=8 + int(spell.letters / 3)))
        elif kind in ("aoe", "slow"):
            for i, e in enumerate(self.alive()):
                self.projectiles.append(Projectile(
                    start, e, color,
                    lambda en, s=spell, a=amount, c=crit: self.hit(en, s, a, c),
                    size=8, delay=i * 0.08))
        elif kind == "heal":
            run.heal(amount)
            self.floaters.append(FloatingText(f"+{amount:.0f} HP", (px, py - 40), GREEN, 32))
            burst(self.particles, (px, py), GREEN, 25)
            self.game.sound.play("heal")
        elif kind == "pact":
            run.heal(amount)
            self.floaters.append(FloatingText(f"+{amount:.0f} HP", (px, py - 40), GREEN, 32))
            burst(self.particles, (px, py), (150, 60, 220), 30)
        elif kind == "shield":
            run.add_shield(amount)
            self.floaters.append(FloatingText(f"+{amount:.0f} shield", (px, py - 40), SHIELD_COL, 30))
            self.game.sound.play("heal")
        elif kind == "sanity":
            run.change_sanity(amount)
            self.floaters.append(FloatingText(f"+{amount:.0f} sanity", (px, py - 40), SANITY_COL, 30))
            self.game.sound.play("heal")
        if cost:
            self.floaters.append(FloatingText(f"-{cost:.0f} sanity", (px - 30, py + 10),
                                              SANITY_COL, 22, 1.2, 30))
        self.hexed.discard(key)
        self.roll_text(key)

    def hit(self, enemy, spell, amount, crit):
        if enemy.dead:
            alive = self.alive()
            if not alive or spell.kind in ("aoe", "slow"):
                return
            enemy = alive[0]
        color = ELEMENT_COLORS[spell.element]
        cx, cy = enemy.center
        if spell.kind == "dot":
            enemy.dots.append([amount / 6, 6, 1.0])
            self.floaters.append(FloatingText("ROTTING", (cx, cy - 40), color, 28))
        else:
            if spell.kind == "execute" and enemy.hp < enemy.max_hp * 0.3:
                amount *= 2
                self.floaters.append(FloatingText("EXECUTED", (cx, cy - 62), color, 26))
            dealt = enemy.take(amount)
            self.run.best_hit = max(self.run.best_hit, int(amount))
            size = 44 if crit else 32
            self.floaters.append(FloatingText(f"{amount:.0f}", (cx, cy - 30),
                                              GOLD if crit else WHITE, size))
            if spell.lifesteal:
                heal = dealt * spell.lifesteal
                self.run.heal(heal)
                px, py = self.player_center()
                self.floaters.append(FloatingText(f"+{heal:.0f} HP", (px, py - 40), GREEN, 28))
            if spell.chill:
                enemy.timer += spell.chill
                enemy.timer_max = max(enemy.timer_max, enemy.timer)
            if spell.kind == "slow":
                enemy.timer += 4.0
                enemy.timer_max = max(enemy.timer_max, enemy.timer)
                self.floaters.append(FloatingText("DELAYED", (cx, cy - 60), color, 24))
        burst(self.particles, (cx, cy), color, 30 if crit else 16)
        self.game.sound.play("hit")
        if crit:
            self.game.add_shake(0.3, 8)
        self.check_death(enemy)

    def check_death(self, enemy):
        if enemy.hp <= 0 and not enemy.dead:
            enemy.dead = True
            enemy.hp = 0
            self.run.kills += 1
            burst(self.particles, enemy.center, (30, 20, 40), 40, speed=(80, 300))
            burst(self.particles, enemy.center, (200, 60, 80), 20)
            self.defense_queue = [e for e in self.defense_queue if e is not enemy]
            enemy.windup = False
            if self.defense and self.defense["enemy"] is enemy:
                self.floaters.append(FloatingText("INTERRUPTED", (WIDTH // 2, 150), GOLD, 30))
                self.defense = None

    # --- defending -------------------------------------------------------------
    def start_defense(self, enemy):
        hp_fraction = self.run.hp / self.run.max_hp
        if enemy.trait == "dirge":
            hp_fraction = min(hp_fraction, 0.6)   # never the short words
        heavy = enemy.next_is_heavy()
        enemy.attacks += 1
        if heavy:
            # a heavy blow asks for a word one step harder than your health would
            hp_fraction = max(0.16, hp_fraction - 0.34) if hp_fraction > 0.16 else hp_fraction
        word, limit = defense_prompt(hp_fraction, self.rng)
        if self.run.has("scarf"):
            limit += 0.7
        self.defense = dict(enemy=enemy, session=TypingSession(word, 0.0),
                            limit=limit, elapsed=0.0, heavy=heavy,
                            damage=enemy.dmg * (HEAVY_DAMAGE if heavy else 1.0))
        enemy.windup = True      # it rears up while you type
        self.game.sound.play("warn")

    def type_defense(self, ch):
        d = self.defense
        result = d["session"].feed(ch, d["elapsed"])
        self.count_key(result != "miss")
        if result == "done":
            self.resolve_defense(True)

    def resolve_defense(self, finished):
        d = self.defense
        self.defense = None
        enemy = d["enemy"]
        session = d["session"]
        enemy.strike()
        px, py = self.player_center()
        if finished:
            used = d["elapsed"] / d["limit"]
            if session.accuracy() >= DEFLECT_ACCURACY and used <= DEFLECT_TIME_FRACTION:
                reflect = d["damage"] * (1.0 if self.run.has("thimble") else REFLECT_FRACTION)
                if self.run.deflects + 1 >= 8:
                    self.game.achieve("thorn")
                enemy.take(reflect)
                self.run.deflects += 1
                self.floaters.append(FloatingText("DEFLECT!", (px + 30, py - 70), (150, 220, 255), 40))
                self.floaters.append(FloatingText(f"{reflect:.0f}", (enemy.center[0], enemy.center[1] - 30),
                                                  (150, 220, 255), 30))
                burst(self.particles, (px + 40, py - 10), (150, 220, 255), 25)
                self.game.sound.play("deflect")
                self.check_death(enemy)
            else:
                self.floaters.append(FloatingText("DODGE", (px + 30, py - 70), WHITE, 36))
                self.game.sound.play("select")
            return
        fraction = 0.5 if session.progress >= 0.5 else 1.0
        label = "GRAZED" if fraction < 1 else "HIT"
        lost = self.run.take_damage(d["damage"] * fraction)
        dread = enemy.dread * fraction
        self.run.change_sanity(-dread)
        self.floaters.append(FloatingText(f"{label} -{lost:.0f}", (px, py - 60), MISS_COL, 34))
        self.floaters.append(FloatingText(f"-{dread:.0f} sanity", (px, py - 30), SANITY_COL, 24))
        burst(self.particles, (px, py), (200, 40, 50), 20)
        self.hurt_flash = 0.3
        self.game.add_shake(0.35, 10 if fraction == 1 else 5)
        self.game.sound.play("hurt")
        self.run.focus = 0
        if enemy.trait == "drink" and not enemy.dead:
            drunk = min(enemy.max_hp - enemy.hp, d["damage"] * fraction)
            if drunk > 0:
                enemy.hp += drunk
                self.floaters.append(FloatingText(f"+{drunk:.0f}", (enemy.center[0], enemy.center[1] - 30),
                                                  GREEN, 26))
        if enemy.trait == "hex":
            self.hex_spell(enemy)

    def toll(self, enemy, allies):
        """The bell rings instead of a blow: allies hurry, or your mind pays."""
        cx, cy = enemy.center
        self.floaters.append(FloatingText("TOLL", (cx, cy - 50), (160, 255, 220), 30))
        self.game.sound.play("warn")
        if allies:
            for other in allies:
                other.timer = max(0.3, other.timer - 2.0)
        else:
            self.run.change_sanity(-4)
            px, py = self.player_center()
            self.floaters.append(FloatingText("-4 sanity", (px, py - 30), SANITY_COL, 24))
            self.hex_spell(enemy)

    def hex_spell(self, enemy):
        """Scramble one spell until it is next cast."""
        keys = [s.key for s in self.run.grimoire if s.key not in self.hexed]
        if not keys:
            return
        key = self.rng.choice(keys)
        self.hexed.add(key)
        if self.locked == key or self.buffer:
            self.clear_input()
        self.roll_text(key)
        self.say(f"{enemy.name} hexes {self.run.get(key).defn.name}!")

    # --- update ----------------------------------------------------------------
    def say(self, text, seconds=2.5):
        self.message = text
        self.message_timer = seconds

    def update(self, dt):
        self.player_anim += dt
        self.cast_anim = max(0.0, self.cast_anim - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.miss_flash = max(0.0, self.miss_flash - dt)
        self.message_timer = max(0.0, self.message_timer - dt)
        self.particles.update(dt)
        for f in self.floaters:
            f.update(dt)
        self.floaters = [f for f in self.floaters if f.alive]
        for e in self.enemies:
            rot = e.update(dt)
            if rot > 0:
                e.take(rot)
                self.floaters.append(FloatingText(f"{rot:.0f}", (e.center[0] + 20, e.center[1] - 20),
                                                  ELEMENT_COLORS["rot"], 24))
                self.check_death(e)

        if self.outcome:
            self.outcome_timer -= dt
            if self.outcome_timer <= 0:
                if self.outcome == "win":
                    self.game.combat_won(self)
                else:
                    self.game.game_over(self.outcome)
            return
        if self.intro > 0:
            self.intro -= dt
            return

        # sanity tier changed -> the words twist (or straighten)
        tier = sanity_tier(self.run.sanity)
        if tier != self.last_tier and not (self.session or self.buffer):
            self.say("Your thoughts clear..." if tier < self.last_tier
                     else "The words begin to twist...")
            self.last_tier = tier
            self.clear_input()
            self.roll_all_texts()

        for p in self.projectiles:
            p.update(dt)
        self.projectiles = [p for p in self.projectiles if not p.done]

        if self.defense:
            self.defense["elapsed"] += dt
            if self.defense["elapsed"] >= self.defense["limit"]:
                self.resolve_defense(False)
        else:
            self.t += dt
            for e in self.alive():
                if e.trait == "stare":
                    self.run.change_sanity(-(0.3 if e.boss else 0.4) * dt)
                e.timer -= dt
                if e.timer <= 0:
                    e.reset_timer(self.rng)
                    allies = [o for o in self.alive() if o is not e]
                    if e.trait == "rally" and self.rng.random() < (0.6 if allies else 0.3):
                        self.toll(e, allies)
                    else:
                        self.defense_queue.append(e)
                if e.boss and not e.raged and e.hp < e.max_hp / 2:
                    e.raged = True
                    e.timer = min(e.timer, 2.0)
                    self.run.change_sanity(-6)
                    self.say(e.rage_text + "  (-6 sanity)", 3.0)
                    self.game.add_shake(0.6, 10)
                    self.game.sound.play("warn")
            self.defense_queue = [e for e in self.defense_queue if not e.dead]
            if self.defense_queue:
                self.start_defense(self.defense_queue.pop(0))

        if self.run.dead:
            self.outcome = "madness" if self.run.sanity <= 0 else "wounds"
            self.outcome_timer = 2.2
            self.clear_input()
            col = (150, 60, 220) if self.outcome == "madness" else (200, 40, 50)
            burst(self.particles, self.player_center(), col, 50, speed=(40, 220), life=(0.6, 1.8))
            self.defense = None
            self.game.sound.play("death")
            return
        if not self.alive() and not self.projectiles:
            self.outcome = "win"
            self.outcome_timer = 2.0     # long enough for the death sheet to play
            self.defense = None

    # --- drawing -----------------------------------------------------------------
    def hero_image(self):
        """The boy's picture: his look follows his sanity, his pose the moment."""
        tier = sanity_tier(self.run.sanity)
        poses = self.hero["looks"][HERO_LOOK[tier]]["right"]
        if self.outcome in ("madness", "wounds"):
            t = 2.2 - self.outcome_timer
            if self.hero["death"]:
                return self.hero["death"][min(3, int(t / 0.45))]
            # no painted death yet: he tips over and fades
            fallen = pygame.transform.rotate(poses["idle"], min(90, t * 150))
            fallen.set_alpha(max(0, int(255 * (1 - max(0.0, t - 0.9) / 1.2))))
            return fallen
        if self.cast_anim > 0:
            return poses["cast"]
        return poses["idle"]

    def draw_world(self, surface):
        if self.scene:
            # shift the scene up so its path lines up with the fighters' feet
            self.scene.draw(surface, self.run.act, self.camera, self.player_anim,
                            STAGE_GROUND - GROUND_Y)
            surface.blit(self.dim, (0, 0))
        else:
            for layer in self.layers:
                layer.draw(surface, 0)
            tw = self.ground.get_width()
            for x in range(0, WIDTH + tw, tw):
                surface.blit(self.ground, (x, STAGE_GROUND))
        pygame.draw.rect(surface, (14, 10, 22), (0, PANEL_Y, WIDTH, HEIGHT - PANEL_Y))
        target = self.current_target()
        for e in self.enemies:
            if not e.dead:
                shade = art.shadow(e.body.width + 20)
                surface.blit(shade, shade.get_rect(center=(e.body.centerx, STAGE_GROUND - 2)))
            e.draw(surface, e is target and len(self.alive()) > 1)
        # the boy
        px, py = self.player_center()
        shade = art.shadow(70)
        surface.blit(shade, shade.get_rect(center=(PLAYER_X, STAGE_GROUND - 2)))
        light = art.glow(100, (150, 220, 255), 70)
        surface.blit(light, light.get_rect(center=(px, py)))
        img = self.hero_image()
        if self.hurt_flash > 0:
            img = img.copy()
            img.fill((160, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(img, img.get_rect(midbottom=(PLAYER_X, STAGE_GROUND)))
        if self.run.shield > 0:
            r = 66 + int(math.sin(self.player_anim * 4) * 2)
            bubble = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            a = int(60 + 120 * self.run.shield / 60)
            pygame.draw.circle(bubble, (*SHIELD_COL, a), (r + 2, r + 2), r, 3)
            surface.blit(bubble, bubble.get_rect(center=(px, py)))
        for p in self.projectiles:
            p.draw(surface)
        self.particles.draw(surface)
        for f in self.floaters:
            f.draw(surface)

    def draw_ui(self, surface):
        game = self.game
        game.draw_hud(surface)
        self.draw_focus(surface)
        self.draw_grimoire(surface)
        if self.message_timer > 0:
            for i, line in enumerate(ui.wrap(self.message, ui.font(24), 350)):
                ui.draw_text(surface, ui.font(24), line, BONE, topleft=(16, 106 + i * 21))
        if self.intro > 0:
            title = self.enemies[0].name if self.boss else "Shadows close in!"
            ui.panel(surface, (WIDTH // 2 - 260, 120, 520, 90), 210)
            ui.draw_text(surface, ui.font(52), title, BONE, center=(WIDTH // 2, 155))
            ui.draw_text(surface, ui.font(22), "Type an incantation to cast it",
                         GRAY, center=(WIDTH // 2, 190))
        if self.defense:
            self.draw_defense(surface)
        if self.outcome == "win":
            ui.draw_text(surface, ui.font(64), "The shadows fade.", BONE, center=(WIDTH // 2, 170))

    def draw_focus(self, surface):
        focus = self.run.focus
        ui.draw_text(surface, ui.font(20), "Focus", GOLD if focus else GRAY, topleft=(16, 80))
        for i in range(FOCUS_MAX):
            center = (84 + i * 14, 88)
            if i < focus:
                pygame.draw.circle(surface, GOLD, center, 5)
            else:
                pygame.draw.circle(surface, GRAY, center, 5, 1)
        if focus:
            ui.draw_text(surface, ui.font(20), f"+{focus * FOCUS_BONUS * 100:.0f}%", GOLD,
                         topleft=(160, 80))

    def draw_defense(self, surface):
        d = self.defense
        session = d["session"]
        word = session.target
        cx, y0 = 660, 4
        edge = (255, 60, 200) if d["heavy"] else (200, 70, 70)
        ui.panel(surface, (cx - 280, y0, 560, 118), 240, border=edge)
        if d["heavy"]:
            pygame.draw.rect(surface, edge, (cx - 280, y0, 560, 118), 3)
            title = "HEAVY BLOW!  " + d["enemy"].attack_text
        else:
            title = d["enemy"].attack_text + "  DEFEND:"
        title = ui.fit(title, ui.font(24), 540)
        ui.draw_text(surface, ui.font(24), title, (255, 150, 230) if d["heavy"] else (255, 140, 120),
                     center=(cx, y0 + 17))
        size = 34
        width = ui.font(size, mono=True).size("m")[0] * len(word)
        ui.draw_incantation(surface, word, session.pos, (cx - width // 2, y0 + 38), size)
        left = 1 - d["elapsed"] / d["limit"]
        deflect_mark = 1 - DEFLECT_TIME_FRACTION
        bar = (cx - 240, y0 + 80, 480, 10)
        ui.draw_bar(surface, bar, left, (220, 80, 70) if left < deflect_mark else (240, 200, 100))
        mx = bar[0] + int(bar[2] * deflect_mark)
        pygame.draw.line(surface, WHITE, (mx, bar[1] - 4), (mx, bar[1] + 13), 2)
        ui.draw_text(surface, ui.font(18), "finish before the line to deflect", GRAY,
                     midleft=(bar[0], y0 + 107))

    def draw_grimoire(self, surface):
        run = self.run
        ui.panel(surface, (0, PANEL_Y, WIDTH, HEIGHT - PANEL_Y), 225)
        tier = sanity_tier(run.sanity)
        jitter = [0, 0.4, 1.2, 2.2][tier]
        col_w = WIDTH // 2
        row_h = 41
        for i, owned in enumerate(run.grimoire):
            spell = owned.defn
            col, row = i // 4, i % 4
            x = 14 + col * col_w
            y = PANEL_Y + 9 + row * row_h
            key = owned.key
            typed = self.typed_count(key)
            dim = self.locked is not None and self.locked != key
            if self.locked == key:
                pygame.draw.rect(surface, (60, 50, 30), (x - 6, y - 3, col_w - 16, row_h - 2),
                                 border_radius=4)
            name_col = GRAY if dim else ELEMENT_COLORS[spell.element]
            label = f"{spell.name}  Lv{owned.level}"
            if key in self.hexed:
                label += "  HEXED"
            ui.draw_text(surface, ui.font(20), label, name_col, topleft=(x, y - 3))
            info = f"{KIND_LABEL[spell.kind]} {owned.strength():.0f}"
            cost_col = MISS_COL if self.cost(spell) >= run.sanity else SANITY_COL
            ui.draw_text(surface, ui.font(18), info, GRAY, topright=(x + col_w - 104, y - 3))
            ui.draw_text(surface, ui.font(18), f"-{self.cost(spell):.0f} san",
                         cost_col, topright=(x + col_w - 26, y - 3))
            ui.draw_incantation(surface, self.texts[key], typed, (x, y + 14), 18,
                                jitter=0 if dim else jitter,
                                color=(90, 88, 96) if dim else WHITE,
                                rng=self.jitter_rng)
        # footer: hints and live typing stats
        foot_y = HEIGHT - 13
        if self.session:
            acc = self.session.accuracy()
            cps = self.session.cps(self.t)
            txt = (f"accuracy {acc * 100:.0f}%    speed {cps:.1f} c/s    "
                   f"crit chance {crit_chance(cps) * 100:.0f}%")
            ui.draw_text(surface, ui.font(20), txt, GOLD, center=(WIDTH // 2, foot_y))
        else:
            ui.draw_text(surface, ui.font(18),
                         "Type a spell to cast    Tab: target    Backspace: cancel    Esc: pause",
                         GRAY, center=(WIDTH // 2, foot_y))
        ui.draw_text(surface, ui.font(18), f"Mind: {TIER_NAMES[tier]}",
                     SANITY_COL, topright=(WIDTH - 10, PANEL_Y - 20))
        if self.miss_flash > 0:
            pygame.draw.rect(surface, MISS_COL, (0, PANEL_Y, WIDTH, HEIGHT - PANEL_Y), 3)
