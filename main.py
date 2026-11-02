import os
import sys
import pygame

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Spell Typer")

clock = pygame.time.Clock()
FPS = 60

font = pygame.font.SysFont("Courier New", 18, bold=True)
font_small = pygame.font.SysFont("Courier New", 14)
font_big = pygame.font.SysFont("Courier New", 40, bold=True)

# Loading the enemy sheets takes a moment, so say so
screen.fill((14, 10, 22))
loading = font.render("Loading...", True, (235, 222, 190))
screen.blit(loading, loading.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
pygame.display.flip()

# These need the window to exist first, so they are imported after set_mode
import sprites
import enemies
import combat_proto as combat

# Build paths from this file's folder so the game runs from any directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "assets", "Sprites", "MC (simplified)")

# The y position of the ground. Everyone's FEET are placed here.
GROUND_Y = 476  # the dirt path in the scene art (scene is scaled to 600 px tall)

# The world is wider than the screen; the camera follows the player.
WORLD_WIDTH = 4800
PLAYER_START_X = 200

# Enemies waiting along the path, in the order you meet them.
# x is where their feet are, in WORLD pixels (not screen pixels).
ENEMY_PLACEMENTS = [
    ("moth", 1100),
    ("maw", 1900),
    ("stag", 2700),
    ("pilgrim", 3500),
    ("bellwether", 4400),   # last one, the toughest
]
REST_HEAL = 25              # HP recovered after each won fight
ENCOUNTER_RANGE = 340       # show an enemy's name when the player is this close
ENEMY_ANIM_DELAY = 11       # frames between enemy idle frames

# Walking into an enemy plays a short animation before combat starts:
#   frames 0-20   the player freezes and a "!" pops up over their head
#   frames 0-48   the enemy rears up (its attack row, played once)
#   frames 50-90  black bars close in from the top and bottom
ENCOUNTER_FRAMES = 90       # 1.5 seconds at 60 FPS
BARS_START = 50
FADE_IN_FRAMES = 30         # coming back from combat, the world fades in over 0.5 s

WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
RED = (220, 20, 60)
GREEN = (80, 220, 120)
PARCHMENT = (235, 222, 190)

# Forest parallax from scene.py (falls back to a flat color if the art is missing)
try:
    from scene import ParallaxBackground
    background = ParallaxBackground(SCREEN_HEIGHT)
except Exception as e:
    print(f"Could not load scene background: {e}")
    background = None


def load_frames(names):
    return [pygame.image.load(os.path.join(SPRITE_DIR, name)).convert_alpha() for name in names]


west_frames = load_frames(["child_west1.png", "child_west2.png"])
east_frames = load_frames(["child_east1.png", "child_east2.png"])

SCALE_FACTOR = 3

# Crop west and east together so both directions share the same size and feet line
all_frames = sprites.crop_to_content(west_frames + east_frames)
west_frames = sprites.scale_frames(all_frames[:2], SCALE_FACTOR)
east_frames = sprites.scale_frames(all_frames[2:], SCALE_FACTOR)

player_speed = 4
half_width = east_frames[0].get_width() // 2
ANIMATION_DELAY = 10

# Same frames as in combat (cached in enemies.py, so they are only cut once)
enemy_art = {key: enemies.load_enemy_frames(key) for key, _ in ENEMY_PLACEMENTS}

overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
overlay.fill((0, 0, 0, 170))
black = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))  # for fading in, using set_alpha
black.fill((0, 0, 0))


# -------------------------------------------------------------------------
# A RUN: everything that resets when you die (permadeath, Milestone 1)
# -------------------------------------------------------------------------
def new_run():
    global player_x, player_hp, camera_x, facing_right, animation_index, anim_timer
    global world_enemies, game_state, toast, toast_timer, enemy_anim_frame, enemy_anim_timer
    global encounter_enemy, encounter_timer, fade_in_timer
    player_x = PLAYER_START_X          # CENTER of the player, in world pixels
    player_hp = combat.PLAYER_MAX_HP
    camera_x = 0
    facing_right = True
    animation_index = 0
    anim_timer = 0
    enemy_anim_frame = 0
    enemy_anim_timer = 0
    world_enemies = [{'key': key, 'x': x, 'alive': True} for key, x in ENEMY_PLACEMENTS]
    game_state = "explore"             # "explore", "encounter", "game_over" or "victory"
    encounter_enemy = None             # the enemy we just walked into
    encounter_timer = 0                # frames since the encounter started
    fade_in_timer = 0
    toast = "Walk with A / D. Something waits in the dark woods..."
    toast_timer = 240                  # frames to keep the message on screen


