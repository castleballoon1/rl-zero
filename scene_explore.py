"""Walking through the procedurally generated woods (side-scrolling)."""
import math
import random

import pygame

import art
import ui
from bestiary import act_info, scaled_enemy, boss_for
from entities import Layer, Player, MapEnemy, burst
from settings import (WIDTH, HEIGHT, GROUND_Y, WHITE, GRAY, GOLD, BONE,
                      BRAMBLE_DAMAGE, MOTE_SANITY, SHRINE_SANITY, MISS_COL, SANITY_COL)
from worldgen import generate_act


class ExploreScene:
    music = "woods"
    pausable = True
    show_sanity_fx = True

    def __init__(self, game):
        self.game = game
        run = game.run
        self.level = generate_act(run.seed, run.act)
        self.info = act_info(run.act)
        # the painted forest if its art is there, otherwise woods drawn with shapes
        self.scene = art.forest_scene()
        if self.scene:
            plat_col = (62, 78, 92)
        else:
            far, mid, trunks, near = art.parallax_layers(self.info, run.seed)
            self.layers = [Layer(far, 0.08), Layer(mid, 0.35), Layer(trunks, 0.7)]
            self.near_layer = Layer(near, 1.25)   # drawn in front of the player
            self.ground = art.ground_tile(self.info["ground"])
            plat_col = tuple(min(255, c + 55) for c in self.info["ground"])
        self.platforms = []
        for (x, y, w, h) in self.level["platforms"]:
            self.platforms.append((pygame.Rect(x, y, w, h),
                                   art.platform_surface(w, h, plat_col)))
        self.platform_rects = [p[0] for p in self.platforms]

        self.player = Player(80)
        self.enemies = pygame.sprite.Group()
        for i, enc in enumerate(self.level["encounters"]):
            if i not in run.cleared:
                self.enemies.add(MapEnemy(i, enc["x"], enc["enemies"]))
        self.shrines = []
        for i, (x, y) in enumerate(self.level["shrines"]):
            self.shrines.append((i, pygame.Rect(x - 20, y - 60, 40, 60)))
        self.lore = [(pygame.Rect(x - 13, GROUND_Y - 34, 26, 34), text)
                     for x, text in self.level["lore"]]
        self.brambles = [(pygame.Rect(x - w // 2, GROUND_Y - 20, w, 20),
                          art.bramble_surface(w))
                         for x, w in self.level["brambles"]]
        # each mote is [rect, taken]
        self.motes = [[pygame.Rect(x - 10, y - 10, 20, 20), False]
                      for x, y in self.level["motes"]]
        self.lore_img = art.lore_surface()
        self.gate_img = art.gate_surface()
        self.gate_rect = self.gate_img.get_rect(midbottom=(self.level["gate_x"], GROUND_Y))
        self.particles = pygame.sprite.Group()
        self.camera_x = 0.0
        self.banner = 3.0
        self.grace = 0.8
        self.step_timer = 0.0
        self.reading = None
        self.prompt = ""
        self.time = 0.0

    # --- events ----------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.reading:
            self.reading = None
            return
        if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            if self.player.on_ground:
                self.game.sound.play("jump")
            self.player.jump()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.player.drop()
        elif event.key == pygame.K_e:
            self.interact()
        elif event.key == pygame.K_RETURN:
            if self.player.hitbox.colliderect(self.gate_rect.inflate(60, 0)):
                run = self.game.run
                self.game.start_combat([boss_for(run.act, run.difficulty)], True, None)

    def interact(self):
        run = self.game.run
        for i, rect in self.shrines:
            if self.player.hitbox.colliderect(rect.inflate(30, 10)) and i not in run.shrines_used:
                run.shrines_used.add(i)
                run.change_sanity(SHRINE_SANITY)
                self.game.sound.play("shrine")
                burst(self.particles, rect.center, (130, 180, 255), 30)
                self.game.float_text(f"+{SHRINE_SANITY} sanity", (WIDTH // 2, 200), (150, 200, 255))
                return
        for rect, text in self.lore:
            if self.player.hitbox.colliderect(rect.inflate(30, 10)):
                self.reading = text
                self.game.sound.play("page")
                return

    # --- update --------------------------------------------------------------
    def update(self, dt):
        self.time += dt
        self.banner = max(0.0, self.banner - dt)
        if self.reading:
            return
        keys = pygame.key.get_pressed()
        was_in_air = not self.player.on_ground
        self.player.update(dt, keys, self.platform_rects, self.level["length"],
                           self.game.run.sanity, self.game.run.max_sanity)
        # footsteps while he walks, a thud when he lands
        if self.player.on_ground:
            if was_in_air:
                self.game.sound.play("land")
            if abs(self.player.vel.x) > 10:
                self.step_timer -= dt
                if self.step_timer <= 0:
                    self.step_timer = 0.3
                    self.game.sound.play("step")
        target = self.player.pos.x - WIDTH * 0.4
        self.camera_x = max(0.0, min(self.level["length"] - WIDTH, target))
        self.enemies.update(dt)
        self.particles.update(dt)
        if self.check_hazards():
            return

        self.grace = max(0.0, self.grace - dt)
        if self.grace <= 0:
            for enemy in self.enemies:
                # the creature's painted body, narrowed so you really walk into it
                if self.player.hitbox.colliderect(enemy.body.inflate(-enemy.body.width // 3, 0)):
                    act = self.game.run.act
                    datas = [scaled_enemy(k, act, self.game.run.difficulty) for k in enemy.kinds]
                    self.game.start_combat(datas, False, enemy.index)
                    return

        self.prompt = ""
        run = self.game.run
        for i, rect in self.shrines:
            if self.player.hitbox.colliderect(rect.inflate(30, 10)):
                self.prompt = ("E: pray at the shrine" if i not in run.shrines_used
                               else "The shrine's flame is spent.")
        for rect, _ in self.lore:
            if self.player.hitbox.colliderect(rect.inflate(30, 10)):
                self.prompt = "E: read the stone"
        if self.player.hitbox.colliderect(self.gate_rect.inflate(60, 0)):
            left = len(self.enemies)
            extra = f"   ({left} creatures still roam)" if left else ""
            self.prompt = "Enter: face the boss" + extra

    def check_hazards(self):
        """Thorns hurt, motes soothe. Returns True if the run just ended."""
        p = self.player
        run = self.game.run
        if p.invulnerable <= 0:
            for rect, _ in self.brambles:
                if p.hitbox.colliderect(rect):
                    run.hurt(BRAMBLE_DAMAGE)
                    p.hurt(-1 if p.pos.x < rect.centerx else 1)
                    self.game.sound.play("hurt")
                    self.game.add_shake(0.25, 5)
                    self.game.float_text(f"Thorns!  -{BRAMBLE_DAMAGE} sanity",
                                         (WIDTH // 2, 200), MISS_COL)
                    burst(self.particles, p.rect.midbottom, (170, 30, 40), 12)
                    if run.dead:
                        self.game.game_over("madness")
                        return True
                    break
        for mote in self.motes:
            if not mote[1] and p.hitbox.colliderect(mote[0]):
                mote[1] = True
                run.change_sanity(MOTE_SANITY)
                self.game.sound.play("mote")
                burst(self.particles, mote[0].center, (190, 170, 255), 14, speed=(30, 120))
                self.game.float_text(f"+{MOTE_SANITY} sanity", (WIDTH // 2, 200), SANITY_COL)
        return False

    def on_cleared(self, index):
        for enemy in list(self.enemies):
            if enemy.index == index:
                burst(self.particles, enemy.body.center, (150, 90, 220), 25)
                enemy.kill()
        self.grace = 1.0

    # --- drawing -----------------------------------------------------------------
    def draw_world(self, surface):
        cam = int(self.camera_x)
        if self.scene:
            self.scene.draw(surface, self.game.run.act, cam, self.time)
        else:
            for layer in self.layers:
                layer.draw(surface, cam)
            tw = self.ground.get_width()
            for x in range(-int(cam % tw), WIDTH + tw, tw):
                surface.blit(self.ground, (x, GROUND_Y))
        for rect, img in self.platforms:
            surface.blit(img, (rect.x - cam, rect.y))
        run = self.game.run
        for i, rect in self.shrines:
            used = i in run.shrines_used
            if not used:
                g = art.glow(40, (110, 160, 255), 90 + int(30 * math.sin(self.time * 3)))
                surface.blit(g, g.get_rect(center=(rect.centerx - cam, rect.centery)))
            surface.blit(art.shrine_surface(used), (rect.x - cam, rect.y))
        for rect, _ in self.lore:
            surface.blit(self.lore_img, (rect.x - cam, rect.y))
        for rect, img in self.brambles:
            surface.blit(img, (rect.x - cam, rect.bottom - 40))
        for k, (rect, taken) in enumerate(self.motes):
            if not taken:
                bob = int(math.sin(self.time * 3 + k) * 4)
                g = art.glow(26, (255, 235, 150), 255)
                surface.blit(g, g.get_rect(center=(rect.centerx - cam, rect.centery + bob)))
                pygame.draw.circle(surface, (40, 30, 60),
                                   (rect.centerx - cam, rect.centery + bob), 6)
                pygame.draw.circle(surface, (255, 250, 215),
                                   (rect.centerx - cam, rect.centery + bob), 4)
        g = art.glow(110, (200, 40, 70), 70)
        surface.blit(g, g.get_rect(center=(self.gate_rect.centerx - cam, self.gate_rect.centery)))
        surface.blit(self.gate_img, (self.gate_rect.x - cam, self.gate_rect.y))
        for enemy in self.enemies:
            surface.blit(enemy.image, (enemy.rect.x - cam, enemy.rect.y))
            if len(enemy.kinds) > 1:      # more than one creature waits in this fight
                ui.draw_text(surface, ui.font(24), f"x{len(enemy.kinds)}", (255, 120, 120),
                             midbottom=(enemy.body.centerx - cam, enemy.body.top - 4))
        # the grimoire's glow around the boy
        p = self.player
        flicker = 4 * math.sin(self.time * 9) + 2 * math.sin(self.time * 23)
        light = art.glow(int(100 + flicker), (150, 220, 255), 90)
        surface.blit(light, light.get_rect(center=(p.rect.centerx - cam, p.rect.centery)))
        if p.visible():
            surface.blit(p.image, (p.rect.x - cam, p.rect.y))
        for part in self.particles:
            surface.blit(part.image, (part.rect.x - cam, part.rect.y))
        if not self.scene:
            self.near_layer.draw(surface, cam)

    def draw_ui(self, surface):
        game = self.game
        game.draw_hud(surface)
        # progress line through the act
        x0, x1, y = 300, WIDTH - 300, 22
        pygame.draw.line(surface, GRAY, (x0, y), (x1, y), 2)
        length = self.level["length"]
        for enemy in self.enemies:
            ex = x0 + (x1 - x0) * enemy.home / length
            pygame.draw.circle(surface, (200, 60, 60), (int(ex), y), 4)
        for i, rect in self.shrines:
            if i not in game.run.shrines_used:
                sx = x0 + (x1 - x0) * rect.centerx / length
                pygame.draw.circle(surface, (120, 170, 255), (int(sx), y), 4)
        pygame.draw.circle(surface, (200, 40, 70), (x1, y), 6)
        px = x0 + (x1 - x0) * self.player.pos.x / length
        pygame.draw.circle(surface, GOLD, (int(px), y), 5)
        ui.draw_text(surface, ui.font(22), self.level["name"], BONE, midtop=(WIDTH // 2, y + 10))

        if self.prompt:
            width = ui.font(28).size(self.prompt)[0] + 30
            ui.panel(surface, (WIDTH // 2 - width // 2, HEIGHT - 62, width, 38), 230)
            ui.draw_text(surface, ui.font(28), self.prompt, WHITE, center=(WIDTH // 2, HEIGHT - 43))
        else:
            ui.draw_text(surface, ui.font(20),
                         "A/D: walk    Space: jump    S: drop down    E: interact    Esc: pause",
                         GRAY, center=(WIDTH // 2, HEIGHT - 10))
        if self.banner > 0:
            a = min(1.0, self.banner)
            img = ui.font(64).outlined(f"Act {game.run.act}: {self.level['name']}", BONE)
            img.set_alpha(int(255 * a))
            surface.blit(img, img.get_rect(center=(WIDTH // 2, 170)))
        if self.reading:
            ui.panel(surface, (WIDTH // 2 - 300, 150, 600, 150), 230)
            lines = ui.wrap(self.reading, ui.font(30), 560)
            for i, line in enumerate(lines):
                ui.draw_text(surface, ui.font(30), line, BONE,
                             center=(WIDTH // 2, 195 + i * 32))
            ui.draw_text(surface, ui.font(20), "(any key)", GRAY, center=(WIDTH // 2, 285))
