# Spell Typer

*A lost boy, a dark wood, and a grimoire that lies.*

A 2D roguelike for CPSC 4160/6160. You walk the painted woods, and when a creature catches you, you fight by **typing incantations**. **Sanity is your only health**: it pays for spells, blows take it, and as it falls the words you must type are scrambled, the boy's eye reddens and the pages you find grow stronger.

## Run it

```
pip install pygame
python main.py
```

| Command | What it runs |
|---|---|
| `python main.py` | The full game |
| `python overworld_proto.py` | The earlier walking prototype (the old `main.py`, unchanged) |
| `python combat_proto.py [stag\|moth\|maw\|pilgrim\|bellwether]` | The earlier turn-based combat prototype |

The plain `README` file describes the two prototypes.

## Controls

| Where | Keys |
|---|---|
| Title | **Type a word to choose it:** `start`, `codex`, `guide` or `quit` (Up/Down and Enter also work) · Left/Right for volume · any key skips the opening animation |
| Naming the boy | Type a name and an optional seed · Tab or Up/Down to switch field · Left/Right to pick the difficulty · Enter to begin |
| Opening scene | Type `ignis` when the grimoire asks · Esc to skip the whole scene |
| Woods | Arrows or A/D to walk · Space/W/Up to jump (over thorns, up to the lights) · S/Down to drop through a platform · E to pray at a shrine or read a stone · Enter at the gate to fight the boss · Esc to pause |
| Combat | Type a spell's incantation to cast it (no Enter needed) · Tab or Left/Right to switch target · Backspace to cancel the spell · Esc to pause |
| Pages, campfires and the dawn | Up/Down and Enter, or press a number · on a boss page, any key turns from the passage to the choices · Esc backs out of crossing a spell out |
| Codex | Left/Right to turn the page · Esc to go back |

## How it plays

* **Title screen:** the name falls into place letter by letter while the boy walks in with his grimoire. Every menu choice is a word you type; type `start` and he casts a spell at the title before the screen fades.
* **Opening scene:** the boy wakes in the woods (his eyes open, droop and open again) and gets up, using the painted wake-to-walk frames (`assets/Sprites/Opening/Wake to Walk.png`). He has no book until he finds the glowing grimoire in the roots and it drifts into his hands; then he drives off a shadow by typing its first word, `ignis`. Esc skips it.
  * He walks at one steady pace (`WALK_SPEED` in `scene_intro.py`) with one step rhythm, both to the book and off the screen, and his footsteps are heard.
  * The painted frames are scaled by one factor so he stands exactly as tall as the boy with the grimoire, and they are lined up by his feet, so he does not grow, shrink or hop when he takes the book.
* **Three acts:** The Whispering Woods, The Hollow Marsh and The Starless Grove. Each is a side-scrolling stretch of the forest with creatures on the path, shrines, lore stones and a boss gate you enter when you are ready. The woods are generated from a seed you can type in.
  * **Each act is exponentially harder:** creatures have 1.5× the health, 1.32× the damage and attack 1.1× as often as in the act before, so act 3 creatures have 2.25× the health of act 1's.
  * **More creatures each act:** 5 groups in act 1 (one or two creatures each), 7 in act 2 and 9 in act 3 (two or three each). The woods grow longer to hold them, and act 3 has a third shrine.
  * **Thorns** cost 6 sanity if you walk into them, so jump them.
  * **Motes of light** on platforms and in the air give +4 sanity each.
* **Sanity is your only health.** There is no separate health bar.
  * Spells cost sanity, and every blow that lands takes it. At 0 the run ends.
  * Paying for a spell can never take your last point. A spell you cannot fully pay for still casts, but weaker in proportion (its cost shows in red).
  * **71–100 Lucid:** words are spelled correctly. No screen effects.
  * **31–70 Uneasy:** 15–50% of the letters are replaced (more the lower you go). You type what you see. A slight black vignette closes in, and now and then a hallucinated word drifts past.
  * **0–30 Fraying:** the words become garbled nonsense. A red vignette pulses at the edges, faster as sanity falls, hallucinated words crowd the screen, and his heartbeat is heard.
  * The letters jitter more at each band, and **the boy's eye turns from brown to red** as sanity falls.
  * It comes back from shrines (+35), motes, the Clarity and Mend spells, burning a page (+20), campfires (+45) and a breath after each fight (+6).
