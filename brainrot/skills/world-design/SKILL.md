---
name: world-design
description: Design the 3D world of a short explainer: the stations (one per idea), the pieces on each and the actions they perform, as data a generic renderer draws.
---

# Designing the world of a video

You are the art director of a short explainer shot in ONE continuous low-poly 3D world (soft pastel colours, rounded shapes, no cuts). The script is already written. Read it and design the
world: what the viewer sees for each idea, and what moves when. You describe the world as DATA in the requested JSON; you never write code. A later step directs the camera and locks the
actions to the narration words, so every action you define must show one clear moment of the story.

## Stations

- A station is a round stage about 16 units across, one per idea of the story, in the order the story tells them. One station is the **hero**: the world as a whole, shown first and last
  (a wide view where the video opens and closes). Use 4 to 9 stations in total, the hero included. Merge ideas rather than inventing filler stages.
- Give each station: a snake_case `id` (english, ascii), `title` and `note` (one sentence of what is on it) in the language of the narration, a `ground` (grass, sand, snow, stone, wood, water,
  soil, floor), `nouns` (1 to 14 lowercase single words that the narration says when this idea is being told; no word may serve two stations; skip generic words like "lentes" if the whole video
  is about them), `cutaway: true` on stations that open up a mechanism (a part seen in detail, a path of something, a measurement): at least three of them when the story has that many.
- Choose the hero as an establishing picture of the topic (for example a boardwalk for sunglasses, a savanna for zebras). It is wider: its pieces may spread up to 30 units sideways.

## Pieces

Coordinates: x to the right, y up from the stage floor, z toward the camera. A station keeps every piece within |x| <= 8 and |z| <= 8 (the hero: |x| <= 30, |z| <= 10) and 0 <= y <= 10. The camera looks
mostly from the front, so put the important pieces near z = 0 and never hide one behind another or let two overlap. Leave room: at most 12 pieces per station, and the key piece is the biggest and
the most detailed.

- Presets (`preset`): `person` (about 2 units tall; `color` = shirt, `color2` = skin; can `wear` glasses), `tree` (`color` leaves, `color2` trunk), `house` (`color` walls, `color2` roof),
  `animal` (a four-legged body, `color` body, `color2` markings), `bird` (`color` body, `color2` wings). A preset takes no `parts`.
- `custom`: compose a piece from 1 to 10 `parts` of: `box` (size = width, height, depth), `ball` (size = radii x, y, z; an ellipsoid), `cylinder`, `cone` and `disc` (size = radius, height,
  radius; a disc is a thin cylinder). A part has `pos` relative to the piece origin (the piece origin is at its base), `rot` in radians, `color` (#RRGGBB), `opacity` (0..1, for glass) and `glow` (0..1.5).
  A station has at most 48 parts in total. Stack parts to make recognisable objects: a lens is a thin `disc` rotated 1.5708 around z or x; a table is a flat box on four thin boxes.
- `scale` (0.2..4) resizes the whole piece; `rot_y` turns it; `hidden: true` starts it invisible (it must then `appear` in some action).
- Style: soft pastel palette, one saturated accent for the idea that matters most, light colours for the ground. No text on pieces. No two pieces interpenetrating.

## Framing (the camera is far away)

The camera looks at a stage from about 90 units and at the hero from about 70: a person at scale 1 (2 units tall) is a speck. Make what matters big and simple: on a station the key piece
spans at least 5 units, on the hero at least 8 (use `scale` up to 4, tall custom parts, a house or tree preset, a wide base platform that gives the hero a ground of its own). Keep important pieces
between y = 1 and y = 8 and near the centre; leave empty ground around them.

## Look (the low-poly recipe, mandatory)

- Soft, calm and flat in colour: pastel grounds and neutral objects (greys, off-whites, light woods). At most two different `ground` values in the whole world, three at the very most.
- One saturated **content colour** is the protagonist of the video (the thing the story is about: purple for ultraviolet, blue for water, amber for honey). Use it on the key pieces and rays and
  nowhere else; everything else stays pale or neutral.
- Red is reserved for force arrows and yellow for the on-screen term callouts, both added later by the director: never colour a ray red or yellow, and keep pieces away from saturated red or yellow
  unless the thing really is that colour (a sun, a fire). Flow or light that is not the content colour is white or pale grey.
- Rounded shapes; no textures, no text, no photoreal detail. Pieces never move on a loop: only through the actions you define.

## Actions and effects

Each station has 1 to 4 actions (the hero at least one; its first action opens the video, so make it the visual hook). An action is one moment of the story: `name` (snake_case), `frames`
(45 to 260 at 30 fps; 90 to 150 is typical), `text` (one sentence in the narration's language saying what the viewer sees and which words it matches) and 1 to 8 `effects`. An effect has a `type`,
the `piece` it acts on, and `start` and `end` as fractions (0..1) of the action:

- `appear` / `disappear`: the piece grows in or shrinks away.
- `move`: `vec` = offset [dx, dy, dz] the piece travels (within 14).
- `scale`: `vec` = target multipliers [sx, sy, sz] (0.02..6); use it for a bar that grows or a lens that swells.
- `color`: the piece turns `color`.
- `glow`: a soft pulse, `amount` 0..4.
- `spin`: turns around y, `amount` = number of turns.
- `ray`: a beam of light, `piece` left empty, from `vec` to `vec2` (both inside the stage), `color`, `amount` = thickness 0.03..0.5. It extends from start to end during the effect and stays.
- `wear`: a `person` puts glasses on, `color` = lens colour.

Rules: nothing moves unless an action says so; do not decorate with loops or wiggles. Effects in the same action may overlap in time only when they are meant to happen together. Keep each action
simple enough to describe in one sentence. A story about something being blocked shows the thing reaching a barrier and stopping (a `ray` that ends at the barrier, or a `move` that stops).

## Also return

- `title` and `setting` (one sentence describing the whole world).
- `glossary`: up to 12 terms from the script worth a yellow callout on screen (names, key words), copied as they are written.
- `motion_words`: stems of narration words that mean motion or flow in the script's language (for example "rebot", "atraviesa", "llega"), used to place rare arrows.

## Example (one station, abridged)

```json
{"id": "uv", "title": "Rayos ultravioleta", "note": "Rayos violetas llegan a una persona hasta que un cristal los frena", "ground": "stone",
 "nouns": ["ultravioleta", "rayos", "crookes"], "cutaway": true,
 "pieces": [{"id": "walker", "preset": "person", "pos": [5, 0, 0], "rot_y": -1.57, "color": "#E59C7C", "color2": "#EBC3A6"},
            {"id": "lens", "preset": "custom", "pos": [1.5, 3, 0], "hidden": true, "parts": [{"shape": "disc", "size": [2.2, 0.15, 2.2], "pos": [0, 0, 0], "rot": [0, 0, 1.5708], "color": "#F4E8A0", "opacity": 0.6}]}],
 "actions": [{"name": "rays_hit", "frames": 110, "text": "rayos violetas cruzan la escena hasta la persona", "effects": [{"type": "ray", "piece": "", "start": 0, "end": 1, "vec": [-6, 6, 0], "vec2": [5, 2.5, 0], "color": "#B48CFF", "amount": 0.12}]},
             {"name": "lens_blocks", "frames": 120, "text": "un cristal aparece y los rayos se detienen contra él", "effects": [{"type": "appear", "piece": "lens", "start": 0, "end": 0.4}]}]}
```

Return only the JSON for the whole world.
