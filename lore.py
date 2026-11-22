"""The grimoire's own story, written on the pages the bosses drop.

Every boss page carries one passage. What the grimoire SAYS is always
readable. Underneath it, in other hands, is what the readers before you
wrote, and you can only make that out when your sanity is below
LORE_TRUTH_BELOW: the grimoire lies, and only a fraying mind sees through it.

Act 1-3 bosses drop pages 1-3; the endless woods drop the rest in order.
Pages found are kept in save.json and can be read again in the codex.
"""

LORE_TRUTH_BELOW = 40       # read a page below this sanity to see what is written beneath

# (title, what the grimoire says, what is written beneath it)
LORE = [
    ("The First Page",
     "To whoever finds me: you are safe now. Read me aloud and the dark will keep "
     "its distance. I was made to lead lost children home.",
     "Beneath it, in a careful hand: It told me that too. I carried a lantern so the "
     "others could follow me. Now the lantern carries me. (Antlers are drawn in the margin.)"),
    ("The Second Page",
     "The marsh is only water. Walk on, and the path will remember your feet. Every "
     "reader who walked far enough found the way out.",
     "Beneath it, scratched hard enough to tear the paper: There is no way out, only "
     "further. I stopped walking and the roots kept me. Do not stop."),
    ("The Third Page",
     "Here the stars go out, but you will not need them. You have me. When the bell "
     "rings, the woods let one reader go. Listen for it.",
     "Beneath it: I rang it for every one of them and led them in like a flock. It "
     "feeds on the words, child. Every spell you cast is a little of you, written into it."),
    ("A Page With Wet Ink",
     "You do not remember turning back. That is all right. Good readers always turn "
     "back. The gate will open for you when you are ready.",
     "Beneath it: The gate is not a way out. It is an eye. It has been reading you "
     "the whole time, the way you read it."),
    ("A Page Full of Wings",
     "Do not be afraid of the moths. They only sing because they love the light, "
     "and I am the only light in these woods.",
     "Beneath it, in many small hands at once: We got too close to the pages. Now "
     "we sing the words so loudly that no one else can hear them."),
    ("The Page of Names",
     "Your name is written on my first page. That is how you know I am yours, and "
     "you are mine.",
     "Beneath it: Go back and look. The first page is full of names, every one "
     "crossed out. Yours is only the newest. Mine is just above it."),
    ("The Page of Forgetting",
     "Every spell you cross out is forgiven. I forget them, so that you do not have "
     "to carry them.",
     "Beneath it: It forgets nothing. It keeps everything a reader lets go of, down "
     "in the mire, and what is kept there grows hungry."),
    ("A Page in Nonsense",
     "Soon you will not need to type at all. I will speak for you, and the words "
     "will come out right.",
     "Beneath it: When the words turn to nonsense, that is not madness. That is its "
     "real language. You have started to read it properly."),
    ("The Last Page",
     "This is the last page. Close me now. Lie down in the leaves and sleep, and "
     "when you wake you will be home.",
     "Beneath it: There is no last page. Turn it. And under that, in your own "
     "handwriting, though you do not remember writing it: I am still here."),
]


def lore_index(act):
    """Which passage the boss of this act drops (the last one repeats after that)."""
    return max(0, min(len(LORE) - 1, act - 1))


def truth_visible(sanity):
    return sanity < LORE_TRUTH_BELOW
