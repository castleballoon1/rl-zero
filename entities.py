"""Things that live in the world: the boy, the creatures, effects."""
import math
import random

import pygame

import art
import sprites
import ui
from bestiary import TRAITS, RAGE_STYLE_BONUS
from settings import (WIDTH, GROUND_Y, GRAVITY, JUMP_SPEED, MOVE_SPEED,
                      PLAYER_FRAME_TIME, RAGE_SPEED, HEAVY_SHOWS_AT, QUICK_FRACTION,
                      PACE_WOBBLE, FEINT_PAUSE, FEINT_RECOVER, FLURRY_GAP)

Vector2 = pygame.math.Vector2
HURT_TIME = 0.3          # how long the hurt row plays after a hit
LUNGE_TIME = 0.4         # how long the attack row plays when a blow lands


class Layer:
    """One parallax layer. Far layers move less than near ones (depth)."""

    def __init__(self, image, factor):
        self.image = image
        self.factor = factor

    def draw(self, surface, camera_x):
        x = -((camera_x * self.factor) % WIDTH)
        surface.blit(self.image, (round(x), 0))
        surface.blit(self.image, (round(x) + WIDTH, 0))


# --- Exploration -------------------------------------------------------------
class Player(pygame.sprite.Sprite):
    """The lost boy. pos is the middle of his feet."""
    TALL = 84

    def __init__(self, x):
        super().__init__()
        self.hero = art.hero_frames(self.TALL)
        self.walk_index = 0
        self.anim_time = 0.0
        self.image = art.hero_poses(self.hero, 100)["idle"]
        self.pos = Vector2(x, GROUND_Y)
        self.vel = Vector2(0, 0)
        self.on_ground = True
        self.facing = 1
        self.drop_timer = 0.0
        self.invulnerable = 0.0
        self.knock = 0.0
        self.rect = self.image.get_rect(midbottom=(round(x), GROUND_Y))
        self.hitbox = pygame.Rect(0, 0, 26, self.TALL - 12)
        self.hitbox.midbottom = self.rect.midbottom

    def jump(self):
        if self.on_ground:
            self.vel.y = -JUMP_SPEED
            self.on_ground = False

    def hurt(self, direction):
        """Knocked back by thorns; safe for a moment afterwards."""
        self.invulnerable = 1.2
        self.knock = direction * 420.0
        self.vel.y = -380
        self.on_ground = False

    def visible(self):
        """Blink while invulnerable."""
        if self.invulnerable <= 0:
            return True
        return int(self.invulnerable * 10) % 2 == 0

    def drop(self):
        """Fall through a one-way platform."""
        if self.on_ground and self.pos.y < GROUND_Y:
            self.drop_timer = 0.25
            self.on_ground = False

    def update(self, dt, keys, platforms, length, sanity=100, max_sanity=100):
        move = 0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move += 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move -= 1
        self.vel.x = move * MOVE_SPEED + self.knock
        self.knock *= math.exp(-8 * dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        if move:
            self.facing = move
        self.vel.y += GRAVITY * dt
        self.drop_timer = max(0.0, self.drop_timer - dt)

        prev_bottom = self.pos.y
        self.pos.x = max(16, min(length - 16, self.pos.x + self.vel.x * dt))
        self.pos.y += self.vel.y * dt
        self.on_ground = False
        if self.pos.y >= GROUND_Y:
            self.pos.y = GROUND_Y
            self.vel.y = 0
            self.on_ground = True
        elif self.vel.y > 0 and self.drop_timer <= 0:
            # one-way platforms: only land when coming down from above
            for p in platforms:
                if (p.left - 6 < self.pos.x < p.right + 6
                        and prev_bottom <= p.top <= self.pos.y):
                    self.pos.y = p.top
                    self.vel.y = 0
                    self.on_ground = True
                    break

        # pick the picture: his look follows his sanity, his pose what he is doing
        poses = art.hero_poses(self.hero, sanity, max_sanity,
                               "right" if self.facing > 0 else "left")
        if not self.on_ground:
            self.image = poses["jump"]
        elif move:
            self.anim_time += dt
            if self.anim_time >= PLAYER_FRAME_TIME:
                self.anim_time -= PLAYER_FRAME_TIME
                self.walk_index = (self.walk_index + 1) % len(poses["walk"])
            self.image = poses["walk"][self.walk_index % len(poses["walk"])]
        else:
            self.anim_time = 0.0
            self.walk_index = 0
            self.image = poses["idle"]
        self.rect = self.image.get_rect(midbottom=(round(self.pos.x), round(self.pos.y)))
        self.hitbox.midbottom = self.rect.midbottom


class MapEnemy(pygame.sprite.Sprite):
    """A creature pacing the path. Walk into it and the fight begins."""
    TALL = 110

    def __init__(self, index, x, kinds):
        super().__init__()
        self.index = index
        self.kinds = kinds
        lead = kinds[0]
        self.left = art.creature_frames(lead, self.TALL)["idle"]   # the art faces left
        self.right = sprites.flip_frames(self.left)
        self.feet_y = GROUND_Y - round(art.creature_hover(lead, self.TALL))
        self.home = x
        self.x = float(x)
        self.dir = random.choice((-1, 1))
        self.speed = random.uniform(25, 45)
        self.anim = random.random()
        self.place()

    def place(self):
        frames = self.right if self.dir > 0 else self.left
        self.image = frames[int(self.anim / 0.18) % len(frames)]
        feet = (round(self.x), self.feet_y)
        self.rect = self.image.get_rect(midbottom=feet)
        self.body = sprites.body_rect(self.image, feet)   # only the painted pixels

    def update(self, dt):
        self.x += self.dir * self.speed * dt
        if abs(self.x - self.home) > 70:
            self.dir *= -1
            self.x = self.home + 70 * (1 if self.x > self.home else -1)
        self.anim += dt
        self.place()


# --- Effects -----------------------------------------------------------------
class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color, speed=(60, 260), life=(0.3, 0.8), size=4):
        super().__init__()
        s = random.uniform(*speed)
        self.vel = Vector2(s, 0).rotate(random.uniform(0, 360))
        self.pos = Vector2(pos)
        self.life = random.uniform(*life)
        self.age = 0.0
        self.color = color
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.age += dt
        if self.age >= self.life:
            self.kill()
            return
        self.pos += self.vel * dt
        self.vel *= math.exp(-3 * dt)
        t = self.age / self.life
        r, g, b = self.color
        self.image.fill((r, g, b, int(255 * (1 - t))))
        self.rect.center = (round(self.pos.x), round(self.pos.y))


