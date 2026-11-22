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
* Enemies keep no steady beat: their bars fill unevenly, some strikes come
  early, some rear up and hold back (a feint), some blows come twice (a
  flurry), and heavy blows are rolled at random (see STYLES in bestiary.py).
"""
import math
import random

import pygame

import art
import ui
from bestiary import act_info
from entities import (Layer, CombatEnemy, Projectile, FloatingText, burst, Ring,
                      RuneCircle)
from settings import (WIDTH, HEIGHT, GROUND_Y, WHITE, GRAY, GOLD, BONE, MISS_COL,
                      ELEMENT_COLORS, SANITY_COL, DEFLECT_ACCURACY,
                      DEFLECT_TIME_FRACTION, REFLECT_FRACTION, GREEN, SHIELD_COL)
from settings import (CRIT_MULT, FOCUS_MAX, FOCUS_ACCURACY, FOCUS_BREAK,
                      FOCUS_BONUS, HEAVY_DAMAGE, BURNOUT_CASTS, HEAT_FADE_TIME,
                      BURNOUT_TIME, SOOTHE_FADE, DIFFICULTY)
from spells import (cast_amount, crit_chance, effect_text, cost_text, TARGET_KINDS,
                    ALL_FOES_KINDS, WEAKEN, WEAKEN_FLOOR, echo_fraction, desperate_bonus)
from typing_engine import TypingSession
from words import corrupt, sanity_tier, defense_prompt, LETTERS

ROW_H = 46                        # one spell in the grimoire panel
PANEL_Y = HEIGHT - (4 * ROW_H + 30)   # top of the grimoire panel
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
        self.music = "boss" if boss else "battle"
        self.encounter_index = encounter_index
        self.rng = random.Random()
        info = act_info(self.run.act)
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
        self.hexed = set()           # spell keys scrambled by a Hex
        # Burnout: every cast heats its spell; heat fades with time. A spell
        # cast too often in a row burns out and cannot be cast for a while.
        self.heat = {}               # spell key -> heat (one cast = 1.0)
        self.burnt = {}              # spell key -> seconds left burnt out
        self.empower = 0.0           # bonus waiting for the next attack (Whisper Pact)
        self.regen = [0.0, 0.0]      # [sanity per second, seconds left] (Mend)
        self.soothes = 0             # healing spells cast this fight (each is weaker)
        self.mirror = 0.0            # Mirror Veil: bonus damage waiting to turn a blow back
        self.last_release = None     # (spell, amount) of the last spell, for Echo
        self.level = DIFFICULTY.get(self.run.difficulty, DIFFICULTY["normal"])
        self.effects = []            # casting circles and impact rings

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
            # the click climbs in pitch as the word nears its end
            typing = self.defense["session"] if self.defense else self.session
            self.game.sound.play_key(typing.progress if typing else 0.0)
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
        matching = [k for k in order if self.texts[k].startswith(new)]
        candidates = [k for k in matching if self.burnt.get(k, 0) <= 0]
        if matching and not candidates:
            # only burnt-out spells start like this: say so, but it is not a typo
            key = matching[0]
            self.say(f"{self.run.get(key).defn.name} is burnt out for "
                     f"{self.burnt[key]:.0f} more seconds.", 1.5)
            self.game.sound.play("miss")
            return
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
        # Paying for a spell never takes the last point of sanity, but a spell
        # you cannot fully pay for comes out weaker, in proportion.
        cost = self.cost(spell)
        paid = min(cost, max(0.0, run.sanity - 1))
        starved = cost > 0 and paid < cost
        if starved:
            amount *= max(0.25, paid / cost)
        run.change_sanity(-cost)
        run.casts += 1
        # focus: clean casts build a streak, sloppy ones break it
        if accuracy >= FOCUS_ACCURACY:
            if run.focus < FOCUS_MAX:
                self.game.sound.play("focus")
            run.focus = min(FOCUS_MAX, run.focus + 1)
        elif accuracy < FOCUS_BREAK:
            run.focus = 0
        if accuracy >= 1.0 and spell.letters >= 20:
            self.game.achieve("finalword")
        if run.casts >= 40:
            self.game.achieve("flare")
        self.clear_input()
        # burnout: the same spell again and again overheats
        self.heat[key] = self.heat.get(key, 0.0) + 1.0
        if self.heat[key] >= BURNOUT_CASTS:
            self.heat[key] = 0.0
            self.burnt[key] = BURNOUT_TIME
            self.game.sound.play("burnout")
            self.say(f"{spell.name} burns out! Use another spell for {BURNOUT_TIME:.0f} seconds.")

        px, py = self.player_center()
        if spell.kind == "desperate":
            # Blood Price: what you have lost is what it spends
            amount *= desperate_bonus(run.sanity + paid, run.max_sanity)
        if spell.kind in TARGET_KINDS + ALL_FOES_KINDS and self.empower:
            amount *= 1 + self.empower
            self.empower = 0.0
            self.floaters.append(FloatingText("Empowered!", (px + 40, py - 118), (190, 120, 255), 26))

        # the casting animation: he raises the book, a rune circle opens at his
        # feet, and the bolt leaves a moment later
        self.cast_anim = 0.55
        self.effects.append(RuneCircle((PLAYER_X, STAGE_GROUND - 3), ELEMENT_COLORS[spell.element]))
        if starved:
            self.say("Too little sanity left: the spell comes out weak.", 2.0)
        line = f"{spell.name}  {accuracy * 100:.0f}%  {cps:.1f} c/s"
        self.floaters.append(FloatingText(line, (px + 40, py - 78), WHITE, 22, 1.6, 25))
        if crit:
            self.floaters.append(FloatingText("Crit!", (px + 40, py - 104), GOLD, 34, 1.4, 30))
            self.game.sound.play("crit")
        self.game.sound.play_cast(spell.element)
        if cost:
            self.floaters.append(FloatingText(f"-{cost:.0f} sanity", (px - 30, py + 10),
                                              SANITY_COL, 22, 1.2, 30))
        if spell.kind == "echo":
            self.echo(amount)
        else:
            self.release(spell, amount, crit)
            self.last_release = (spell, amount)
        self.hexed.discard(key)
        self.roll_text(key)

    def echo(self, amount):
        """Echo: the last spell sounds again, weaker, and costs nothing."""
        px, py = self.player_center()
        if not self.last_release:
            self.floaters.append(FloatingText("Nothing to echo", (px, py - 40), GRAY, 26))
            return
        spell, last = self.last_release
        share = echo_fraction(amount)
        self.floaters.append(FloatingText(f"Echo: {spell.name} {share * 100:.0f}%",
                                          (px + 40, py - 130), (200, 180, 255), 26))
        self.release(spell, last * share, False)

    def release(self, spell, amount, crit):
        """What a spell does once it leaves the book: bolts at foes, or a
        ring of light around the boy for the spells cast on himself."""
        run = self.run
        kind = spell.kind
        color = ELEMENT_COLORS[spell.element]
        px, py = self.player_center()
        burst(self.particles, (px + 20, py - 20), color, 18, speed=(40, 180))
        start = (px + 22, py - 22)
        release = 0.16                 # the bolt waits for the circle to open
        if kind in TARGET_KINDS:
            target = self.current_target()
            if target:
                self.projectiles.append(Projectile(
                    start, target, color,
                    lambda e, s=spell, a=amount, c=crit: self.hit(e, s, a, c),
                    size=8 + int(spell.letters / 3), delay=release))
        elif kind in ALL_FOES_KINDS:
            for i, e in enumerate(self.alive()):
                self.projectiles.append(Projectile(
                    start, e, color,
                    lambda en, s=spell, a=amount, c=crit: self.hit(en, s, a, c),
                    size=8, delay=release + i * 0.08))
        else:
            # spells cast on himself: a ring of light closes around him
            self.effects.append(Ring((px, py), color, radius=90, life=0.5))
            self.game.sound.play({"shield": "shield", "pact": "pact",
                                  "mirror": "shield"}.get(kind, "heal"))
        if kind in ("sanity", "regen"):
            # every healing spell in one fight is weaker than the last
            amount *= SOOTHE_FADE ** self.soothes
            self.soothes += 1
        if kind == "sanity":
            run.change_sanity(amount)
            self.floaters.append(FloatingText(f"+{amount:.0f} sanity", (px, py - 40), SANITY_COL, 30))
            for hexed in list(self.hexed):          # Clarity also lifts every hex
                self.hexed.discard(hexed)
                self.roll_text(hexed)
        elif kind == "regen":
            self.regen = [amount / 6, 6.0]
            self.floaters.append(FloatingText(f"+{amount:.0f} sanity over 6 s", (px, py - 40),
                                              GREEN, 26))
        elif kind == "pact":
            self.empower = amount / 100
            self.floaters.append(FloatingText(f"Next spell +{amount:.0f}%", (px, py - 40),
                                              (190, 120, 255), 28))
        elif kind == "shield":
            run.add_shield(amount)
            self.floaters.append(FloatingText(f"+{amount:.0f} shield", (px, py - 40), SHIELD_COL, 30))
        elif kind == "mirror":
            self.mirror = max(self.mirror, amount)
            self.floaters.append(FloatingText("Mirror raised", (px, py - 40), (200, 230, 255), 30))

    def hit(self, enemy, spell, amount, crit):
        if enemy.dead:
            alive = self.alive()
            if not alive or spell.kind in ("aoe", "slow"):
                return
            enemy = alive[0]
        color = ELEMENT_COLORS[spell.element]
        cx, cy = enemy.center
        if spell.kind in ("dot", "plague"):
            enemy.dots.append([amount / 6, 6, 1.0])
            self.floaters.append(FloatingText("Rotting", (cx, cy - 40), color, 28))
        else:
            if spell.kind == "execute" and enemy.hp < enemy.max_hp * 0.3:
                amount *= 2
                self.floaters.append(FloatingText("Executed", (cx, cy - 62), color, 26))
            dealt = enemy.take(amount)
            self.run.best_hit = max(self.run.best_hit, int(amount))
            size = 44 if crit else 32
            self.floaters.append(FloatingText(f"{amount:.0f}", (cx, cy - 30),
                                              GOLD if crit else WHITE, size))
            if spell.lifesteal:
                heal = dealt * spell.lifesteal
                self.run.change_sanity(heal)
                px, py = self.player_center()
                self.floaters.append(FloatingText(f"+{heal:.0f} sanity", (px, py - 40), GREEN, 28))
            if spell.chill:
                enemy.timer += spell.chill
                enemy.timer_max = max(enemy.timer_max, enemy.timer)
            if spell.kind == "slow":
                enemy.timer += 4.0
                enemy.timer_max = max(enemy.timer_max, enemy.timer)
                self.floaters.append(FloatingText("Delayed", (cx, cy - 60), color, 24))
            if spell.kind == "weaken" and not enemy.dead:
                floor = enemy.base_dmg * WEAKEN_FLOOR
                enemy.dmg = max(floor, enemy.dmg * WEAKEN)
                self.floaters.append(FloatingText("Weakened", (cx, cy - 60), color, 24))
            if spell.kind == "interrupt" and not enemy.dead:
                # its attack bar is knocked back to empty, and a feint is broken off
                enemy.feinting = 0.0
                enemy.windup = False
                enemy.reset_timer(self.rng)
                self.floaters.append(FloatingText("Staggered", (cx, cy - 60), color, 24))
        burst(self.particles, (cx, cy), color, 30 if crit else 16)
        self.effects.append(Ring((cx, cy), color, radius=90 if crit else 60))
        self.game.sound.play("hit")
        if crit:
            self.game.add_shake(0.3, 8)
        self.check_death(enemy)

    def check_death(self, enemy):
        if enemy.hp <= 0 and not enemy.dead:
            enemy.dead = True
            enemy.hp = 0
            self.run.kills += 1
            self.game.sound.play("enemy_die")
            burst(self.particles, enemy.center, (30, 20, 40), 40, speed=(80, 300))
            burst(self.particles, enemy.center, (200, 60, 80), 20)
            self.defense_queue = [e for e in self.defense_queue if e is not enemy]
            enemy.windup = False
            if self.defense and self.defense["enemy"] is enemy:
                self.floaters.append(FloatingText("Interrupted", (WIDTH // 2, 150), GOLD, 30))
                self.defense = None

    # --- defending -------------------------------------------------------------
    def start_defense(self, enemy):
        hp_fraction = self.run.sanity / self.run.max_sanity    # sanity is his health
        if enemy.trait == "dirge":
            hp_fraction = min(hp_fraction, 0.6)   # never the short words
        heavy = enemy.next_is_heavy()
        enemy.attacks += 1
        flurry = enemy.chain > 0
        if heavy:
            # a heavy blow asks for a word one step harder than your health would
            hp_fraction = max(0.21, hp_fraction - 0.3) if hp_fraction > 0.21 else hp_fraction
        word, limit = defense_prompt(hp_fraction, self.rng, self.level["defend"])
        if self.run.has("scarf"):
            limit += 0.7
        self.defense = dict(enemy=enemy, session=TypingSession(word, 0.0),
                            limit=limit, elapsed=0.0, heavy=heavy, flurry=flurry,
                            damage=enemy.dmg * (HEAVY_DAMAGE if heavy else 1.0))
        enemy.windup = True      # it rears up while you type
        self.game.sound.play("heavy" if heavy else "warn")

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
        self.land_blow(d, enemy, finished)
        if not enemy.dead and enemy.after_blow(self.rng):
            # a flurry: it comes again almost at once
            cx, cy = enemy.center
            self.floaters.append(FloatingText("Again!", (cx, cy - 70), (255, 150, 120), 30))

    def land_blow(self, d, enemy, finished):
        """How one blow ends: dodged, deflected, mirrored, grazed or taken."""
        session = d["session"]
        enemy.strike()
        px, py = self.player_center()
        if not finished and self.mirror > 0:
            # Mirror Veil: the blow that would have landed turns back on its maker
            reflect = d["damage"] + self.mirror
            self.mirror = 0.0
            enemy.take(reflect)
            self.floaters.append(FloatingText("Mirrored!", (px + 30, py - 70), (200, 230, 255), 40))
            self.floaters.append(FloatingText(f"{reflect:.0f}", (enemy.center[0], enemy.center[1] - 30),
                                              (200, 230, 255), 30))
            self.effects.append(Ring((px, py), (200, 230, 255), radius=110, life=0.5))
            self.game.sound.play("deflect")
            self.check_death(enemy)
            return
        if finished:
            used = d["elapsed"] / d["limit"]
            if session.accuracy() >= DEFLECT_ACCURACY and used <= DEFLECT_TIME_FRACTION:
                reflect = d["damage"] * (1.0 if self.run.has("thimble") else REFLECT_FRACTION)
                if self.run.deflects + 1 >= 8:
                    self.game.achieve("thorn")
                enemy.take(reflect)
                self.run.deflects += 1
                self.floaters.append(FloatingText("Deflect!", (px + 30, py - 70), (150, 220, 255), 40))
                self.floaters.append(FloatingText(f"{reflect:.0f}", (enemy.center[0], enemy.center[1] - 30),
                                                  (150, 220, 255), 30))
                burst(self.particles, (px + 40, py - 10), (150, 220, 255), 25)
                self.game.sound.play("deflect")
                self.check_death(enemy)
            else:
                self.floaters.append(FloatingText("Dodge", (px + 30, py - 70), WHITE, 36))
                self.game.sound.play("dodge")
            return
        fraction = 0.5 if session.progress >= 0.5 else 1.0
        label = "Grazed" if fraction < 1 else "Hit"
        lost = self.run.hurt(d["damage"] * fraction)     # a blow is the one thing that can kill
        self.floaters.append(FloatingText(f"{label}!  -{lost:.0f} sanity", (px + 20, py - 60),
                                          MISS_COL, 34))
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
        self.floaters.append(FloatingText("Toll", (cx, cy - 50), (160, 255, 220), 30))
        self.game.sound.play("toll")
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
        self.game.sound.play("hex")
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
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if effect.alive]
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
                    self.game.game_over("madness")
                self.outcome_timer = 99.0     # the scene is over; do not ask twice
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

        # burnout cools, Mend mends
        for key in list(self.heat):
            self.heat[key] = max(0.0, self.heat[key] - dt / HEAT_FADE_TIME)
        for key in list(self.burnt):
            self.burnt[key] -= dt
            if self.burnt[key] <= 0:
                del self.burnt[key]
        if self.regen[1] > 0:
            self.regen[1] -= dt
            self.run.change_sanity(self.regen[0] * dt)

        if self.defense:
            self.defense["elapsed"] += dt
            if self.defense["elapsed"] >= self.defense["limit"]:
                self.resolve_defense(False)
        else:
            self.t += dt
            for e in self.alive():
                if e.trait == "stare":
                    self.run.change_sanity(-(0.3 if e.boss else 0.4) * dt)
                what = e.tick(dt, self.rng)
                if what == "feint":
                    # it rears up ... and holds back. The real blow comes soon.
                    cx, cy = e.center
                    self.floaters.append(FloatingText("Feint", (cx, cy - 70), (255, 200, 150), 26))
                    self.game.sound.play("warn")
                elif what == "attack":
                    allies = [o for o in self.alive() if o is not e]
                    if e.trait == "rally" and self.rng.random() < (0.6 if allies else 0.3):
                        self.toll(e, allies)
                    else:
                        self.defense_queue.append(e)
                if e.boss and not e.raged and e.hp < e.max_hp / 2:
                    e.raged = True
                    e.set_timer(min(e.timer, 2.0))
                    self.run.change_sanity(-6)
                    self.say(e.rage_text + "  (-6 sanity)", 3.0)
                    self.game.add_shake(0.6, 10)
                    self.game.sound.play("rage")
            self.defense_queue = [e for e in self.defense_queue if not e.dead]
            if self.defense_queue:
                self.start_defense(self.defense_queue.pop(0))

        if self.run.dead:
            # his mind breaks: a beat of stillness, then the death scene
            self.outcome = "madness"
            self.outcome_timer = 0.9
            self.clear_input()
            self.hurt_flash = 0.9
            burst(self.particles, self.player_center(), (200, 30, 40), 50,
                  speed=(40, 220), life=(0.6, 1.8))
            self.defense = None
            return
        if not self.alive() and not self.projectiles:
            self.outcome = "win"
            self.outcome_timer = 2.0     # long enough for the death sheet to play
            self.defense = None

    # --- drawing -----------------------------------------------------------------
    def hero_image(self):
        """The boy's picture: his look and eye follow his sanity, his pose the moment."""
        poses = art.hero_poses(self.hero, self.run.sanity, self.run.max_sanity)
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
        for effect in self.effects:
            effect.draw(surface)
        if self.session and not self.outcome:
            # the grimoire gathers light as the incantation nears its end
            charge = self.session.progress
            spark = ELEMENT_COLORS[self.run.get(self.locked).defn.element]
            g = art.glow(int(26 + 46 * charge), spark, int(110 + 140 * charge))
            surface.blit(g, g.get_rect(center=(px + 16, py + 4)))
            for k in range(3):
                angle = self.player_anim * 7 + k * math.tau / 3
                reach = 46 - 26 * charge
                pygame.draw.circle(surface, spark, (px + 16 + math.cos(angle) * reach,
                                                    py + 4 + math.sin(angle) * reach * 0.6), 3)
        img = self.hero_image()
        if self.cast_anim > 0:
            # a small hop as the spell leaves
            lift = int(math.sin((1 - self.cast_anim / 0.55) * math.pi) * 10)
        else:
            lift = 0
        if self.hurt_flash > 0:
            img = img.copy()
            img.fill((160, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(img, img.get_rect(midbottom=(PLAYER_X, STAGE_GROUND - lift)))
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
            for i, line in enumerate(ui.wrap(self.message, ui.font(24), 330)):
                ui.draw_text(surface, ui.font(24), line, BONE, topleft=(16, 92 + i * 17))
        if self.intro > 0:
            title = self.enemies[0].name if self.boss else "Shadows close in!"
            ui.panel(surface, (WIDTH // 2 - 260, 120, 520, 90), 210)
            ui.draw_text(surface, ui.font(52), title, BONE, center=(WIDTH // 2, 152))
            ui.draw_text(surface, ui.font(22), "Type an incantation to cast it",
                         GRAY, center=(WIDTH // 2, 192))
        if self.defense:
            self.draw_defense(surface)
        if self.outcome == "win":
            ui.draw_text(surface, ui.font(64), "The shadows fade.", BONE, center=(WIDTH // 2, 170))

    def draw_focus(self, surface):
        focus = self.run.focus
        ui.draw_text(surface, ui.font(20), "Focus", GOLD if focus else GRAY, topleft=(16, 66))
        for i in range(FOCUS_MAX):
            center = (66 + i * 14, 74)
            if i < focus:
                pygame.draw.circle(surface, GOLD, center, 5)
            else:
                pygame.draw.circle(surface, GRAY, center, 5, 1)
        if focus:
            ui.draw_text(surface, ui.font(20), f"+{focus * FOCUS_BONUS * 100:.0f}%", GOLD,
                         topleft=(142, 66))
        x = 190
        if self.empower:
            r = ui.draw_text(surface, ui.font(20), f"Pact: next spell +{self.empower * 100:.0f}%",
                             (190, 120, 255), topleft=(x, 66))
            x = r.right + 14
        if self.mirror:
            ui.draw_text(surface, ui.font(20), "Mirror raised", (200, 230, 255), topleft=(x, 66))

    def draw_defense(self, surface):
        d = self.defense
        session = d["session"]
        word = session.target
        cx, y0 = 660, 4
        edge = (255, 60, 200) if d["heavy"] else (200, 70, 70)
        ui.panel(surface, (cx - 280, y0, 560, 118), 240, border=edge,
                 border_width=3 if d["heavy"] else 1)
        if d["heavy"]:
            title = "Heavy blow!  " + d["enemy"].attack_text
        elif d["flurry"]:
            title = "Again!  " + d["enemy"].attack_text + "  Defend:"
        else:
            title = d["enemy"].attack_text + "  Defend:"
        title = ui.fit(title, ui.font(24), 540)
        ui.draw_text(surface, ui.font(24), title, (255, 150, 230) if d["heavy"] else (255, 140, 120),
                     center=(cx, y0 + 15))
        size = 34
        width = ui.incantation_width(word, size)
        ui.draw_incantation(surface, word, session.pos, (cx - width // 2, y0 + 32), size)
        left = 1 - d["elapsed"] / d["limit"]
        deflect_mark = 1 - DEFLECT_TIME_FRACTION
        bar = (cx - 240, y0 + 78, 480, 10)
        ui.draw_bar(surface, bar, left, (220, 80, 70) if left < deflect_mark else (240, 200, 100))
        mx = bar[0] + int(bar[2] * deflect_mark)
        pygame.draw.line(surface, WHITE, (mx, bar[1] - 4), (mx, bar[1] + 13), 2)
        ui.draw_text(surface, ui.font(18), "finish before the line to deflect", GRAY,
                     midleft=(bar[0], y0 + 104))

    def draw_grimoire(self, surface):
        run = self.run
        ui.panel(surface, (-4, PANEL_Y - 5, WIDTH + 8, HEIGHT - PANEL_Y + 9), 225, scale=0.16)
        tier = sanity_tier(run.sanity)
        jitter = [0, 0.8, 2.2][tier]
        col_w = WIDTH // 2
        small = ui.font(20)
        for i, owned in enumerate(run.grimoire):
            spell = owned.defn
            col, row = i // 4, i % 4
            x = 14 + col * col_w
            y = PANEL_Y + 6 + row * ROW_H
            key = owned.key
            typed = self.typed_count(key)
            burnt = self.burnt.get(key, 0)
            dim = burnt > 0 or (self.locked is not None and self.locked != key)
            if self.locked == key:
                pygame.draw.rect(surface, (60, 50, 30), (x - 6, y - 2, col_w - 16, ROW_H - 2),
                                 border_radius=4)
            # first line: name, heat, what it does, what it costs
            name_col = GRAY if dim else ELEMENT_COLORS[spell.element]
            label = f"{spell.name}  Lv{owned.level}"
            if key in self.hexed:
                label += "  (hexed)"
            name_rect = ui.draw_text(surface, small, label, name_col, topleft=(x, y))
            heat = self.heat.get(key, 0.0)
            for k in range(BURNOUT_CASTS):             # heat pips: full = burnout
                pip = (name_rect.right + 10 + k * 9, y + 5, 6, 6)
                if burnt > 0 or heat > k + 0.01:
                    pygame.draw.rect(surface, (255, 120, 40), pip)
                pygame.draw.rect(surface, (120, 100, 90), pip, 1)
            info = effect_text(spell.kind, owned.strength())
            ui.draw_text(surface, small, info, GRAY, topright=(x + col_w - 96, y))
            cant_pay = self.cost(spell) > run.sanity - 1     # red: it will come out weak
            ui.draw_text(surface, small, cost_text(self.cost(spell)),
                         MISS_COL if cant_pay else SANITY_COL,
                         topright=(x + col_w - 22, y))
            # second line: the incantation to type, drawn large
            if burnt > 0:
                ui.draw_text(surface, ui.font(30), f"Burnt out  {burnt:.0f}s", (255, 120, 40),
                             topleft=(x, y + 13))
                bar = (x + 200, y + 26, 200, 6)
                ui.draw_bar(surface, bar, burnt / BURNOUT_TIME, (255, 120, 40))
            else:
                ui.draw_incantation(surface, self.texts[key], typed, (x, y + 13), 30,
                                    jitter=0 if dim else jitter,
                                    color=(104, 100, 112) if dim else WHITE,
                                    rng=self.jitter_rng, max_width=col_w - 30)
        # footer: hints and live typing stats
        foot_y = HEIGHT - 12
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
        if self.miss_flash > 0:
            pygame.draw.rect(surface, MISS_COL, (0, PANEL_Y, WIDTH, HEIGHT - PANEL_Y), 3)
