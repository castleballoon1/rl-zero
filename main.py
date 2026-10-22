import pygame
import sys

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("2d project")

clock = pygame.time.Clock()
FPS = 60

BACKGROUND_IMAGE_PATH = None

background_image = None
if BACKGROUND_IMAGE_PATH:
    try:
        background_image = pygame.image.load(BACKGROUND_IMAGE_PATH).convert()
        background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except pygame.error as e:
        print(f"Could not load background image: {e}")

west_frames = [
    pygame.image.load("assets/Sprites/MC (simplified)/child_west1.png").convert_alpha(),
    pygame.image.load("assets/Sprites/MC (simplified)/child_west2.png").convert_alpha()
]

east_frames = [
    pygame.image.load("assets/Sprites/MC (simplified)/child_east1.png").convert_alpha(),
    pygame.image.load("assets/Sprites/MC (simplified)/child_east2.png").convert_alpha()
]

SCALE_FACTOR = 3
def scale_frames(frames):
    scaled = []
    for img in frames:
        w, h = img.get_size()
        scaled.append(pygame.transform.scale(img, (w * SCALE_FACTOR, h * SCALE_FACTOR)))
    return scaled

west_frames = scale_frames(west_frames)
east_frames = scale_frames(east_frames)

player_x = SCREEN_WIDTH // 2
player_y = SCREEN_HEIGHT - 200
player_speed = 4

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

    if keys[pygame.K_a]:
        player_x -= player_speed
        facing_right = False
        is_moving = True
    if keys[pygame.K_d]:
        player_x += player_speed
        facing_right = True
        is_moving = True

    player_x = max(0, min(SCREEN_WIDTH - west_frames[0].get_width(), player_x))

    if is_moving:
        anim_timer += 1
        if anim_timer >= ANIMATION_DELAY:
            animation_index = (animation_index + 1) % len(west_frames)
            anim_timer = 0
    else:
        animation_index = 0
        anim_timer = 0

    if background_image:
        screen.blit(background_image, (0, 0))
    else:
        screen.fill((50, 100, 150))

    if facing_right:
        current_image = east_frames[animation_index]
    else:
        current_image = west_frames[animation_index]

    screen.blit(current_image, (player_x, player_y))

    pygame.display.flip()
    clock.tick(FPS)
