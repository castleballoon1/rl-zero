"""Music and sound effects.

MUSIC is real recorded music: five CC0 (public domain) tracks in
assets/audio/, listed with their authors in assets/audio/CREDITS.md. They are
streamed with pygame.mixer.music, one at a time; when the scene changes the
old track fades out and the new one fades in. If a track's file is missing, a quiet drone made in code plays instead.

SOUND EFFECTS are all made in code from sine, square and saw waves and noise,
so they need no files. To use a recorded effect instead, put
assets/audio/sfx_<name>.wav (or .ogg) next to the music and it replaces the
one made here.

If the computer has no audio device, every call quietly does nothing.
"""
import math
import os
import random
from array import array

import pygame

from art import ASSET_DIR

AUDIO_DIR = os.path.join(ASSET_DIR, "audio")
RATE = 22050            # the effects are built at this many samples per second

# name -> (file, loops forever?, loudness). The boss track is mastered much
# louder than the others, so it is turned down to match.
MUSIC = {
    "woods": ("music_woods.ogg", True, 1.0),       # title, the woods, campfires, pages
    "battle": ("music_battle.ogg", True, 0.9),     # ordinary fights
    "boss": ("music_boss.ogg", True, 0.5),         # boss fights
    "defeat": ("stinger_defeat.ogg", False, 0.85),  # the death scene
    "victory": ("stinger_victory.ogg", False, 0.85),  # the escape
}
MUSIC_LEVEL = 0.55      # music sits under the effects
FADE_OUT = 0.3          # seconds the old track takes to fade away
FADE_IN_MS = 700        # milliseconds the new track takes to swell in


