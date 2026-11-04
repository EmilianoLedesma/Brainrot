# Low-poly cutaway recipe

A cookbook for a different look than `motion-graphics-recipe.md`: a 3D low-poly
product explainer where the hero object is shown mid-section, with a continuous
narration and hard cuts between a fixed set of shot types. Reverse-engineered
frame-by-frame from four reference videos (`@conrazon_es` on TikTok): a
windproof lighter, a ballpoint pen, a pressure cooker, and — the one that
started this — a moka pot. Nothing here is built yet; this is the spec to
build against, written the way `motion-graphics-recipe.md` documents its own
POCs. No reference footage, audio or channel artwork is copied into any
prototype — only the technique.

Status: derived from contact-sheet review (8 sheets, ~24 frames each, two
reference videos fully covered at ~0.7-0.9 fps). Nobody has built a POC yet.
Treat every timing number below as a starting hypothesis to test against a
first render, not a measured fact.

## The look

- Flat-shaded low-poly geometry (`MeshStandardMaterial({flatShading: true})`),
  no textures, no photoreal materials. Faceted surfaces are the point, not a
  limitation to hide.
- One saturated pastel background color per video (mint-green tiled wall +
  coral floor, or sky blue + wood desk) — never mixed, never more than two
  background colors in a single video.
- The object itself stays desaturated/neutral (grays, off-white) so it never
  competes with the background or the one saturated "content" color (purple
  gas, blue water, amber honey) that is always the visual protagonist of the
  shot.
- Red is reserved exclusively for force/direction indicators (arrows). Yellow
  is reserved exclusively for the on-screen term callout. Never use either for
  anything else.
- Captions: white bold sans, heavy black stroke, **no background pill** in the
  large majority of shots. This is the opposite default from
  `motion-graphics-recipe.md`'s dark rounded card — do not default to a card
  here.

## Ingredients

Build on `@remotion/three` (React Three Fiber), new to this repo — no POC has
used it yet. `npx remotion add @remotion/three`. Everything inside
`<ThreeCanvas>`, animation only via `useCurrentFrame()` (never `useFrame()`,
it flickers on render). Ambient light low (~0.4-0.5) + one directional light
from high-side angle for hard-edged low-poly shadows.

| Primitive | Used for |
| --- | --- |
| Procedural geometry (cylinders, cones, flattened cones, deformed icosahedrons) | every object in the first POCs — skip `.glb` imports until the style is validated |
| `InstancedMesh` | granular fill content (coffee grounds, chickpeas) — hundreds of small irregular meshes, must be instanced or it will not render in time |
| Clipped/half geometry (model only the visible half, do not use a runtime clipping plane) | the cutaway itself |
| Deterministic noise (seed by index, drive with frame, not `Math.random()`) | flame flicker, puff drift, idle wobble |
| A small `<WordCaption>` overlay in screen space (outside `<ThreeCanvas>`, plain DOM/SVG text with `-webkit-text-stroke` or a stroke filter) | captions — these are 2D overlays on top of the 3D canvas, not 3D text |

## Shot grammar — four types, cut hard between them

This is the single most important finding: the camera does **not** orbit one
continuous composition. It cuts between four fixed shot types on narration
beats (roughly every 2-4 words). Build each as a separate `<Sequence>` with
its own camera position, not as one camera path with keyframes.

1. **Establishing** — the whole product, no cutaway, in its full context (the
   closed pot on the stove; the complete lighter in the box). Opens and
   sometimes closes the video.
2. **Cutaway interior** — the hero shot. Half the object is modeled away,
   camera holds on the exposed cross-section. Most of the runtime lives here.
3. **Insert macro** — an extreme close-up of one small isolated part against a
   near-empty background (the valve pin alone, the spring alone, the pen tip
   alone). No surrounding context. Use this to land a single technical term.
4. **Metaphor cutaway** — a cutaway of something that is *not* the product,
   used to illustrate a real-world effect or a worst-case/safety point (a
   human face cut away at the brow to show a frown mechanism; a child's throat
   in cross-section showing a swallowed cap). Rare — one per video at most,
   reserved for the most dramatic beat.

