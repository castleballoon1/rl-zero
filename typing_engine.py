"""Tracks one typing attempt: progress, mistakes, speed (pure Python).

Like Typing of the Dead, a wrong key does not advance the cursor; it only
counts as a mistake. Accuracy = correct keys / all keys pressed.
"""


class TypingSession:
    def __init__(self, target, start_time=None):
        self.target = target
        self.pos = 0
        self.errors = 0
        self.start = start_time
        self.end = None

    @property
    def done(self):
        return self.pos >= len(self.target)

    @property
    def progress(self):
        return self.pos / max(1, len(self.target))

    def feed(self, ch, now):
        """Feed one character. Returns 'ok', 'miss' or 'done'."""
        if self.done:
            return "done"
        if self.start is None:
            self.start = now
        if ch == self.target[self.pos]:
            self.pos += 1
            if self.done:
                self.end = now
                return "done"
            return "ok"
        self.errors += 1
        return "miss"

    def accuracy(self):
        presses = self.pos + self.errors
        if presses == 0:
            return 1.0
        return self.pos / presses

    def elapsed(self, now):
        if self.start is None:
            return 0.0
        end = self.end if self.end is not None else now
        return max(0.0, end - self.start)

    def cps(self, now):
        """Characters per second (correct characters only)."""
        return self.pos / max(0.15, self.elapsed(now))