def burst(group, pos, color, count, **kw):
    for _ in range(count):
        group.add(Particle(pos, color, **kw))


class FloatingText:
    """Numbers and words that rise and fade (damage, CRIT!, DODGE ...)."""

    def __init__(self, text, pos, color, size=28, life=1.1, rise=50):
        self.image = ui.font(size).outlined(text, color)
        self.pos = Vector2(pos)
        self.life = life
        self.age = 0.0
        self.rise = rise

    @property
    def alive(self):
        return self.age < self.life

    def update(self, dt):
        self.age += dt
        self.pos.y -= self.rise * dt

    def draw(self, surface):
        t = self.age / self.life
        img = self.image.copy()
        img.set_alpha(int(255 * (1 - t * t)))
        surface.blit(img, img.get_rect(center=(round(self.pos.x), round(self.pos.y))))


class Projectile:
    """A homing bolt of magic. Calls on_hit(target) when it arrives."""

    def __init__(self, start, target, color, on_hit, speed=900, size=8, delay=0.0):
        self.pos = Vector2(start)
        self.target = target
        self.color = color
        self.on_hit = on_hit
        self.speed = speed
        self.size = size
        self.delay = delay
        self.trail = []
        self.done = False

    def update(self, dt):
        if self.delay > 0:
            self.delay -= dt
            return
        goal = Vector2(self.target.center)
        to_goal = goal - self.pos
        step = self.speed * dt
        self.trail.append(Vector2(self.pos))
        self.trail = self.trail[-8:]
        if to_goal.length() <= step:
            self.done = True
            self.on_hit(self.target)
        else:
            to_goal.scale_to_length(step)
            self.pos += to_goal

    def draw(self, surface):
        if self.delay > 0:
            return
        for i, p in enumerate(self.trail):
            r = max(1, int(self.size * (i + 1) / len(self.trail) * 0.7))
            pygame.draw.circle(surface, self.color, (round(p.x), round(p.y)), r)
        g = art.glow(self.size * 3, self.color, 200)
        surface.blit(g, g.get_rect(center=(round(self.pos.x), round(self.pos.y))))
        pygame.draw.circle(surface, (255, 255, 255), (round(self.pos.x), round(self.pos.y)),
                           max(2, self.size // 2))


class Ring:
    """An expanding ring of light: the flash where a spell lands."""

    def __init__(self, center, color, radius=60, life=0.35, width=4):
        self.center = center
        self.color = color
        self.radius = radius
        self.life = life
        self.width = width
        self.age = 0.0

    @property
    def alive(self):
        return self.age < self.life

    def update(self, dt):
        self.age += dt

    def draw(self, surface):
        t = self.age / self.life
        r = max(2, int(self.radius * (0.2 + 0.8 * t)))
        surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, int(255 * (1 - t))), (r + 2, r + 2), r, self.width)
        surface.blit(surf, surf.get_rect(center=self.center))


