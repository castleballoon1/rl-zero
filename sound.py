"""Sound effects and a droning music loop, synthesized in code.

If the audio device is missing, every call quietly does nothing so the game
still runs (useful on lab machines without speakers).
To use real files, place e.g. assets/music.ogg or assets/sfx_hit.wav and they
will be used instead.
"""
import math
import os
import random
from array import array

import pygame

from art import ASSET_DIR

RATE = 22050


class Sound:
    def __init__(self):
        self.enabled = False
        self.sfx = {}
        self.music = None
        self.music_channel = None
        self.volume = 5          # 0..10, like the course menu
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            freq, size, channels = pygame.mixer.get_init()
            self.channels = channels
            self.rate = freq
            self.enabled = True
        except (pygame.error, TypeError):
            return
        self._build()
        self.set_volume(self.volume)

    # --- synthesis -----------------------------------------------------------
    def _make(self, samples):
        """Turn a list of floats in [-1, 1] into a pygame Sound."""
        data = array("h")
        for v in samples:
            s = int(max(-1.0, min(1.0, v)) * 32000)
            for _ in range(self.channels):
                data.append(s)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _tone(self, freq, length, decay=8.0, wave="sine", slide=0.0, noise=0.0):
        n = int(self.rate * length)
        out = []
        phase = 0.0
        rng = random.Random(int(freq * 100))
        for i in range(n):
            t = i / self.rate
            f = freq + slide * t
            phase += f / self.rate
            if wave == "square":
                v = 1.0 if (phase % 1.0) < 0.5 else -1.0
            elif wave == "saw":
                v = 2 * (phase % 1.0) - 1
            else:
                v = math.sin(phase * math.tau)
            v = v * (1 - noise) + (rng.random() * 2 - 1) * noise
            out.append(v * math.exp(-decay * t) * 0.5)
        return out

    def _load_file(self, name):
        for ext in (".wav", ".ogg"):
            path = os.path.join(ASSET_DIR, name + ext)
            if os.path.exists(path):
                try:
                    return pygame.mixer.Sound(path)
                except pygame.error:
                    return None
        return None

    def _build(self):
        recipes = {
            "key": lambda: self._tone(900, 0.04, 60, "square"),
            "miss": lambda: self._tone(140, 0.12, 25, "saw", noise=0.3),
            "lock": lambda: self._tone(660, 0.08, 30, "sine", slide=900),
            "cast": lambda: self._tone(300, 0.35, 7, "saw", slide=900, noise=0.15),
            "hit": lambda: self._tone(120, 0.18, 18, "square", noise=0.5),
            "crit": lambda: self._tone(220, 0.4, 6, "square", slide=-300, noise=0.3),
            "hurt": lambda: self._tone(90, 0.3, 9, "saw", noise=0.6),
            "deflect": lambda: self._tone(1200, 0.25, 12, "sine", slide=-800),
            "page": lambda: self._tone(500, 0.6, 4, "sine", slide=200),
            "heal": lambda: self._tone(520, 0.4, 5, "sine", slide=400),
            "warn": lambda: self._tone(200, 0.25, 6, "square", slide=200),
            "death": lambda: self._tone(160, 1.4, 2, "saw", slide=-100, noise=0.2),
            "select": lambda: self._tone(440, 0.07, 30, "square"),
        }
        for name, recipe in recipes.items():
            self.sfx[name] = self._load_file("sfx_" + name) or self._make(recipe())
        self.music = self._load_file("music") or self._make(self._drone())

    def _drone(self):
        """A slow, uneasy two-note drone with a beat, ~6 seconds, loops."""
        n = int(self.rate * 6)
        out = []
        for i in range(n):
            t = i / self.rate
            v = (math.sin(t * 55 * math.tau) * 0.5
                 + math.sin(t * 82.5 * math.tau) * 0.3
                 + math.sin(t * 110.5 * math.tau) * 0.15)
            v *= 0.55 + 0.45 * math.sin(t / 6 * math.tau)  # swell, loops cleanly
            out.append(v * 0.35)
        return out

    # --- playback -----------------------------------------------------------
    def play(self, name):
        if self.enabled and name in self.sfx:
            self.sfx[name].play()

    def start_music(self):
        if self.enabled and self.music and self.music_channel is None:
            self.music_channel = self.music.play(loops=-1)
            self.set_volume(self.volume)

    def set_volume(self, volume):
        self.volume = max(0, min(10, volume))
        if not self.enabled:
            return
        for s in self.sfx.values():
            s.set_volume(self.volume / 10 * 0.6)
        if self.music:
            self.music.set_volume(self.volume / 10 * 0.5)