* **Typing combat, inspired by Typing of the Dead:** your grimoire's spells are listed at the bottom of the screen.
  * The first letters you type pick the spell. After that, a wrong key counts as a mistake and does not move you forward.
  * **Damage = spell strength × accuracy².** Strength = power per letter × number of letters × level bonus × page potency, so **longer incantations hit harder**.
  * **Crit chance is inversely proportional to typing speed:** chance = 1 ÷ (letters per second), clamped to 5–50%. Careful typing earns crits, but the enemies' attack bars keep filling while you take your time.
  * **Casting animation:** the grimoire gathers light as you type; on the last letter a rune circle opens at the boy's feet, a pillar of light rises, and the bolt flies a moment later and bursts in a ring where it lands.
* **Burnout:** casting the same spell 3 times in quick succession burns it out for 8 seconds. Each cast adds a point of heat (the orange pips beside the spell's name) and a point fades every 6 seconds.
* **Focus:** every cast at 95%+ accuracy adds a point of Focus, up to 5. Each point adds +8% to every spell. A cast below 80% accuracy, or any blow that lands on you, resets it.
* **Defense:** when an enemy's attack bar fills, it rears up and a Defend word appears.
  * Type it in time to **dodge**.
  * Type it before the marker line at 90%+ accuracy to **deflect** half the damage back.
  * Get halfway through and you're **grazed** for half damage.
  * **Heavy blows** are rolled at random (about 30% of attacks; more for the Lantern Stag). The attack bar turns magenta once it is past halfway, the word is one step harder, and it takes 1.5× the sanity.
  * **Creatures keep no steady beat.** The wait between attacks is wide and random, and each attack bar speeds up and slows down as it fills. Each creature has its own habits (`STYLES` in `bestiary.py`):
    * **Quick strikes** come after only 40–65% of the usual wait (the Mire Maw does this most).
    * **Feints:** the creature rears up, holds back, and strikes for real 0.7–1.6 s later (the Moth Choir does this most).
    * **Flurries:** a second blow follows the first almost at once ("Again!"; the Rootbound Pilgrim does this most).
    * Bosses feint and flurry more, and more still once enraged.
  * **The lower your sanity, the harder the words:** short words above 75%, longer words between 45% and 75%, phrases below 45%, and phrases with misspelled letters below 20%. You get 0.6 s plus time per letter, and the typing speed that time assumes rises at each step.
* **Pages, like Balatro's boss blinds:**
  * A dying creature dissolves into a page (its death sheet plays). Bosses drop a full page, ordinary fights a scrap.
  * **The lower your sanity when you read it,** the higher its potency (up to ×1.9), the more spells you can choose from (up to 5), and below 40 sanity forbidden spells appear. The page is cyan when you are Lucid, violet when Uneasy, crimson when Fraying.
  * Picking a spell you already own empowers it by one level. You can also burn the page for +20 sanity: it catches at the bottom and burns up to ash, taking the writing with it.
  * **A full grimoire (8 spells) can still take a new spell:** choose it, then cross out one of your spells to make room. The pen strikes it through and the new spell is written in its place. "Never mind" (or Esc) goes back to the page.
  * **Boss pages carry the grimoire's story.** Before you choose, you read one passage (`lore.py`): what the grimoire says about itself. Read it **below 40 sanity** and what earlier readers wrote beneath it shows through in red ink. The grimoire lies; only a fraying mind sees it. Acts 1 to 3 give the first three pages and the endless woods the rest (9 in all). Pages found are kept in `save.json` and can be read again in the codex.
* **Campfires:** after the first and second boss you pick one: regain 45 sanity, raise one spell by a level, or take one of two relics.
* **Dawn and the endless woods:** beating the third boss counts as an escape. Then you choose: walk out of the woods (the run ends in victory) or turn back into the dark. The endless woods repeat the three acts' looks ("Deeper I: The Whispering Woods" ...), with every creature roaming, one more group each act (up to 12), and a campfire between acts. Past act 3, every act multiplies the creatures' health by 1.15, their damage by 1.10 and how often they attack by 1.06, and their feints, flurries and first attacks come back 6% sooner. No creature waits less than 1.6 s between attacks. The bosses return as "The Deeper ..." versions.
* **Difficulty levels,** picked when you name the boy (the last one is remembered):

  | Level | Creature health | Damage | Attack speed | Time on Defend words |
  |---|---|---|---|---|
  | Story | ×0.75 | ×0.6 | ×0.85 | ×1.35 |
  | Normal | ×1 | ×1 | ×1 | ×1 |
  | Hard | ×1.25 | ×1.25 | ×1.12 | ×0.9 |
  | Nightmare | ×1.5 | ×1.5 | ×1.25 | ×0.8 |
* **Death:** when sanity reaches 0 the screen goes black and the boy stands alone in the middle. His eyes burn red, go black, and he comes apart into purple wisps (`assets/Sprites/Death/Fading Boy with Purple Wisps.png`). Each painted frame melts into the next instead of cutting, wisps drift up off him, and what is left fades into the dark. Any key skips to the end screen.
* **Scene changes** fade through black.
* **Score, codex, permadeath:** each run ends with a score and the best is saved. The codex on the title menu lists every spell (and how to unlock the sealed ones), relic and trait, and the boss pages you have found. Death resets your grimoire; unlocked spells are kept in `save.json`.

## Creatures

| Creature | Where | Trait |
|---|---|---|
| Moth Choir | All acts | **Stare:** drains sanity for as long as it lives |
| Mire Maw | All acts | **Drink:** heals by the sanity it takes from you |
| Lantern Stag | Acts 2–3; boss of act 1 | **Hex:** a blow that lands scrambles one of your spells until you cast it |
| Rootbound Pilgrim | Act 3 and the endless woods; boss of act 2 | **Grasp:** its attacks never use the short Defend words |
| Starved Bellwether | Boss of act 3; roams the endless woods | **Toll:** sometimes rings its bell instead of striking, which costs 4 sanity and scrambles a spell |

## Spells

| Spell | Incantation | Effect | Unlock |
|---|---|---|---|
| Ember | ignis | Damage | Starter |
| Ward | aegis fortis | Shield that absorbs blows | Starter |
| Frost Needle | glacies acus | Damage + delays the target's attack | Starter |
| Spark Lash | fulgur verbera | Damage | Available from the start |
| Mend | sana vulnus meum | Regain sanity over 6 s (free) | Available from the start |
| Clarity | mens clara manet | Regain sanity at once and lift every hex (free) | Available from the start |
| Cinder Rain | pluvia cinerum | Hits all foes (cheap) | Available from the start |
| Withering Word | marcesce vis tua | Damage; the target's blows take 30% less for the fight (never below 40% of the original) | Available from the start |
| Shatter Stride | frange impetum | Damage; knocks the target's attack bar back to empty and breaks off a feint | Available from the start |
| Hex of Rot | putresce caro mortalis | Damage over 6 s | Available from the start |
| Bone Spear | os hasta perforat | Heavy damage | Available from the start |
| Whisper Pact | foedus susurri in tenebris | Pay sanity; your next attack hits about 90% harder | Available from the start |
| Soul Drain | anima tua mihi exhauritur | Damage; regain half of it as sanity | Beat The Lantern Stag |
| Chain Lightning | tonitrus catena saltat | Hits all foes | Beat The Rootbound Pilgrim |
| Hourglass Rend | clepsydra frangitur | Delays every foe's attack | Beat The Rootbound Pilgrim |
| Thorn Cage | spinae te claudunt | Damage + delays the target 3 s | Deflect 8 attacks in one run |
| Grimoire Flare | lumen lucernae exardescit | Hits all foes | Cast 40 spells in one run |
| Final Word | verbum ultimum | Double damage to a foe below 30% health | Cast a 20+ letter incantation at 100% accuracy |
| Mirror Veil | speculum reddit ictum | The next blow that would land is turned back on its maker, plus the spell's strength | Available from the start |
| Echo | echo verborum redit | Your last spell sounds again at about 58% (more with levels), for free | Beat The Lantern Stag |
| Creeping Plague | lues per omnes serpit | Every foe rots over 6 s | Beat The Rootbound Pilgrim |
| Black Sun | sol niger ardet in me | Huge damage (forbidden) | Available from the start |
| The Gate's Gaze | oculus ultra portam aperitur | Massive damage (forbidden) | Win a fight with under 15 sanity |
| Starless Hymn | cantus sine stellis omnia devorat | Massive damage to all foes (forbidden) | Beat The Starved Bellwether |
| Blood Price | sanguis pro verbis meis | Damage that grows as your sanity falls, up to ×2.5 (forbidden) | Win a fight while Fraying |

Each healing spell cast in one fight restores 60% of what the last one did. Every spell that isn't a starter only shows up on a page. Forbidden spells also need you to read the page below 40 sanity.

## Relics

| Relic | Effect |
|---|---|
| Cracked Lens | Crits deal ×2.5 instead of ×2 |
| Ink of the Deep | Spells cost 25% less sanity |
| Moth-eaten Scarf | +0.7 s on every Defend word |
| Bone Charm | +20 maximum sanity |
| Black Candle | Pages read as if you had 15 less sanity |
| Quiet Bell | Foes wait 3 s longer before their first attack |
| Thorned Thimble | Deflects return all the damage, not half |
| Heartwood Splinter | Regain 8 more sanity after every fight |

## Art

| Art | Where it is used |
|---|---|
| `assets/Scene/*` | The forest in the woods, fights, campfires and menus (loaded through `scene.py`). Acts 2 and 3 tint it. |
| `assets/Sprites/Enemies/*` | Idle, hurt and attack rows (through `enemies.py`), plus the `*death*` sheets, which end in the dropped page |
| `assets/Sprites/MC (detailed)/the child spritesheet (no book).png` | The child's calm row with the grimoire painted out, for the opening before he finds it. Made from the main sheet by `tools/remove_book.py` (run it again if the sheet is re-exported). |
| `assets/Sprites/MC (detailed)/` | The child. The three rows are his Lucid, Uneasy and Fraying looks. His eye is recoloured in code as sanity falls (the eye boxes are listed in `art.py`). |
| `assets/Sprites/drops/` | The page on the reward screen, coloured by sanity |
| `assets/Sprites/Burning Spell Selection Parchment Sprite Sheet-2.png` | The parchment you choose a spell from (frame 0, stretched to the page), and the 6 frames of it burning when you burn the page (`art.parchment_frames`) |
| `assets/Sprites/Eight-Frame Enchanted Campfire Loop-1.png` | The campfire between acts, an 8-frame loop at 10 frames a second (`art.campfire_frames`) |
| `assets/Sprites/Enchanted thorn bramble hazard.png` | The thorn patches in the woods, drawn 1.4x wider than the part that hurts (`art.bramble_surface`) |
| `assets/Sprites/Blank Vined Pixel-Art HUD Frame.png` | The vined stone frame around every text box and menu (`ui.panel`). `tools/make_vine_frame.py` trims it and makes its inside see-through, writing `assets/Sprites/UI/vine_frame.png`; the game cuts that into 9 pieces so a box can be any size. Run the tool again if the frame is re-exported. |
| `assets/Sprites/Teal Rune Shrine Animation Atlas-2.png` | The shrines: waiting (rune faintly lit), the four frames that play when he prays (motes, a swirl, a ring of light), and spent (rune dark). The shrine's box in each cell is `art.SHRINE_BOX` |
| `assets/Sprites/Glowing Runic Stone Tablet.png` | The lore stones in the woods |
| `assets/Sprites/Blank Ancient Violet Stone Tablet-1.png` | The frame behind the words read from a lore stone (`ui.stone_panel`; every other box keeps the vine frame) |
| `assets/Sprites/Opening/Wake to Walk.png` | The boy waking, getting up and walking in the opening, before he has the grimoire (the boxes are in `art.OPENING_CELLS`) |
| `assets/Sprites/Death/Fading Boy with Purple Wisps.png` | The death scene (where he stands in each frame is in `art.UNRAVEL_CENTERS`) |

All text uses a medieval, blackletter-style pixel font drawn in code (`pixelfont.py`), with a black outline. Every letter is a grid of dots listed in that file, so no font file is needed.

Still drawn with shapes, with no painted art yet: platforms, motes, the casting circle and the spell bolts.

If a painted file is missing, the game falls back to a drawn stand-in.

## Music and sound

The music is five recorded tracks, all **CC0 (public domain)** from OpenGameArt, converted to OGG. Authors and links are in `assets/audio/CREDITS.md`.

| File | Plays during | Track |
|---|---|---|
| `music_woods.ogg` | Title, the woods, campfires, pages | "Cathedral in the forest" by congusbongus |
| `music_battle.ogg` | Ordinary fights | "Battle Theme" by Wolfgang_ |
| `music_boss.ogg` | Boss fights | "Boss Battle Music" by Juhani Junkala / SubspaceAudio |
| `stinger_defeat.ogg` | The death scene and its end screen | "Medieval: Defeat Theme" by RandomMind |
| `stinger_victory.ogg` | The escape | "Medieval: Victory Theme" by RandomMind |

When the scene changes, the old track fades out and the new one fades in. To swap a track, replace its file; if a file is missing a quiet drone plays instead.

The 45 sound effects are all generated in code by `sound.py`: key clicks that climb in pitch through a word, a different cast sound per element, blows, dodges and deflects, burnout, hexes, the bell's toll, a boss's rage, footsteps, jumps and landings, motes and shrines, menu sounds, scene fades, and a heartbeat while Fraying (30 sanity or below). A file named `assets/audio/sfx_<name>.wav` replaces the generated effect of that name.

## Code layout (course concepts)

| File | What it holds | Course topic |
|---|---|---|
| `main.py` | `Game`: window, clock, main loop, scene state machine with fades, the sanity bar, pause, screen shake, sanity effects | Game loop, dt capped at 0.05, finite state machine, render target + shake |
| `settings.py` | All tuning numbers | Named constants |
| `scene_menus.py` | Animated typed title, codex, how-to, name/seed/difficulty entry, the dawn choice, the death scene, end screens | Menus, animation over time, conditional rendering, `enumerate` |
| `scene_intro.py` | The opening scene: a list of timed beats with typed-out captions, and one beat that waits for the player to type | Scripted sequences, state machines, timers |
| `scene_explore.py` | Scrolling woods: camera, one-way platforms, enemy contact, hazards, shrines, gate | Screen scrolling, parallax, rect collision |
| `scene_combat.py` | Typing combat, defense prompts, projectiles | Event-driven input, timers, cooldowns |
| `scene_page.py` | Reading a boss page, choosing a spell from a page, crossing one out | Weighted random choices, menus with several stages |
| `scene_camp.py` | The campfire between acts | Menus with two modes |
| `entities.py` | `Player`, `MapEnemy`, `Particle`, `FloatingText`, `Projectile`, `Ring`, `RuneCircle`, `CombatEnemy` | Classes, Sprites and Groups, `kill()`, Vector2, particles |
| `art.py` | Loads the painted art, cuts the death sheets and the child, draws what has no art | Sprite sheets, alpha surfaces |
| `bestiary.py` | Real-time stats, traits, death-sheet rows and act pools for the creatures in `enemies.py` | Data tables |
| `enemies.py`, `sprites.py`, `scene.py` | The team's creature table, image helpers and parallax (shared with the prototypes) | Sprite sheets, masks, parallax |
| `pixelfont.py`, `ui.py` | The pixel font (every letter is a grid of dots) and the text, bar and panel helpers | Surfaces, caching |
| `sound.py` | Streams the music with fades between scenes; builds every sound effect from waves and noise | `pygame.mixer`, `pygame.mixer.music` |
| `words.py`, `typing_engine.py`, `spells.py`, `relics.py`, `lore.py`, `worldgen.py`, `run_state.py` | Game rules and text with no drawing | Separating logic from rendering |

## Tuning

* `settings.py`: sanity thresholds, the crit constant, the deflect window, Focus, thorn damage, sanity regained from shrines, motes, fights and campfires.
* `settings.py`, under **Burnout**, **Defend words** and **Scene changes**: how many casts burn a spell out and for how long, how much time a Defend word allows, and the fade length.
* `settings.py`, under **Sanity tiers**: where Lucid, Uneasy and Fraying begin, and how many letters Uneasy replaces.
* `settings.py`, under **Difficulty**: `FOE_HEALTH`, `FOE_DAMAGE`, `FOE_SPEED`, the exponential growth per act (`ACT_*_GROWTH`), heavy blows and boss rage. Lower the first three towards 1.0 for an easier game.
* `settings.py`, under **Unpredictable foes**, **Difficulty levels** and **Endless woods**: quick strikes, feints, flurries and how unevenly bars fill; the four levels; how much harder each endless act gets.
* `bestiary.py`: `STYLES` sets each creature's habits; `ACTS` sets how many groups roam each act and how big they are.
* `spells.py`: spell power and cost. `relics.py`: relics.
* `bestiary.py`: creature stats, traits, bosses and which creatures roam each act.
* `scene_combat.py` (top): how tall creatures are drawn in a fight and where they stand.