## Recipe

1. **Pick the hero object and model only its cutaway half.** Do not build the
   full solid and clip it at render time; model the half-geometry directly so
   silhouette edges stay clean low-poly facets, not a flat clip-plane seam.
2. **Write the script as JSON first**, same discipline as the vector recipe:
   `duration`, a `shots` array (`type: establishing|cutaway|insert|metaphor`,
   `start`, `end`, camera position/target), a `captions` array (`at`, `until`,
   `text`, `style: word|term`), an `events` array (see below), and a
   `sources` list. The component only interprets the script.
3. **Ambient motion runs inside every held shot, independent of events** — the
   fill level/line rises continuously across consecutive words (not a loop:
   it progresses with the narration), steam/smoke clusters are born small and
   keep accumulating, a flame never stops flickering. If nothing else is
   scripted for a shot, this is still happening.
4. **Script discrete events, each locked to one spoken word**, same pattern as
   `brainrot/motion.py`'s `_cue_time`: an inward-squeezing pair of red arrows
   on a pressure/compression word; a gust of white puff-clouds entering from
   one side with a direction arrow on a wind word; a downward arrow + object
   depresses on a "press/firm" word; an odometer-style stat that **hard-cuts**
   to a new number on the beat (never tweens — a value flip, not a count-up);
   a small macro insert where a part visibly latches/locks on its own word.
5. **Reserve one indicator that escalates across several beats**, distinct
   from the hard-cut counters above: a stack of upward arrows that grows in
   count and height over 3-4 consecutive beats as pressure/intensity builds
   narratively. This is the one place smooth progression belongs.
6. **The payoff transformation is a state change on the hero object itself**,
   not a new object: the flame changes shape and color when the windproof
   cage engages; the pot's valve pin visibly rises as the indicator. Never cut
   away from the object to show the "answer" — the object becomes the answer.
7. **Captions**: one short phrase per shot, white bold with heavy black
   stroke, no background box, positioned near but never over the hero object.
   A secondary yellow/gold term callout (same stroke style, larger) appears
   below it only on an insert or cutaway shot that is naming a part, and holds
   one beat longer than the primary caption. A dark rounded pill with white
   bold text is reserved for data badges only (temperature, elapsed time,
   distance, a running count) — never for narration text.
8. **Stat badges attach to the object, not the frame corner** — "118°C",
   "11 min" sit near the part they describe and update in place as the shot
   continues, they do not live in a fixed HUD position.

## Gotchas to test for (hypotheses, not yet confirmed in this repo)

- `InstancedMesh` for granular fill (coffee grounds, chickpeas) needs a fixed
  instance count decided at script-write time; do not grow the instance count
  at runtime mid-shot.
- A hard-cut stat flip (884 → 3.000) will look like a bug if accidentally
  interpolated — make sure nothing wraps it in `interpolate()`.
- The four shot types need their own camera rigs; reusing one camera object
  across shot types will carry unwanted FOV/position state between cuts.
- Deterministic flicker (flame, puffs) must be seeded per-instance by index,
  not by frame alone, or every flame triangle will flicker in lockstep.

## What a POC needs before this is more than a spec

1. Build one shot type at a time, starting with "cutaway interior" alone
   (highest-value shot, most of the runtime), before attempting all four.
2. A 10s test exercising ambient motion + one hard-cut event + one escalating
   indicator, rendered and checked as a contact sheet, before adding the
   insert/metaphor shot types.
3. Decide instancing limits for granular fill by testing render time on this
   machine, not by guessing a count.
4. Once validated, this follows the same six-step integration path as
   `motion-graphics-recipe.md`: move primitives into `motion/`, model/script
   JSON split, load as a skill, automatic contact-sheet review step.

## Reference

Four TikTok videos from `@conrazon_es`, analyzed frame-by-frame (not stored in
this repo — technique only, no footage copied): a windproof lighter
("cortavientos"), a ballpoint pen cutaway, a pressure cooker, and a moka pot
(the original reference image this recipe was requested from).
