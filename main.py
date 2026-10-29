import os
import sys
import pygame

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("2d project")

clock = pygame.time.Clock()
FPS = 60

# Build paths from this file's folder so the game runs from any directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "assets", "Sprites", "MC (simplified)")

# The y position of the ground. The player's FEET are placed here.
GROUND_Y = 476  # the dirt path in the scene art (scene is scaled to 600 px tall)

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


def crop_to_content(frames):
    """Trim the transparent border, using one box for every frame so nothing jitters.

    Without this, empty pixels under the sprite make it float above the ground,
    and frames with different padding make it wobble while walking.
    """
    box = frames[0].get_bounding_rect()
    for img in frames[1:]:
        box.union_ip(img.get_bounding_rect())
    return [img.subsurface(box).copy() for img in frames]


SCALE_FACTOR = 3
def scale_frames(frames):
    scaled = []
    for img in frames:
        w, h = img.get_size()
        scaled.append(pygame.transform.scale(img, (w * SCALE_FACTOR, h * SCALE_FACTOR)))
    return scaled


# Crop west and east together so both directions share the same size and feet line
all_frames = crop_to_content(west_frames + east_frames)
west_frames = scale_frames(all_frames[:2])
east_frames = scale_frames(all_frames[2:])

# player_x is the CENTER of the player, so turning around doesn't shift the sprite
player_x = SCREEN_WIDTH // 2
player_speed = 4
half_width = east_frames[0].get_width() // 2

facing_right = True
is_moving = False
animation_index = 0
anim_timer = 0
ANIMATION_DELAY = 10

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    is_moving = False
    old_x = player_x

    if keys[pygame.K_a]:
        player_x -= player_speed
        facing_right = False
        is_moving = True
    if keys[pygame.K_d]:
        player_x += player_speed
        facing_right = True
        is_moving = True

    player_x = max(half_width, min(SCREEN_WIDTH - half_width, player_x))

    if is_moving:
        anim_timer += 1
        if anim_timer >= ANIMATION_DELAY:
            animation_index = (animation_index + 1) % len(west_frames)
            anim_timer = 0
    else:
        animation_index = 0
        anim_timer = 0

    if background:
        background.update(player_x - old_x)
        background.draw(screen)
    else:
        screen.fill((50, 100, 150))

    if facing_right:
        current_image = east_frames[animation_index]
    else:
        current_image = west_frames[animation_index]

    # Anchor by the feet: midbottom puts the bottom-center of the sprite on the ground
    screen.blit(current_image, current_image.get_rect(midbottom=(player_x, GROUND_Y)))

    pygame.display.flip()
    clock.tick(FPS)
