"""The opening: the boy wakes in the woods and finds the grimoire.

A short scripted scene played at the start of every run (Esc skips it).
It is a list of beats; each beat lasts a set time and shows one caption,
typed out letter by letter. One beat waits for the player: the grimoire's
first word, 'ignis', must be typed to drive off a shadow, which teaches
the game's one rule before the woods begin.
"""
import math
import random

import pygame

import art
import ui
from entities import Projectile, Ring, RuneCircle, burst
from settings import WIDTH, HEIGHT, GROUND_Y, GRAY, BONE, GOLD, ELEMENT_COLORS, MISS_COL
from words import LETTERS

HERO_TALL = 120
WAKE_X = 300           # where his feet are as he lies, and where he stands up

# Getting up comes in two parts.
# 1. He sits up: the picture is cut at the waist; his legs stay flat on the
#    ground while his body turns up about the hips. (seconds, body tilt)
#    Tilt 90 is lying flat with his head to the left, 0 is upright, below 0
#    leans forward.
SIT_KEYS = [(0.0, 90), (0.45, 83), (1.15, -8), (1.45, -4)]
# 2. He gets his feet under him and stands: the whole picture, crouched
#    (squashed down towards his feet) and tilted. (seconds, tilt, crouch, pose)
STAND_KEYS = [(1.45, -16, 0.70, "stride"), (1.80, -12, 0.73, "stride"),
              (2.25, 4, 1.03, "idle"), (2.70, 0, 1.00, "idle")]
WAIST = 0.66           # where the picture is cut: this share of his height from the top
SIT_X = WAKE_X - 34    # where his hips rest while he lies and sits


def _ease(keys, t):
    """Values between two keys, eased in and out."""
    for k0, k1 in zip(keys, keys[1:]):
        if t <= k1[0]:
            k = (t - k0[0]) / (k1[0] - k0[0])
            k = k * k * (3 - 2 * k)
            return tuple(a + (b - a) * k if isinstance(a, (int, float)) else a
                         for a, b in zip(k0[1:], k1[1:]))
    return keys[-1][1:]


def rise_pose(t):
    """('sit', body tilt) or ('stand', tilt, crouch, pose) at t seconds into getting up."""
    if t < SIT_KEYS[-1][0]:
        return ("sit",) + _ease(SIT_KEYS, t)
    return ("stand",) + _ease(STAND_KEYS, t)


def placed_center(size, pivot, angle, screen_pivot):
    """Where to put the centre of a picture turned `angle` degrees (as pygame turns
    it, about its centre) so that `pivot` (a point in the picture) lands on
    `screen_pivot`."""
    a = math.radians(angle)
    vx, vy = pivot[0] - size[0] / 2, pivot[1] - size[1] / 2
    rx = vx * math.cos(a) + vy * math.sin(a)
    ry = -vx * math.sin(a) + vy * math.cos(a)
    return screen_pivot[0] - rx, screen_pivot[1] - ry

BOOK_X = 600           # where the grimoire glows in the roots
SHADOW_STOP = 800      # how close the shadow creeps
FIRST_WORD = "ignis"

# He walks at one steady pace the whole scene, to the book and off the screen,
# with one step rhythm, whether or not he is carrying the grimoire.
WALK_SPEED = 115       # px / s
WALK_FRAME = 0.16      # seconds per walking picture (stride, stand, stride, stand)
WALK_TO = BOOK_X - 70  # where he stops to pick up the book
WALK_OFF = WIDTH + 60  # where he is gone off the right edge

# (beat, seconds, caption). A beat of None seconds waits for the player.
BEATS = [
    ("dark", 1.8, "..."),
    ("wake", 2.6, "Cold earth. Wet leaves. He does not remember lying down."),
    ("rise", 2.7, "He gets up, slowly. Nothing here is familiar."),
    ("look", 2.2, "The woods are very quiet."),
    ("glow", 1.8, "Something glows under the roots."),
    ("walk", (WALK_TO - WAKE_X) / WALK_SPEED, ""),
    ("lift", 2.2, "A book. It is warm, though nothing else here is."),
    ("take", 1.4, "It opens on its own, as if it had been waiting for him."),
    ("shadow", 2.0, "Then something moves between the trees."),
    ("type", None, "One word is already written. Read it aloud: type it."),
    ("after", 2.8, "The shadow shrieks and is gone. The grimoire hums in his hands."),
    ("go", (WALK_OFF - WALK_TO) / WALK_SPEED, "Somewhere ahead, the trees part. He walks."),
]


