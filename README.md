# Spell Typer

*A lost boy, a dark wood, and a grimoire that lies.*

A 2D roguelike for CPSC 4160/6160. You walk the painted woods, and when a creature catches you, you fight by **typing incantations**. Your **sanity** changes the words you must type, the boy's look, and the pages you collect.

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
| Woods | Arrows or A/D to walk · Space/W/Up to jump (over thorns, up to the lights) · S/Down to drop through a platform · E to pray at a shrine or read a stone · Enter at the gate to fight the boss · Esc to pause |
| Combat | Type a spell's incantation to cast it (no Enter needed) · Tab or Left/Right to switch target · Backspace to cancel the spell · Esc to pause |
| Pages and campfires | Up/Down and Enter, or press a number |
| Codex | Left/Right to turn the page · Esc to go back |

## How it plays

* **Three acts:** The Whispering Woods, The Hollow Marsh and The Starless Grove. Each is a side-scrolling stretch of the forest with creatures on the path, shrines, lore stones and a boss gate you enter when you are ready. The woods are generated from a seed you can type in.
  * **Thorns** cost 6 health if you walk into them, so jump them.
  * **Motes of light** on platforms and in the air give +3 sanity each.
* **Typing combat, inspired by Typing of the Dead:** your grimoire's spells are listed at the bottom of the screen.
  * The first letters you type pick the spell. After that, a wrong key counts as a mistake and does not move you forward.
  * **Damage = spell strength × accuracy².** Strength = power per letter × number of letters × level bonus × page potency, so **longer incantations hit harder**.
  * **Crit chance is inversely proportional to typing speed:** chance = 1 ÷ (letters per second), clamped to 5–50%. Careful typing earns crits, but the enemies' attack bars keep filling while you take your time.
* **Focus:** every cast at 95%+ accuracy adds a point of Focus, up to 5. Each point adds +8% to every spell. A cast below 80% accuracy, or any blow that lands on you, resets it.
* **Sanity**
  * **70 or more (Lucid):** words are spelled correctly.
  * **Below 70:** 10–55% of the letters are replaced. You type what you see.
  * **Below 15 (Mad):** the words become garbled nonsense.
  * **0:** your mind is gone and the run ends.

  Sanity falls when you cast spells, when attacks land, and when a boss rages. It comes back from shrines, motes, the Clarity spell, burning a page, and a breath after each fight. As it drops the screen darkens, the letters jitter, whispers drift past, and the boy changes to his violet and then crimson look.
* **Defense:** when an enemy's attack bar fills, it rears up and a DEFEND word appears.
  * Type it in time to **dodge**.
  * Type it before the marker line at 90%+ accuracy to **deflect** half the damage back.
  * Get halfway through and you're **grazed** for half damage.
  * **Every third attack of a creature is a HEAVY blow:** its attack bar turns magenta beforehand, the word is one step harder, and it deals 1.5× damage.
  * **The lower your health, the harder the words:** short words above 66% health, longer words between 33% and 66%, phrases below 33%, and phrases with misspelled letters below 15%.
* **Pages, like Balatro's boss blinds:**
  * A dying creature dissolves into a page (its death sheet plays). Bosses drop a full page, ordinary fights a scrap.
  * **The lower your sanity when you read it,** the higher its potency (up to ×1.9), the more spells you can choose from (up to 6), and below 40 sanity forbidden spells appear. The page is cyan when you are calm, violet when shaken, crimson when mad.
  * Picking a spell you already own empowers it by one level. You can also burn the page for +20 sanity.
* **Campfires:** after the first and second boss you pick one: heal 40 health and 30 sanity, raise one spell by a level, or take one of two relics.
* **Score, codex, permadeath:** each run ends with a score and the best is saved. The codex on the title menu lists every spell (and how to unlock the sealed ones), relic and trait. Death resets your grimoire; unlocked spells are kept in `save.json`.

## Creatures

| Creature | Where | Trait |
|---|---|---|
| Moth Choir | All acts | **STARE:** drains sanity for as long as it lives |
| Mire Maw | All acts | **DRINK:** heals by the damage it deals to you |
| Lantern Stag | Acts 2–3; boss of act 1 | **HEX:** a blow that lands scrambles one of your spells until you cast it |
| Rootbound Pilgrim | Act 3; boss of act 2 | **GRASP:** its attacks never use the short DEFEND words |
| Starved Bellwether | Boss of act 3 | **TOLL:** sometimes rings its bell instead of striking, which costs 4 sanity and scrambles a spell |

## Spells