class RuneCircle:
    """The casting circle: it snaps open at the boy's feet, its runes turn,
    a pillar of light rises through him, and it fades as the spell flies."""
    LIFE = 0.8

    def __init__(self, feet, color, radius=66):
        self.feet = feet
        self.color = color
        self.radius = radius
        self.age = 0.0

    @property
    def alive(self):
        return self.age < self.LIFE

    def update(self, dt):
        self.age += dt

    def draw(self, surface):
        t = self.age / self.LIFE
        grow = min(1.0, t / 0.18)                       # opens fast ...
        fade = 1 - max(0.0, (t - 0.45) / 0.55)          # ... and fades slowly
        alpha = int(255 * fade)
        r = self.radius * grow
        # the circle lies on the ground, so it is drawn as a flat oval
        w, h = int(r * 2) + 8, int(r * 0.62) + 8
        ring = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (*self.color, alpha // 4), (2, 2, w - 4, h - 4))
        pygame.draw.ellipse(ring, (*self.color, alpha), (2, 2, w - 4, h - 4), 3)
        inner = (w * 0.18, h * 0.18, w * 0.64, h * 0.64)
        pygame.draw.ellipse(ring, (255, 255, 255, alpha), inner, 2)
        for k in range(8):                              # eight runes circling
            angle = k / 8 * math.tau + self.age * 4
            x = w / 2 + math.cos(angle) * (w / 2 - 12)
            y = h / 2 + math.sin(angle) * (h / 2 - 7)
            pygame.draw.rect(ring, (255, 255, 255, alpha), (x - 2, y - 2, 5, 5))
        surface.blit(ring, ring.get_rect(center=self.feet))
        # the pillar of light
        tall = int(170 * grow)
        if tall > 4:
            pillar = pygame.Surface((int(r * 1.2) + 2, tall), pygame.SRCALPHA)
            pw = pillar.get_width()
            for k in range(4):
                inset = k * pw // 9
                pygame.draw.rect(pillar, (*self.color, int(46 * fade)),
                                 (inset, 0, pw - 2 * inset, tall))
            surface.blit(pillar, pillar.get_rect(midbottom=self.feet))


# --- Combat ------------------------------------------------------------------
class CombatEnemy:
    """One creature in a fight. `feet` is where it stands; `tall` its height in pixels."""

    def __init__(self, data, feet_x, ground_y, tall, rng):
        self.name = data["name"]
        self.kind = data["kind"]
        self.max_hp = data["hp"]
        self.hp = float(data["hp"])
        self.dmg = data["dmg"]
        self.base_dmg = data["dmg"]   # before any Withering Word
        self.interval = data["interval"]
        self.boss = data["boss"]
        self.rage_text = data.get("rage", "")
        self.trait = data.get("trait", "")
        self.attack_text = data.get("attack_text", f"The {self.name} attacks!")
        self.raged = False
        # habits that keep it from keeping a steady beat (see STYLES in bestiary.py)
        self.style = data.get("style", dict(quick=0.0, feint=0.0, flurry=0.0,
                                            heavy=0.3, wobble=0.0))
        self.cooldown = data.get("cooldown", 1.0)
        self.rng = rng
        self.pace_phase = rng.uniform(0, math.tau)
        self.pace_freq = rng.uniform(0.6, 1.5)
        self.heavy_next = rng.random() < self.style["heavy"]
        self.feinting = 0.0       # seconds left rearing up in a feint
        self.feinted = False      # it just feinted, so the next fill is real
        self.chain = 0            # 1 while a flurry's second blow is coming
        self.art = art.creature_frames(data["art"], tall)
        self.feet = (round(feet_x), round(ground_y - art.creature_hover(data["art"], tall)))
        # the painted pixels of the idle pose: used for bars, targets and hit sparks
        self.body = sprites.body_rect(self.art["idle"][0], self.feet)
        # first attack comes a little later so the player can get ready
        self.timer = rng.uniform(*self.interval) + 1.5 * self.cooldown
        self.timer_max = self.timer
        self.anim = rng.random()
        self.flash = 0.0          # time left on the hurt row
        self.lunge = 0.0          # time left on the attack row
        self.windup = False       # rearing up while the player types a DEFEND word
        self.attacks = 0          # how many times it has attacked
        self.dead = False
        self.death_time = 0.0
        self.dots = []            # [damage_per_tick, ticks_left, time_to_next_tick]

    @property
    def rect(self):
        return self.body

    @property
    def center(self):
        return self.body.center

    def take(self, amount):
        dealt = min(self.hp, amount)
        self.hp -= amount
        self.flash = HURT_TIME
        return dealt

    def chance(self, habit):
        """How likely this creature is to do something (quick, feint, flurry ...)."""
        extra = RAGE_STYLE_BONUS.get(habit, 0.0) if self.raged else 0.0
        return self.style.get(habit, 0.0) + extra

    def next_is_heavy(self):
        return self.heavy_next

    def shows_heavy(self):
        """The magenta warning only shows once the bar is well along."""
        return self.heavy_next and self.bar_fraction() >= HEAVY_SHOWS_AT

    def bar_fraction(self):
        if self.feinting > 0:
            return 1.0
        return 1 - self.timer / max(0.01, self.timer_max)

    def pace(self):
        """How fast its attack bar fills right now: it speeds up and slows down."""
        wobble = PACE_WOBBLE * self.style.get("wobble", 0.0)
        return 1 + wobble * math.sin(self.anim * self.pace_freq + self.pace_phase)

    def strike(self):
        self.windup = False
        self.lunge = LUNGE_TIME

    def set_timer(self, seconds):
        self.timer = seconds
        self.timer_max = seconds

    def reset_timer(self, rng):
        """Wait for the next attack: a random time, sometimes cut short."""
        scale = 1 / RAGE_SPEED if self.raged else 1.0
        wait = rng.uniform(*self.interval) * scale
        if rng.random() < self.chance("quick"):
            wait *= rng.uniform(*QUICK_FRACTION)          # a quick strike
        self.set_timer(wait)
        self.heavy_next = rng.random() < self.chance("heavy")

    def tick(self, dt, rng):
        """Run its attack clock. Returns 'attack', 'feint' or None."""
        if self.feinting > 0:
            self.feinting -= dt
            if self.feinting <= 0:
                # it holds back ... and comes again soon after
                self.windup = False
                self.set_timer(rng.uniform(*FEINT_RECOVER) * self.cooldown)
            return None
        self.timer -= dt * self.pace()
        if self.timer > 0:
            return None
        if not self.feinted and self.chain == 0 and rng.random() < self.chance("feint"):
            self.feinted = True
            self.feinting = FEINT_PAUSE
            self.windup = True
            return "feint"
        self.feinted = False
        self.reset_timer(rng)
        return "attack"

    def after_blow(self, rng):
        """Called when one of its blows is over. Returns True if a flurry follows."""
        if self.dead or self.chain:
            self.chain = 0
            return False
        if rng.random() < self.chance("flurry"):
            self.chain = 1
            self.set_timer(rng.uniform(*FLURRY_GAP) * self.cooldown)
            self.heavy_next = False
            return True
        return False

    def update(self, dt):
        """Returns the rot damage dealt this frame (0 most frames)."""
        self.anim += dt
        self.flash = max(0.0, self.flash - dt)
        self.lunge = max(0.0, self.lunge - dt)
        if self.dead:
            self.death_time += dt
            return 0.0
        damage = 0.0
        for dot in self.dots:
            dot[2] -= dt
            if dot[2] <= 0 and dot[1] > 0:
                dot[1] -= 1
                dot[2] += 1.0
                damage += dot[0]
        self.dots = [d for d in self.dots if d[1] > 0]
        return damage

    def picture(self):
        """Which frame to show: death, attack, hurt or idle (like pick_enemy_image)."""
        rows = self.art
        if self.dead:
            if rows["death"]:
                index = int(self.death_time / art.DEATH_FRAME_TIME)
                return rows["death"][min(len(rows["death"]) - 1, index)]
            faded = rows["idle"][0].copy()
            faded.set_alpha(max(0, int(255 * (1 - self.death_time))))
            return faded

        def played(frames, left, total):
            return frames[min(len(frames) - 1, int((total - left) / total * len(frames)))]

        if self.lunge > 0:
            return played(rows["attack"], self.lunge, LUNGE_TIME)
        if self.windup:
            return rows["attack"][min(1, len(rows["attack"]) - 1)]
        if self.flash > 0:
            return played(rows["hurt"], self.flash, HURT_TIME)
        return rows["idle"][int(self.anim / 0.18) % len(rows["idle"])]

    def draw(self, surface, targeted):
        img = self.picture()
        rect = img.get_rect(midbottom=self.feet)
        if self.lunge > 0:
            rect.x -= int(math.sin(self.lunge / LUNGE_TIME * math.pi) * 40)
        if self.dots and not self.dead:
            g = art.glow(self.body.width // 2 + 10, (110, 200, 70), 70)
            surface.blit(g, g.get_rect(center=self.body.center))
        surface.blit(img, rect)
        if self.dead:
            return
        # name, health and attack timer above the head
        body = self.body
        top = body.top - 44
        col = (255, 220, 120) if targeted else (235, 230, 220)
        w = max(90, min(132, body.width))
        plate_w = max(w, ui.font(22).size(self.name)[0]) + 14
        plate = pygame.Rect(body.centerx - plate_w // 2, top - 21, plate_w, 62)
        ui.panel(surface, plate, 150, border=(40, 34, 54))
        ui.draw_text(surface, ui.font(22), self.name, col, midbottom=(body.centerx, top))
        ui.draw_bar(surface, (body.centerx - w // 2, top + 2, w, 8),
                    self.hp / self.max_hp, (200, 50, 60))
        frac = self.bar_fraction()
        warn = (255, 120, 60) if frac > 0.8 else (200, 170, 90)
        if self.shows_heavy():
            warn = (255, 60, 200)      # a magenta bar warns that a HEAVY blow is coming
        ui.draw_bar(surface, (body.centerx - w // 2, top + 13, w, 4), frac, warn)
        if self.trait:
            ui.draw_text(surface, ui.font(16), TRAITS[self.trait][0], (200, 160, 240),
                         midtop=(body.centerx, top + 21))
        if targeted:
            bob = math.sin(self.anim * 6) * 4
            x, y = body.centerx, top - 26 + bob
            pygame.draw.polygon(surface, (255, 220, 120),
                                [(x - 8, y - 10), (x + 8, y - 10), (x, y)])