def enemy_hitbox(e):
    """The enemy's body in world pixels, narrowed so you have to really walk into it."""
    enemy = enemies.ENEMIES[e['key']]
    frame = enemy_art[e['key']]['idle'][0]
    body = sprites.body_rect(frame, (e['x'], GROUND_Y - enemy['hover']))
    return body.inflate(-body.width // 2, 0)


def player_hitbox():
    body = sprites.body_rect(east_frames[0], (player_x, GROUND_Y))
    return body.inflate(-body.width // 3, 0)


def begin_encounter(e):
    """Walked into an enemy: freeze and play the encounter animation first."""
    global game_state, encounter_enemy, encounter_timer, animation_index, anim_timer
    game_state = "encounter"
    encounter_enemy = e
    encounter_timer = 0
    animation_index = 0
    anim_timer = 0


def start_encounter(e):
    """The encounter animation finished: switch to the combat screen until the fight ends."""
    global player_hp, game_state, toast, toast_timer, player_x, fade_in_timer
    result, player_hp = combat.run_combat(e['key'], player_hp)
    pygame.display.set_caption("Spell Typer")
    clock.tick(FPS)  # forget the time spent in combat
    pygame.event.clear()  # don't let keys from combat leak back into the world
    fade_in_timer = FADE_IN_FRAMES
    game_state = "explore"

    if result == "won":
        e['alive'] = False
        healed = min(REST_HEAL, combat.PLAYER_MAX_HP - player_hp)
        player_hp += healed
        name = enemies.ENEMIES[e['key']]['name']
        toast = f"The {name} is gone. You catch your breath (+{healed} HP)."
        toast_timer = 180
        if not any(other['alive'] for other in world_enemies):
            game_state = "victory"
    else:
        game_state = "game_over"


def draw_text(f, text, color, **position):
    image = f.render(text, True, color)
    screen.blit(image, image.get_rect(**position))


def draw_hud():
    # HP bar, top-left
    pygame.draw.rect(screen, (14, 10, 22), (12, 12, 236, 46), border_radius=8)
    draw_text(font, "Wanderer", WHITE, topleft=(24, 16))
    draw_text(font_small, f"{player_hp}/{combat.PLAYER_MAX_HP}", PARCHMENT, topright=(236, 19))
    pygame.draw.rect(screen, (30, 20, 30), (24, 38, 212, 10), border_radius=4)
    fill = int(212 * player_hp / combat.PLAYER_MAX_HP)
    if fill > 0:
        pygame.draw.rect(screen, GREEN, (24, 38, fill, 10), border_radius=4)
    # Enemies left, top-right
    left = sum(1 for e in world_enemies if e['alive'])
    pygame.draw.rect(screen, (14, 10, 22), (SCREEN_WIDTH - 200, 12, 188, 30), border_radius=8)
    draw_text(font_small, f"Horrors remaining: {left}", PARCHMENT, center=(SCREEN_WIDTH - 106, 27))
    # Message along the bottom
    if toast_timer > 0:
        box = pygame.Rect(0, 0, 640, 34)
        box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)
        pygame.draw.rect(screen, (14, 10, 22), box, border_radius=8)
        draw_text(font_small, toast, PARCHMENT, center=box.center)


def draw_encounter_effects():
    """The "!" over the player and the black bars closing in."""
    t = encounter_timer
    # "!" pops up: it jumps 18 px, then settles back down
    bounce = 18 * max(0, 1 - t / 12) if t < 12 else 0
    head = sprites.body_rect(east_frames[0], (player_x - camera_x, GROUND_Y)).midtop
    bubble = pygame.Rect(0, 0, 34, 40)
    bubble.midbottom = (head[0], head[1] - 10 - bounce)
    pygame.draw.rect(screen, (14, 10, 22), bubble, border_radius=10)
    pygame.draw.rect(screen, GOLD, bubble, 2, border_radius=10)
    draw_text(font_big, "!", GOLD, center=bubble.center)

    # Black bars close in from the top and bottom, like a curtain
    if t > BARS_START:
        progress = min(1, (t - BARS_START) / (ENCOUNTER_FRAMES - BARS_START))
        bar_h = int(progress * progress * (SCREEN_HEIGHT // 2 + 2))  # starts slowly, then speeds up
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, SCREEN_WIDTH, bar_h))
        pygame.draw.rect(screen, (0, 0, 0), (0, SCREEN_HEIGHT - bar_h, SCREEN_WIDTH, bar_h))


def draw_end_overlay(title, color, line):
    screen.blit(overlay, (0, 0))
    draw_text(font_big, title, color, center=(SCREEN_WIDTH // 2, 230))
    draw_text(font, line, PARCHMENT, center=(SCREEN_WIDTH // 2, 290))
    draw_text(font_small, "Enter: start a new run     Esc: quit", PARCHMENT, center=(SCREEN_WIDTH // 2, 340))


new_run()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if game_state in ("game_over", "victory") and event.key == pygame.K_RETURN:
                new_run()

    # ---------- UPDATE ----------
    old_camera = camera_x
    if game_state == "explore":
        keys = pygame.key.get_pressed()
        is_moving = False

        if keys[pygame.K_a]:
            player_x -= player_speed
            facing_right = False
            is_moving = True
        if keys[pygame.K_d]:
            player_x += player_speed
            facing_right = True
            is_moving = True

        player_x = max(half_width, min(WORLD_WIDTH - half_width, player_x))

        if is_moving:
            anim_timer += 1
            if anim_timer >= ANIMATION_DELAY:
                animation_index = (animation_index + 1) % len(west_frames)
                anim_timer = 0
        else:
            animation_index = 0
            anim_timer = 0

        # Camera keeps the player in the middle, but stops at the ends of the world
        camera_x = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, player_x - SCREEN_WIDTH // 2))

        # Collision (class 9): walking into a living enemy starts a fight
        for e in world_enemies:
            if e['alive'] and player_hitbox().colliderect(enemy_hitbox(e)):
                begin_encounter(e)
                break

    elif game_state == "encounter":
        # Nothing you press counts here; the animation just plays out
        encounter_timer += 1
        if encounter_timer >= ENCOUNTER_FRAMES:
            start_encounter(encounter_enemy)

    if fade_in_timer > 0:
        fade_in_timer -= 1

    enemy_anim_timer += 1
    if enemy_anim_timer >= ENEMY_ANIM_DELAY:
        enemy_anim_timer = 0
        enemy_anim_frame = (enemy_anim_frame + 1) % 4
    if toast_timer > 0:
        toast_timer -= 1

    # ---------- DRAW ----------
    if background:
        background.update(camera_x - old_camera)
        background.draw(screen)
    else:
        screen.fill((50, 100, 150))

    # Enemies: world x minus camera x gives the screen x
    for e in world_enemies:
        if not e['alive']:
            continue
        enemy = enemies.ENEMIES[e['key']]
        frames = enemy_art[e['key']]['idle']
        image = frames[enemy_anim_frame % len(frames)]
        if game_state == "encounter" and e is encounter_enemy and encounter_timer < 48:
            # the enemy rears up once: its attack row, 12 frames per picture
            attack = enemy_art[e['key']]['attack']
            image = attack[min(len(attack) - 1, encounter_timer // 12)]
        screen_x = e['x'] - camera_x
        if -300 < screen_x < SCREEN_WIDTH + 300:  # only draw enemies near the screen
            rect = image.get_rect(midbottom=(screen_x, GROUND_Y - enemy['hover']))
            screen.blit(image, rect)
            if game_state in ("explore", "encounter") and abs(e['x'] - player_x) < ENCOUNTER_RANGE:
                body = sprites.body_rect(image, rect.midbottom)
                label = font.render(enemy['name'], True, RED)
                plate = label.get_rect(midbottom=(body.centerx, body.top - 8)).inflate(16, 8)
                pygame.draw.rect(screen, (14, 10, 22), plate, border_radius=6)
                screen.blit(label, label.get_rect(center=plate.center))

    if facing_right:
        current_image = east_frames[animation_index]
    else:
        current_image = west_frames[animation_index]

    # Anchor by the feet: midbottom puts the bottom-center of the sprite on the ground
    screen.blit(current_image, current_image.get_rect(midbottom=(player_x - camera_x, GROUND_Y)))

    draw_hud()
    if game_state == "encounter":
        draw_encounter_effects()
    if fade_in_timer > 0:
        black.set_alpha(int(255 * fade_in_timer / FADE_IN_FRAMES))
        screen.blit(black, (0, 0))
    if game_state == "game_over":
        draw_end_overlay("YOUR RUN HAS ENDED", RED, "The woods keep what they take. Begin again.")
    elif game_state == "victory":
        draw_end_overlay("THE WOODS FALL SILENT", GOLD, "Every horror on this path has been undone.")

    pygame.display.flip()
    clock.tick(FPS)