class _Spot:
    def __init__(self, center):
        self.center = center


class IntroScene:
    music = "woods"
    pausable = False
    show_sanity_fx = False

    def __init__(self, game):
        self.game = game
        self.scene = art.forest_scene()
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((4, 2, 12, 140))
        self.hero = art.hero_frames(HERO_TALL)
        self.bare = art.hero_bookless(HERO_TALL)    # before he finds the grimoire
        self.opening_frames = art.opening_boy_frames(HERO_TALL)
        self.turned = {}                            # rotated pictures while he gets up
        self.rise_sounds = set()
        self.beat = 0
        self.beat_time = 0.0
        self.time = 0.0
        self.x = float(WAKE_X)
        self.facing = "right"
        self.walk_anim = 0.0
        self.last_step = -1
        self.book_x = float(BOOK_X)
        self.book_y = GROUND_Y - 14
        self.book_open = 0.0
        self.book_size = 24
        self.has_book = False
        self.typed = 0
        self.miss = 0.0
        self.shadow_x = WIDTH + 120.0
        self.shadow_gone = 0.0           # seconds since the bolt struck it
        self.cast_anim = 0.0
        self.effects = []
        self.particles = pygame.sprite.Group()
        self.bolt = None
        self.done = False
        self.rng = random.Random(4)
        frames = art.creature_frames("moth", 150)["idle"]
        self.shadow_frames = []
        for frame in frames:                     # a dark shape, not yet a creature
            dark = frame.copy()
            dark.fill((50, 34, 70), special_flags=pygame.BLEND_RGB_MULT)
            self.shadow_frames.append(dark)
        self.shadow_hover = art.creature_hover("moth", 150)

    # --- the script ------------------------------------------------------------------
    @property
    def name(self):
        return BEATS[min(self.beat, len(BEATS) - 1)][0]   # holds the last beat while fading out

    def next_beat(self):
        self.beat += 1
        self.beat_time = 0.0
        if self.beat >= len(BEATS):
            self.finish()
            return
        if self.name == "glow":
            self.game.sound.play("shrine")
        elif self.name == "lift":
            self.game.sound.play("page")
        elif self.name == "take":
            self.has_book = True
            self.game.sound.play("unlock")
            burst(self.particles, self.hand(), (255, 210, 140), 30, speed=(40, 200))
            self.effects.append(Ring(self.hand(), (255, 210, 140), radius=80, life=0.6))
        elif self.name == "shadow":
            self.game.sound.play("warn")

    def finish(self):
        if not self.done:
            self.done = True
            self.game.enter_woods()

    def hand(self):
        """Where he holds the book."""
        return (round(self.x) + 18, GROUND_Y - 52)

    # --- input -----------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.done:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.sound.play("select")
            self.finish()
            return
        if self.name != "type" or self.typed >= len(FIRST_WORD):
            return
        ch = event.unicode.lower() if event.unicode else ""
        if len(ch) != 1 or ch not in LETTERS:
            return
        if ch == FIRST_WORD[self.typed]:
            self.typed += 1
            self.game.sound.play_key(self.typed / len(FIRST_WORD))
            if self.typed == len(FIRST_WORD):
                self.cast()
        else:
            self.miss = 0.2
            self.game.sound.play("miss")

    def cast(self):
        self.cast_anim = 0.55
        color = ELEMENT_COLORS["fire"]
        self.effects.append(RuneCircle((round(self.x), GROUND_Y - 3), color))
        self.game.sound.play_cast("fire")
        burst(self.particles, self.hand(), color, 18, speed=(40, 180))
        target = _Spot((round(self.shadow_x), GROUND_Y - 110))
        self.bolt = Projectile(self.hand(), target, color, self.bolt_lands, size=12, delay=0.16)

    def bolt_lands(self, spot):
        self.shadow_gone = 0.001
        self.effects.append(Ring(spot.center, (255, 170, 80), radius=120, life=0.5, width=5))
        burst(self.particles, spot.center, (255, 150, 70), 40, speed=(60, 320))
        burst(self.particles, spot.center, (40, 20, 50), 30, speed=(60, 260))
        self.game.sound.play("hit")
        self.game.sound.play("enemy_die")
        self.game.add_shake(0.3, 7)

    # --- update ----------------------------------------------------------------------
    def update(self, dt):
        if self.done:
            return
        self.time += dt
        self.beat_time += dt
        self.miss = max(0.0, self.miss - dt)
        self.cast_anim = max(0.0, self.cast_anim - dt)
        self.particles.update(dt)
        for effect in self.effects:
            effect.update(dt)
        self.effects = [e for e in self.effects if e.alive]
        if self.bolt:
            self.bolt.update(dt)
            if self.bolt.done:
                self.bolt = None
        name = self.name
        t = self.beat_time
        if name == "rise":
            # shuffling leaves as he pushes up, a scuff as he gets his feet under him
            for at, sound, dust in ((0.5, "step", 6), (1.15, "land", 14), (1.9, "step", 10)):
                if t >= at and at not in self.rise_sounds:
                    self.rise_sounds.add(at)
                    self.game.sound.play(sound)
                    burst(self.particles, (WAKE_X - 10, GROUND_Y - 4), (90, 80, 70), dust,
                          speed=(20, 90), life=(0.3, 0.8), size=3)
        if name == "look":
            self.facing = "left" if 0.5 < t < 1.3 else "right"
        elif name in ("walk", "go"):
            start, end = (WAKE_X, WALK_TO) if name == "walk" else (WALK_TO, WALK_OFF)
            self.x = min(float(end), start + WALK_SPEED * t)
            self.walk_anim += dt
            step = int(self.walk_anim / WALK_FRAME)
            if step != self.last_step and step % 2 == 0:      # a foot comes down
                self.game.sound.play("step")
            self.last_step = step
        elif name == "lift":
            # it rises out of the roots, opening, then drifts into his hands
            k = min(1.0, t / 1.3)
            self.book_y = GROUND_Y - 14 - 70 * (1 - (1 - k) ** 2)
            self.book_open = k
            drift = max(0.0, min(1.0, (t - 1.4) / 0.8))
            drift = drift * drift * (3 - 2 * drift)
            hx, hy = self.hand()
            self.book_x = BOOK_X + (hx - BOOK_X) * drift
            self.book_y += (hy - self.book_y) * drift
            self.book_open = k * (1 - drift)          # it closes as he takes it
            self.book_size = 24 - 10 * drift
            if self.rng.random() < 0.3:
                burst(self.particles, (BOOK_X, self.book_y), (255, 230, 170), 1,
                      speed=(20, 60), life=(0.5, 1.2), size=3)
        if name in ("shadow", "type"):
            # it creeps closer, then waits at the edge of the light
            self.shadow_x = max(SHADOW_STOP, self.shadow_x - 160 * dt)
        if self.shadow_gone:
            self.shadow_gone += dt
            self.shadow_x += 260 * dt
        if self.beat >= len(BEATS):
            return
        duration = BEATS[self.beat][1]
        if duration is None:
            # the waiting beat ends a little after the bolt strikes
            if self.shadow_gone > 0.9:
                self.next_beat()
        elif t >= duration:
            self.next_beat()

    # --- drawing ---------------------------------------------------------------------
    def eyelids(self):
        """How open his eyes are (0 shut, 1 open): they open, droop, then open."""
        if self.name == "dark":
            return 0.0
        if self.name != "wake":
            return 1.0
        t = self.beat_time
        if t < 0.7:
            return t / 0.7 * 0.6
        if t < 1.1:
            return 0.6 - (t - 0.7) / 0.4 * 0.45
        return min(1.0, 0.15 + (t - 1.1) / 0.8 * 0.85)

    def poses(self):
        """His pictures: without the book until he has taken it."""
        if self.has_book:
            return art.hero_poses(self.hero, 100, 100, self.facing)
        return self.bare[self.facing]

    def rise_now(self):
        """How he lies or rises at this moment, or None once he is standing."""
        name = self.name
        if name in ("dark", "wake"):
            return ("sit", 90.0)
        if name == "rise":
            return rise_pose(self.beat_time)
        return None

    def boy_parts(self):
        """[(picture, centre)] to draw for the boy, back to front."""
        if self.has_book:
            poses = art.hero_poses(self.hero, 100, 100, self.facing)
            name = self.name
            if name in ("walk", "go"):
                img = poses["walk"][self.walk_step() % len(poses["walk"])]
            elif self.cast_anim > 0:
                img = poses["cast"]
            else:
                img = poses["idle"]       # he stands just as he stood before he took it
            lift = int(math.sin((1 - self.cast_anim / 0.55) * math.pi) * 10) if self.cast_anim else 0
            return [(img, img.get_rect(midbottom=(round(self.x), GROUND_Y - lift)).center)]

        if self.opening_frames:
            name = self.name
            t = self.beat_time
            if name in ("dark", "wake"):
                index = 0 if t < 1.1 else 1
            elif name == "rise":
                index = min(5, 1 + int(t / 2.7 * 5))
            elif name == "walk" or name == "go":
                index = (7, 6, 8, 6)[self.walk_step() % 4]     # the same rhythm as with the book
            elif name == "look" and self.facing == "left":
                index = 6
            elif name in ("take", "cast"):
                index = 5
            else:
                index = 6
            img = self.opening_frames[index]
            if name == "look" and self.facing == "left":
                img = pygame.transform.flip(img, True, False)
            lift = int(math.sin((1 - self.cast_anim / 0.55) * math.pi) * 10) if self.cast_anim else 0
            return [(img, img.get_rect(midbottom=(round(self.x), GROUND_Y - lift)).center)]

        poses = self.poses()
        state = self.rise_now()
        if state and state[0] == "sit":
            return self.sitting(poses["idle"], state[1])
        if state:
            _, tilt, crouch, pose = state
            base = poses["walk"][0] if pose == "stride" else poses["idle"]
            return [self.crouched(base, pose, tilt, crouch)]
        name = self.name
        if name == "walk":
            img = poses["walk"][self.walk_step() % len(poses["walk"])]
        elif self.cast_anim > 0 or name == "take":
            img = poses["cast"]
        else:
            img = poses["idle"]
        lift = int(math.sin((1 - self.cast_anim / 0.55) * math.pi) * 10) if self.cast_anim else 0
        return [(img, img.get_rect(midbottom=(round(self.x), GROUND_Y - lift)).center)]

    def walk_step(self):
        """Which walking picture: one every WALK_FRAME seconds of walking."""
        return int(self.walk_anim / WALK_FRAME)

    def split(self, img):
        """Cut a standing picture at the waist: (body, legs, hip point in each, thicknesses)."""
        key = ("split", id(img))
        if key not in self.turned:
            w, h = img.get_size()
            box = img.get_bounding_rect()
            cut = box.top + round(box.height * WAIST)
            body = img.subsurface((0, 0, w, cut)).copy()
            legs = img.subsurface((0, cut, w, h - cut)).copy()
            legs_box = legs.get_bounding_rect()
            hip_x = legs_box.centerx
            self.turned[key] = dict(body=body, legs=legs, body_pivot=(hip_x, cut),
                                    legs_pivot=(hip_x, 0), legs_thick=legs_box.width,
                                    body_thick=box.width)
        return self.turned[key]

    def rotated(self, img, angle, tag):
        angle = round(angle / 2) * 2
        key = ("turn", id(img), angle, tag)
        if key not in self.turned:
            self.turned[key] = pygame.transform.rotozoom(img, angle, 1.0) if angle else img
        return self.turned[key]

    def sitting(self, img, tilt):
        """Lying flat (tilt 90) to sitting up (tilt 0): legs flat on the ground,
        the body turning up about the hips."""
        parts = self.split(img)
        a = math.radians(tilt)
        # lying, his side rests on the ground; sitting, he sits on his legs
        hip_y = GROUND_Y - max(parts["legs_thick"] / 2, parts["body_thick"] / 2 * math.sin(a) - 4)
        breathe = math.sin(self.time * 2.2) * (1 if self.name in ("dark", "wake") else 0)
        hip = (SIT_X, hip_y + breathe)
        legs = self.rotated(parts["legs"], 90, "legs")
        legs_c = placed_center(parts["legs"].get_size(), parts["legs_pivot"], 90, hip)
        body = self.rotated(parts["body"], tilt, "body")
        body_c = placed_center(parts["body"].get_size(), parts["body_pivot"], round(tilt / 2) * 2, hip)
        return [(legs, legs_c), (body, body_c)]

    def crouched(self, base, pose, tilt, crouch):
        """The whole picture, squashed down into a crouch and tilted about his feet."""
        crouch = round(crouch, 2)
        key = ("crouch", id(base), crouch)
        if key not in self.turned:
            w, h = base.get_size()
            self.turned[key] = (pygame.transform.smoothscale(base, (w, max(1, round(h * crouch))))
                                if crouch != 1.0 else base)
        img = self.turned[key]
        turned = self.rotated(img, tilt, ("crouch", crouch))
        w, h = img.get_size()
        return turned, placed_center((w, h), (w / 2, h), round(tilt / 2) * 2, (WAKE_X, GROUND_Y))

    def draw_world(self, surface):
        if self.scene:
            self.scene.draw(surface, 1, 600, self.time * 0.4)
        else:
            surface.fill((12, 14, 24))
            pygame.draw.rect(surface, (24, 30, 28), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        surface.blit(self.shade, (0, 0))
        # the shadow between the trees
        if self.shadow_x < WIDTH + 100:
            img = self.shadow_frames[int(self.time / 0.18) % len(self.shadow_frames)]
            if self.shadow_gone:
                img = img.copy()
                img.set_alpha(max(0, int(255 * (1 - self.shadow_gone / 0.8))))
            feet = (round(self.shadow_x), round(GROUND_Y - self.shadow_hover))
            surface.blit(img, img.get_rect(midbottom=feet))
        # the grimoire's glow, first in the roots, then in his hands
        beat = self.beat
        glow_from = [b[0] for b in BEATS].index("glow")
        if beat >= glow_from and not self.has_book:
            pulse = 30 * math.sin(self.time * 3)
            spot = (round(self.book_x), round(self.book_y))
            g = art.glow(int(60 + pulse * 0.3), (255, 210, 140), int(150 + pulse))
            surface.blit(g, g.get_rect(center=spot))
            book = art.grimoire_surface(self.book_open, round(self.book_size))
            surface.blit(book, book.get_rect(center=spot))
        if self.has_book:
            light = art.glow(100, (150, 220, 255), 90)
            surface.blit(light, light.get_rect(center=(round(self.x), GROUND_Y - 60)))
        for effect in self.effects:
            if isinstance(effect, RuneCircle):
                effect.draw(surface)
        state = self.rise_now()
        lying = 0.0
        if state:
            lying = abs(math.sin(math.radians(state[1])))
        # lying down, his shadow stretches out along the ground
        shade = art.shadow(int(70 + 70 * lying))
        sx = self.x if not state else (SIT_X + 20 * lying if state[0] == "sit" else WAKE_X)
        surface.blit(shade, shade.get_rect(center=(round(sx), GROUND_Y - 2)))
        for img, center in self.boy_parts():
            surface.blit(img, img.get_rect(center=(round(center[0]), round(center[1]))))
        for effect in self.effects:
            if not isinstance(effect, RuneCircle):
                effect.draw(surface)
        if self.bolt:
            self.bolt.draw(surface)
        self.particles.draw(surface)
        # eyelids: black from the top and bottom, parting as he wakes
        shut = 1 - self.eyelids()
        if shut > 0:
            lid = int(HEIGHT / 2 * shut) + 1
            pygame.draw.rect(surface, (0, 0, 0), (0, 0, WIDTH, lid))
            pygame.draw.rect(surface, (0, 0, 0), (0, HEIGHT - lid, WIDTH, lid))

    def draw_ui(self, surface):
        caption = BEATS[min(self.beat, len(BEATS) - 1)][2]
        if caption:
            shown = caption[:int(self.beat_time * 40)]       # typed out, 40 letters a second
            box = pygame.Rect(WIDTH // 2 - 360, HEIGHT - 110, 720, 80)
            ui.panel(surface, box, 190)
            # wrap the whole caption, so lines do not jump about as it types out
            left = shown
            for i, line in enumerate(ui.wrap(caption, ui.font(28), box.width - 30)):
                part, left = left[:len(line)], left[len(line):].lstrip(" ")
                ui.draw_text(surface, ui.font(28), part, BONE,
                             topleft=(box.x + 15, box.y + 10 + i * 32))
        if self.name == "type":
            size = 64
            width = ui.incantation_width(FIRST_WORD, size)
            pos = (WIDTH // 2 - width // 2, 150)
            ui.panel(surface, (pos[0] - 30, pos[1] - 22, width + 60, 90), 200,
                     border=MISS_COL if self.miss > 0 else (120, 100, 70))
            ui.draw_incantation(surface, FIRST_WORD, self.typed, pos, size)
            ui.draw_text(surface, ui.font(20), "type the word", GOLD,
                         center=(WIDTH // 2, pos[1] + 58))
        ui.draw_text(surface, ui.font(18), "Esc: skip", GRAY, topright=(WIDTH - 12, 10))
