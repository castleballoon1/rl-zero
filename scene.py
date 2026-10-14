import os
import pygame

SCENE_DIR = os.path.join(os.path.dirname(__file__), "assets", "Scene")


class ParallaxLayer:
    """One background image that scrolls at its own speed and wraps forever."""

    def __init__(self, image_path, speed, screen_height, drift=0.0):
        image = pygame.image.load(image_path).convert_alpha()

        # Scale to fill the screen height, keeping the aspect ratio
        w, h = image.get_size()
        scale = screen_height / h
        self.image = pygame.transform.smoothscale(image, (int(w * scale), screen_height))
        self.width = self.image.get_width()

        self.speed = speed  # 0 = never moves, 1 = moves with the camera
        self.drift = drift  # extra pixels/frame on its own (e.g. moving mist)
        self.offset = 0.0

    def update(self, camera_dx):
        self.offset += camera_dx * self.speed + self.drift
        self.offset %= self.width  # wrap so the number never grows forever

    def draw(self, screen):
        # Draw the image side by side enough times to cover the screen
        x = -self.offset
        while x < screen.get_width():
            screen.blit(self.image, (x, 0))
            x += self.width


class ParallaxBackground:
    """Holds every layer of a scene, back to front, and updates/draws them together."""

    # (file name, speed, drift) -- listed back (far) to front (near)
    FOREST_LAYERS = [
        ("Sky.png",               0.1, 0.0),
        ("Forest_Backround.png",  0.3, 0.0),
        ("Mist.png",              0.5, 0.3),
        ("Forest_Foreground.png", 0.7, 0.0),
        ("Foreground.png",        1.0, 0.0),
    ]

    def __init__(self, screen_height, layer_defs=FOREST_LAYERS, folder=SCENE_DIR):
        self.layers = [
            ParallaxLayer(os.path.join(folder, name), speed, screen_height, drift)
            for name, speed, drift in layer_defs
        ]

    def update(self, camera_dx):
        for layer in self.layers:
            layer.update(camera_dx)

    def draw(self, screen):
        for layer in self.layers:
            layer.draw(screen)
