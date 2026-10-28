import sys
import pygame

pygame.init()

# Screen Configuration
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Spell Typer - Combat Prototype")

clock = pygame.time.Clock()
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PURPLE = (75, 0, 130)
GOLD = (255, 215, 0)
GRAY = (100, 100, 100)
RED = (220, 20, 60)

# Fonts
font_large = pygame.font.SysFont("Courier New", 32, bold=True)
font_med = pygame.font.SysFont("Courier New", 24, bold=True)
font_small = pygame.font.SysFont("Courier New", 18)

# -------------------------------------------------------------------------
# MODULAR SPELL SCRIPTING
# -------------------------------------------------------------------------
class Spell:
    def __init__(self, name, incantation, effect_func, damage=25):
        self.name = name
        self.incantation = incantation.lower()
        self.effect_func = effect_func
        self.damage = damage

    def cast(self, combat_state):
        print(f" Casting Spell: {self.name} ('{self.incantation}')")
        if self.effect_func:
            self.effect_func(combat_state)

def spark_effect(state):
    state['enemy_hp'] -= state['current_spell'].damage
    state['message'] = f"Spark struck the beast for {state['current_spell'].damage} damage!"

# Initialize our baseline spell
baseline_spell = Spell(
    name="Spark",
    incantation="lumos",
    effect_func=spark_effect,
    damage=30
)

# -------------------------------------------------------------------------
# LOAD ASSETS (Fallback to simple shapes if files aren't found)
# -------------------------------------------------------------------------
def load_image_safely(path, scale=1):
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale != 1:
            w, h = img.get_size()
            img = pygame.transform.scale(img, (int(w * scale), int(h * scale)))
        return img
    except Exception:
        return None

# Load Player & Enemy graphics based on Milestone 1 references
player_img = load_image_safely("assets/Sprites/MC (simplified)/child_east1.png", scale=3)
if not player_img:
    # Placeholder surface if asset missing
    player_img = pygame.Surface((60, 100))
    player_img.fill((50, 150, 255))

enemy_img = load_image_safely("assets/Sprites/Enemies/Lantern_Stag_Spritesheet/LanternStag.png", scale=1.5)
if not enemy_img:
    enemy_img = pygame.Surface((180, 140))
    enemy_img.fill((100, 50, 120))

scroll_img = load_image_safely("Scroll.png", scale=1) # Optional spell banner background

# -------------------------------------------------------------------------
# COMBAT STATE & GAME LOOP
# -------------------------------------------------------------------------
combat_state = {
    'enemy_hp': 100,
    'enemy_max_hp': 100,
    'current_spell': baseline_spell,
    'typed_buffer': "",
    'message': "A wild horror emerges from the dark woods! Cast your spell!"
}

player_pos = (150, 320)
enemy_pos = (500, 260)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            if combat_state['enemy_hp'] > 0:
                if event.key == pygame.K_BACKSPACE:
                    combat_state['typed_buffer'] = combat_state['typed_buffer'][:-1]
                elif event.key == pygame.K_RETURN:
                    # Check if typed text matches spell incantation
                    if combat_state['typed_buffer'].strip().lower() == combat_state['current_spell'].incantation:
                        combat_state['current_spell'].cast(combat_state)
                        combat_state['typed_buffer'] = ""
                    else:
                        combat_state['message'] = "Incantation fizzled! Try again."
                        combat_state['typed_buffer'] = ""
                else:
                    # Append typed character if valid ASCII
                    char = event.unicode
                    if char.isprintable() and len(char) == 1:
                        combat_state['typed_buffer'] += char

    # Background Fill (Dark cursed fantasy theme)
    screen.fill((20, 15, 30))

    # Render Characters
    screen.blit(player_img, player_pos)
    screen.blit(enemy_img, enemy_pos)

    # Render Enemy Health Bar
    hp_bar_width = 200
    hp_bar_height = 20
    hp_x, hp_y = 500, 220
    current_hp_w = int(hp_bar_width * max(combat_state['enemy_hp'], 0) / combat_state['enemy_max_hp'])
    pygame.draw.rect(screen, RED, (hp_x, hp_y, hp_bar_width, hp_bar_height))
    pygame.draw.rect(screen, (50, 205, 50), (hp_x, hp_y, current_hp_w, hp_bar_height))
    pygame.draw.rect(screen, WHITE, (hp_x, hp_y, hp_bar_width, hp_bar_height), 2)
    
    hp_text = font_small.render(f"HP: {max(combat_state['enemy_hp'], 0)}/{combat_state['enemy_max_hp']}", True, WHITE)
    screen.blit(hp_text, (hp_x, hp_y - 25))

    # -------------------------------------------------------------------------
    # TYPING OF THE DEAD
    # -------------------------------------------------------------------------
    # UI Panel Box at the bottom
    panel_rect = pygame.Rect(50, 420, 700, 140)
    pygame.draw.rect(screen, (40, 30, 60), panel_rect)
    pygame.draw.rect(screen, GOLD, panel_rect, 3)

    # Display Status Message
    msg_surface = font_small.render(combat_state['message'], True, GOLD)
    screen.blit(msg_surface, (panel_rect.x + 20, panel_rect.y + 15))

    if combat_state['enemy_hp'] > 0:
        # Display Spell Name & Target Incantation
        spell_title = font_med.render(f"Spell: {combat_state['current_spell'].name}", True, WHITE)
        screen.blit(spell_title, (panel_rect.x + 20, panel_rect.y + 45))

        # Render Target Incantation with typed highlighting style
        target_str = combat_state['current_spell'].incantation
        typed_str = combat_state['typed_buffer']

        incant_label = font_large.render(f"Type: {target_str}", True, (150, 150, 150))
        screen.blit(incant_label, (panel_rect.x + 20, panel_rect.y + 80))

        # User Input Feedback
        input_surface = font_large.render(f"> {typed_str}_", True, WHITE)
        screen.blit(input_surface, (panel_rect.x + 350, panel_rect.y + 80))
    else:
        win_surface = font_large.render("ENEMY DEFEATED! Press ESC to exit.", True, (50, 255, 50))
        screen.blit(win_surface, (panel_rect.x + 40, panel_rect.y + 70))

    pygame.display.flip()
    clock.tick(FPS)