class Sound:
    def __init__(self):
        self.enabled = False
        self.sfx = {}
        self.drone = None            # stand-in when a music file is missing
        self.drone_channel = None
        self.current = None          # name of the music playing (or about to)
        self.switching = False       # True while the old track is fading out
        self.fade_left = 0.0
        self.level = 1.0             # loudness of the track playing now
        self.volume = 5              # 0..10, like the course menu
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            freq, size, channels = pygame.mixer.get_init()
            self.channels = channels
            # effects are built at RATE and each sample repeated to fill the mixer's rate
            self.repeat = max(1, round(freq / RATE))
            self.rate = freq / self.repeat
            pygame.mixer.set_num_channels(16)
            self.enabled = True
        except (pygame.error, TypeError):
            return
        self._build()
        self.set_volume(self.volume)

    # --- synthesis -----------------------------------------------------------
    def _make(self, samples):
        """Turn a list of floats in [-1, 1] into a pygame Sound."""
        data = array("h")
        copies = self.channels * self.repeat
        for v in samples:
            s = int(max(-1.0, min(1.0, v)) * 32000)
            for _ in range(copies):
                data.append(s)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _tone(self, freq, length, decay=8.0, wave="sine", slide=0.0, noise=0.0,
              attack=0.0, gain=0.5):
        """One note. slide is Hz per second; noise mixes in hiss (0..1);
        attack is the seconds it takes to swell in."""
        n = int(self.rate * length)
        out = []
        phase = 0.0
        rng = random.Random(int(freq * 100) + n)
        for i in range(n):
            t = i / self.rate
            f = max(20.0, freq + slide * t)
            phase += f / self.rate
            if wave == "square":
                v = 1.0 if (phase % 1.0) < 0.5 else -1.0
            elif wave == "saw":
                v = 2 * (phase % 1.0) - 1
            else:
                v = math.sin(phase * math.tau)
            v = v * (1 - noise) + (rng.random() * 2 - 1) * noise
            swell = min(1.0, t / attack) if attack else 1.0
            out.append(v * math.exp(-decay * t) * swell * gain)
        return out

    @staticmethod
    def _mix(*parts):
        """Play several sounds at once."""
        out = [0.0] * max(len(p) for p in parts)
        for part in parts:
            for i, v in enumerate(part):
                out[i] += v
        return out

    @staticmethod
    def _then(*parts):
        """Play several sounds one after another."""
        out = []
        for part in parts:
            out += part
        return out

    def _bell(self, freq, length=1.6):
        """A bell: several partials that are NOT whole multiples of the note."""
        partials = [(1.0, 0.5, 2.5), (2.0, 0.3, 3.5), (2.76, 0.25, 4.5), (5.4, 0.15, 7.0)]
        return self._mix(*[self._tone(freq * m, length, decay, gain=g)
                           for m, g, decay in partials])

    def _load_file(self, name):
        for folder in (AUDIO_DIR, ASSET_DIR):
            for ext in (".wav", ".ogg"):
                path = os.path.join(folder, name + ext)
                if os.path.exists(path):
                    try:
                        return pygame.mixer.Sound(path)
                    except pygame.error:
                        return None
        return None

    def _build(self):
        tone, mix, then = self._tone, self._mix, self._then
        recipes = {
            # --- typing: the key click climbs in pitch as a word nears its end
            **{f"key{i}": (lambda i=i: tone(700 + 110 * i, 0.04, 60, "square", gain=0.4))
               for i in range(6)},
            "key": lambda: tone(900, 0.04, 60, "square"),
            "miss": lambda: tone(140, 0.12, 25, "saw", noise=0.3),
            "lock": lambda: tone(660, 0.08, 30, slide=900),
            # --- menus
            "select": lambda: tone(440, 0.07, 30, "square"),
            "confirm": lambda: then(tone(520, 0.07, 22, "square"), tone(780, 0.12, 14, "square")),
            "fade": lambda: tone(300, 0.3, 7, noise=0.9, slide=-400, attack=0.08, gain=0.25),
            # --- casting, by element
            "cast": lambda: tone(300, 0.35, 7, "saw", slide=900, noise=0.15),
            "cast_fire": lambda: mix(tone(180, 0.45, 5, "saw", slide=500, noise=0.6, attack=0.05),
                                     tone(90, 0.3, 9, gain=0.4)),
            "cast_frost": lambda: mix(tone(1400, 0.4, 7, slide=-500),
                                      tone(2100, 0.3, 10, slide=-800, gain=0.3)),
            "cast_storm": lambda: then(tone(900, 0.06, 20, "square", slide=-6000, noise=0.4),
                                       tone(500, 0.3, 10, "square", slide=-1200, noise=0.5)),
            "cast_void": lambda: mix(tone(110, 0.6, 4, "saw", slide=-60),
                                     tone(116, 0.6, 4, "saw", slide=-70, gain=0.4)),
            "cast_bone": lambda: then(tone(320, 0.05, 40, "square", noise=0.4),
                                      tone(240, 0.25, 12, "square", slide=300, noise=0.2)),
            "cast_rot": lambda: tone(160, 0.5, 5, "saw", slide=120, noise=0.35, attack=0.1),
            "shield": lambda: mix(tone(440, 0.5, 5, slide=500, attack=0.05),
                                  tone(660, 0.5, 5, slide=700, attack=0.05, gain=0.3)),
            "heal": lambda: tone(520, 0.4, 5, slide=400),
            "pact": lambda: mix(tone(98, 0.8, 3, "saw", gain=0.45), tone(147, 0.8, 3, gain=0.35),
                                tone(233, 0.8, 4, gain=0.25)),
            "burnout": lambda: tone(600, 0.5, 6, "saw", slide=-1000, noise=0.8),
            "focus": lambda: then(tone(880, 0.05, 30), tone(1320, 0.14, 14)),
            # --- blows given and taken
            "hit": lambda: tone(120, 0.18, 18, "square", noise=0.5),
            "crit": lambda: tone(220, 0.4, 6, "square", slide=-300, noise=0.3),
            "enemy_die": lambda: tone(260, 0.7, 4, "saw", slide=-320, noise=0.35),
            "hurt": lambda: tone(90, 0.3, 9, "saw", noise=0.6),
            "warn": lambda: tone(200, 0.25, 6, "square", slide=200),
            "heavy": lambda: then(tone(110, 0.16, 6, "square", gain=0.6),
                                  tone(110, 0.3, 5, "square", slide=-40, gain=0.6)),
            "dodge": lambda: tone(500, 0.2, 10, noise=0.95, slide=1500, attack=0.04, gain=0.3),
            "deflect": lambda: tone(1200, 0.25, 12, slide=-800),
            "hex": lambda: mix(tone(330, 0.5, 5, "square", slide=-150, gain=0.3),
                               tone(349, 0.5, 5, "square", slide=160, gain=0.3)),
            "toll": lambda: self._bell(196),
            "rage": lambda: mix(tone(70, 0.9, 2.5, "saw", slide=40, noise=0.4, attack=0.1, gain=0.6),
                                tone(140, 0.9, 3, "square", slide=-50, noise=0.3, gain=0.3)),
            # --- the woods
            "jump": lambda: tone(260, 0.14, 12, slide=900, gain=0.35),
            "land": lambda: tone(90, 0.1, 30, noise=0.6, gain=0.4),
            "step": lambda: tone(70, 0.05, 50, noise=0.85, gain=0.22),
            "mote": lambda: then(tone(1047, 0.07, 18, gain=0.4), tone(1568, 0.25, 9, gain=0.4)),
            "shrine": lambda: mix(tone(262, 0.9, 3, attack=0.15, gain=0.3),
                                  tone(392, 0.9, 3, attack=0.15, gain=0.3),
                                  tone(523, 0.9, 3, attack=0.15, gain=0.25)),
            "page": lambda: tone(500, 0.6, 4, slide=200),
            "unlock": lambda: then(tone(523, 0.1, 10), tone(659, 0.1, 10), tone(784, 0.1, 10),
                                   tone(1047, 0.45, 5)),
            # --- the mind
            "heartbeat": lambda: then(tone(55, 0.12, 22, gain=0.9), [0.0] * int(self.rate * 0.06),
                                      tone(48, 0.16, 18, gain=0.7)),
            "death": lambda: tone(160, 1.4, 2, "saw", slide=-100, noise=0.2),
            "black": lambda: mix(tone(45, 1.8, 1.6, gain=0.9), tone(30, 1.8, 1.4, "saw", gain=0.3)),
        }
        for name, recipe in recipes.items():
            self.sfx[name] = self._load_file("sfx_" + name) or self._make(recipe())
        self.drone = self._make(self._drone())

    def _drone(self):
        """A slow two-note drone, 6 seconds, that loops cleanly."""
        out = []
        for i in range(int(self.rate * 6)):
            t = i / self.rate
            v = (math.sin(t * 55 * math.tau) * 0.5
                 + math.sin(t * 82.5 * math.tau) * 0.3
                 + math.sin(t * 110.5 * math.tau) * 0.15)
            v *= 0.55 + 0.45 * math.sin(t / 6 * math.tau)
            out.append(v * 0.35)
        return out

    # --- playback -----------------------------------------------------------
    def play(self, name):
        if self.enabled and name in self.sfx:
            self.sfx[name].play()

    def play_key(self, progress):
        """The key click, higher the further through the word you are (0..1)."""
        self.play(f"key{min(5, int(progress * 6))}")

    def play_cast(self, element):
        """The whoosh of a spell leaving, by element."""
        name = "cast_" + element
        self.play(name if name in self.sfx else "cast")

    def play_music(self, name):
        """Switch the background music; the old track fades out, the new one in.

        Asking for the track that is already playing does nothing, so scenes
        that share a track do not restart it. None means silence.
        The fade itself happens a little each frame in update().
        """
        if not self.enabled or name == self.current:
            return
        self.current = name
        self.switching = True
        playing = pygame.mixer.music.get_busy() or self.drone_channel is not None
        self.fade_left = FADE_OUT if playing else 0.0

    def update(self, dt):
        """Call once per frame: turns the old track down, then starts the new one."""
        if not self.enabled or not self.switching:
            return
        self.fade_left -= dt
        if self.fade_left > 0:
            quieter = self.fade_left / FADE_OUT
            pygame.mixer.music.set_volume(self.volume / 10 * MUSIC_LEVEL * self.level * quieter)
            if self.drone:
                self.drone.set_volume(self.volume / 10 * 0.5 * quieter)
            return
        self.switching = False
        pygame.mixer.music.stop()
        if self.drone_channel:
            self.drone_channel.stop()
            self.drone_channel = None
        if self.current is None:
            return
        filename, loops, self.level = MUSIC[self.current]
        try:
            pygame.mixer.music.load(os.path.join(AUDIO_DIR, filename))
            pygame.mixer.music.set_volume(self.volume / 10 * MUSIC_LEVEL * self.level)
            pygame.mixer.music.play(-1 if loops else 0, fade_ms=FADE_IN_MS)
        except pygame.error:
            # the file is missing or unreadable: hum the drone under looping scenes
            if loops and self.drone:
                self.drone.set_volume(self.volume / 10 * 0.5)
                self.drone_channel = self.drone.play(loops=-1, fade_ms=FADE_IN_MS)

    def set_volume(self, volume):
        self.volume = max(0, min(10, volume))
        if not self.enabled:
            return
        for s in self.sfx.values():
            s.set_volume(self.volume / 10 * 0.6)
        if self.drone:
            self.drone.set_volume(self.volume / 10 * 0.5)
        pygame.mixer.music.set_volume(self.volume / 10 * MUSIC_LEVEL * self.level)