| Spell | Incantation | Effect | Unlock |
|---|---|---|---|
| Ember | ignis | Damage | Starter |
| Ward | aegis fortis | Shield | Starter |
| Frost Needle | glacies acus | Damage + delays the target's attack | Available from the start |
| Spark Lash | fulgur verbera | Damage | Available from the start |
| Mend | sana vulnus meum | Heal | Available from the start |
| Clarity | mens clara manet | Restore sanity | Available from the start |
| Hex of Rot | putresce caro mortalis | Damage over 6 s | Available from the start |
| Bone Spear | os hasta perforat | Heavy damage | Available from the start |
| Whisper Pact | foedus susurri in tenebris | Trade sanity for HP | Available from the start |
| Soul Drain | anima tua mihi exhauritur | Damage, heals for half | Beat The Lantern Stag |
| Chain Lightning | tonitrus catena saltat | Hits all foes | Beat The Rootbound Pilgrim |
| Hourglass Rend | clepsydra frangitur | Delays every foe's attack | Beat The Rootbound Pilgrim |
| Thorn Cage | spinae te claudunt | Damage + delays the target 3 s | Deflect 8 attacks in one run |
| Grimoire Flare | lumen lucernae exardescit | Hits all foes | Cast 40 spells in one run |
| Final Word | verbum ultimum | Double damage to a foe below 30% health | Cast a 20+ letter incantation at 100% accuracy |
| Black Sun | sol niger ardet in me | Huge damage (forbidden) | Available from the start |
| The Gate's Gaze | oculus ultra portam aperitur | Massive damage (forbidden) | Win a fight while Mad |
| Starless Hymn | cantus sine stellis omnia devorat | Massive damage to all foes (forbidden) | Beat The Starved Bellwether |

Every spell that isn't a starter only shows up on a page. Forbidden spells also need you to read the page below 40 sanity.

## Relics

| Relic | Effect |
|---|---|
| Cracked Lens | Crits deal ×2.5 instead of ×2 |
| Ink of the Deep | Spells cost 25% less sanity |
| Moth-eaten Scarf | +0.7 s on every DEFEND word |
| Bone Charm | +25 maximum health |
| Black Candle | Pages read as if you had 15 less sanity |
| Quiet Bell | Foes wait 3 s longer before their first attack |
| Thorned Thimble | Deflects return all the damage, not half |
| Heartwood Splinter | Heal 8 health after every fight |

## Art

| Art | Where it is used |
|---|---|
| `assets/Scene/*` | The forest in the woods, fights, campfires and menus (loaded through `scene.py`). Acts 2 and 3 tint it. |
| `assets/Sprites/Enemies/*` | Idle, hurt and attack rows (through `enemies.py`), plus the `*death*` sheets, which end in the dropped page |
| `assets/Sprites/MC (detailed)/` | The child. The three rows are his calm, shaken and mad looks. |
| `assets/Sprites/drops/` | The page on the reward screen, coloured by sanity |

All text uses a pixel font drawn in code (`pixelfont.py`), with a black outline, so it matches the pixel art and needs no font file.

Still drawn with shapes, with no painted art yet: platforms, thorns, motes, shrines, lore stones, the boss gate, the campfire, and the child's death (he tips over and fades). All sound is synthesized in `sound.py`; `assets/music.ogg` or `assets/sfx_<name>.wav` replace it if present.

If a painted file is missing, the game falls back to a drawn stand-in.

## Code layout (course concepts)

| File | What it holds | Course topic |
|---|---|---|
| `main.py` | `Game`: window, clock, main loop, scene state machine, HUD, pause, screen shake, sanity effects | Game loop, dt capped at 0.05, finite state machine, render target + shake |
| `settings.py` | All tuning numbers | Named constants |
| `scene_menus.py` | Title (with volume), codex, how-to, name and seed entry, end screens | Menus, conditional rendering, `enumerate` |
| `scene_explore.py` | Scrolling woods: camera, one-way platforms, enemy contact, hazards, shrines, gate | Screen scrolling, parallax, rect collision |
| `scene_combat.py` | Typing combat, defense prompts, projectiles | Event-driven input, timers, cooldowns |
| `scene_page.py` | Choosing a spell from a page | Weighted random choices |
| `scene_camp.py` | The campfire between acts | Menus with two modes |
| `entities.py` | `Player`, `MapEnemy`, `Particle`, `FloatingText`, `Projectile`, `CombatEnemy` | Classes, Sprites and Groups, `kill()`, Vector2, particles |
| `art.py` | Loads the painted art, cuts the death sheets and the child, draws what has no art | Sprite sheets, alpha surfaces |
| `bestiary.py` | Real-time stats, traits, death-sheet rows and act pools for the creatures in `enemies.py` | Data tables |
| `enemies.py`, `sprites.py`, `scene.py` | The team's creature table, image helpers and parallax (shared with the prototypes) | Sprite sheets, masks, parallax |
| `pixelfont.py`, `ui.py` | The pixel font (every letter is a grid of dots) and the text, bar and panel helpers | Surfaces, caching |
| `sound.py` | Synthesized sound effects and a looping drone | `pygame.mixer` |
| `words.py`, `typing_engine.py`, `spells.py`, `relics.py`, `worldgen.py`, `run_state.py` | Game rules with no drawing | Separating logic from rendering |

## Tuning

* `settings.py`: sanity thresholds, the crit constant, the deflect window, Focus, thorn damage, campfire healing.
* `settings.py`, under **Difficulty**: `FOE_HEALTH`, `FOE_DAMAGE`, `FOE_SPEED`, growth per act, heavy blows and boss rage. Set the first three to 1.0 for the earlier, easier game.
* `spells.py`: spell power and cost. `relics.py`: relics.
* `bestiary.py`: creature stats, traits, bosses and which creatures roam each act.
* `scene_combat.py` (top): how tall creatures are drawn in a fight and where they stand.
