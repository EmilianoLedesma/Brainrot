# Low-poly cutaway recipe

A cookbook for a different look than `motion-graphics-recipe.md`: a 3D low-poly
product explainer where the hero object is shown mid-section, with a continuous
narration and hard cuts between a fixed set of shot types. Reverse-engineered
frame-by-frame from reference videos: four from `@conrazon_es` on TikTok (a
windproof lighter, a ballpoint pen, a pressure cooker, and — the one that
started this — a moka pot), plus a fifth from a different channel (a bridge
explainer: vigas, pilares, socavación, junta de dilatación) that confirmed the
same grammar on a different topic. No reference footage, audio or channel
artwork is copied into any prototype — only the technique.

Status: no longer a pure hypothesis. Two of this repo's own renders have been
reviewed frame-by-frame against this recipe — a 10s silent "why the sky is
blue" POC, and a 93.65s silent "why aluminum foil has two sides" full test —
and both exposed real gaps, listed below with what each one proved. Treat the
rest of the document as validated; treat anything still marked a hypothesis as
genuinely untested.

## Lessons from test renders (read this before building)

These are not style opinions — they are specific defects found by reviewing
actual rendered output, several of which were already flagged once and did
**not** get fixed on the next pass. Each is now a hard requirement below, not
a suggestion.

- **The caption system kept reverting to the wrong one, twice.** Both the
  sky-blue POC and the full aluminum-foil render used *sentence accumulation*
  (text grows word by word into a full sentence, e.g. "El papel aluminio" →
  "...puede verse distinto" → "...por cada lado") instead of short-phrase
  *replacement*. This was called out as a blocking bug after the first test
  and still shipped unchanged in the second. Whatever implements captions
  must make sentence-accumulation structurally impossible, not just
  documented against — see "Captions" below for the exact rule.
- **Held shots render as literally identical frames when no event is
  scripted.** Not "static-feeling" — bit-for-bit the same image repeated for
  the shot's full duration (confirmed on the foil render's opening 14.9s
  establishing shot and its block-4 insert shot). A soft guideline
  ("ambient motion should run") is not enough; it must be a required,
  non-null field in the shot script, checked before render.
- **Zero camera movement anywhere in the full-length test.** Every shot was a
  locked-off camera for the entire 93.65s. All five reference videos — the
  four original ones and the bridge video — have continuous, slow camera
  motion (orbit, push, or pan) even in establishing shots. This was never
  written down as a requirement; it is now one.
- **The background was two flat color planes and nothing else.** No secondary
  objects, no texture, no sense of a place — the hero object read as floating
  in a void. The reference videos always layer in 2-3 environmental elements
  (water, trees, soil, a counter, a stove). This needs to be a minimum, not
  an aspiration.
- **When a shot does get real device/event treatment, it works.** The foil
  render's rolling-mill shot (red compress-arrows flattening a slab, then two
  slabs merging and feeding through a pair of rollers) was legible and well
  executed — proof this is a specification gap in the other shots, not a
  model-capability ceiling. Do not read "deplorable video" as "the model
  can't do this"; read it as "most shots got no event spec at all."
- **The one fix that did land, landed cleanly.** The yellow callout term and
  the previously-empty block were both fixed correctly on request (the
  callout became "RODILLOS"; the empty block got a real curling-sheet event).
  Confirms the loop works when a fix is unambiguous and mechanical — the
  caption system did not land because the instruction described a visual
  result ("short replacement, not accumulation") without pinning down *where
  in the code* that behavior is decided. Future fix requests for this recipe
  should name the exact script field or component responsible, not just the
  visible symptom.

## The look

- Flat-shaded low-poly geometry (`MeshStandardMaterial({flatShading: true})`),
  no textures, no photoreal materials. Faceted surfaces are the point, not a
  limitation to hide. This applies to **every** mesh in the shot, including
  particles and event effects (see Gotchas) — a flat 2D sprite dropped into an
  otherwise flat-shaded 3D scene reads as a compositing mistake.
- One saturated pastel background color per video (mint-green tiled wall +
  coral floor, or sky blue + wood desk) — never mixed, never more than two
  background colors in a single video.
- The object itself stays desaturated/neutral (grays, off-white) so it never
  competes with the background or the one saturated "content" color (purple
  gas, blue water, amber honey) that is always the visual protagonist of the
  shot.
- Three reserved indicator colors, never used for anything else and never
  mixed with each other:
  - **Red** — force/direction/pressure (arrows showing a push, a compression,
    a load).
  - **Yellow** — the on-screen technical-term callout, and only that (name
    the real mechanism part — "rodillos", "pilares" — never a generic word
    like "superficie").
  - **Neutral gray/white** — flow or current direction, distinct from force:
    small chevrons or short arrows showing water/air/material moving past or
    around something (confirmed in the bridge reference's under-water
    scour shot). Use this instead of red when nothing is being pushed or
    compressed, only carried or flowing.
- Captions: white bold sans, heavy black stroke, **no background pill** in the
  large majority of shots. This is the opposite default from
  `motion-graphics-recipe.md`'s dark rounded card — do not default to a card
  here. See "Captions" below for the exact behavior — this is the rule that
  has broken twice.

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

## Camera (mandatory — not optional, not covered by object-level motion)

No shot in this recipe is ever a locked-off camera, regardless of how much the
object itself is animating. Every `<Sequence>` needs its own slow, continuous,
frame-driven camera motion:

- **Establishing** — a slow orbit (a few degrees over the shot's duration) or
  a slight push-in. Never a still frame even though nothing else may be
  scripted here.
- **Cutaway interior** — a slow push or a very small orbit around the cross-
  section, enough to read as "alive," not enough to disorient.
- **Insert macro** — the smallest motion of the four, but still present: a
  tiny push or drift, because this is usually the longest-held shot per word
  of narration and the one most likely to look frozen.
- **Metaphor** (when used) — matches whichever of the above it visually is.

Camera position/target are frame-driven (`interpolate` against
`useCurrentFrame()`), computed once per shot type, never reused wholesale
across shot types — carrying one shot's camera rig into another leaks FOV or
position state.

## Shot grammar — up to four types, cut hard between them

The camera does **not** orbit one continuous composition across unrelated
subjects, and shots do not blend into each other — hard cuts, same convention
as `brainrot/motion.py`'s scene cuts. Build each as a separate `<Sequence>`
with its own camera position, not as one camera path with keyframes. A video
can also stay on a single real subject the entire time, cutting only between
angles of *that* subject (confirmed by the bridge reference, which never
leaves the one bridge) — that is a valid use of this grammar, not a
simplification of it.

1. **Establishing** — the whole product, no cutaway, in its full context (the
   closed pot on the stove; the complete lighter in the box; a bridge seen
   from the riverbank). Opens and sometimes closes the video.
2. **Cutaway interior** — the hero shot. Half the object is modeled away,
   camera holds on the exposed cross-section. Most of the runtime lives here.
3. **Insert macro** — an extreme close-up of one small isolated part against a
   near-empty background (the valve pin alone, the spring alone, the pen tip
   alone, the expansion joint's interlocking plates alone). No surrounding
   context. Use this to land a single technical term.
4. **Metaphor cutaway** (optional, topic-dependent) — a cutaway of something
   that is *not* the product, used to illustrate a real-world effect or a
   worst-case/safety point (a human face cut away at the brow to show a frown
   mechanism; a child's throat in cross-section showing a swallowed cap).
   Skip this entirely when the real mechanism is already concrete and
   visualizable without an analogy — the bridge reference uses zero metaphor
   shots and is not weaker for it. When used, it is rare: one per video at
   most, reserved for the most dramatic beat.

## Recipe

1. **Pick the hero object and model only its cutaway half.** Do not build the
   full solid and clip it at render time; model the half-geometry directly so
   silhouette edges stay clean low-poly facets, not a flat clip-plane seam.
2. **Write the script as JSON first**, same discipline as the vector recipe:
   `duration`, a `shots` array (`type: establishing|cutaway|insert|metaphor`,
   `start`, `end`, camera position/target — see Camera above, this field is
   required and may not be a fixed/static value), a `captions` array (see
   Captions below), an `events` array (see below), an `ambient` field per
   shot (see point 3, required, non-null), and a `sources` list. The
   component only interprets the script.
3. **Ambient motion is a required field on every shot, not a fallback
   behavior.** The script must name it explicitly — e.g.
   `ambient: {kind: "fill-rise" | "flame-flicker" | "surface-sheen" |
   "idle-wobble", ...params}` — and the renderer should treat a missing or
   null `ambient` field as a build-time error, not a silently static shot.
   The fill level/line rises continuously across consecutive words (not a
   loop: it progresses with the narration), steam/smoke clusters are born
   small and keep accumulating, a flame never stops flickering, water/metal
   surfaces carry a slow-moving sheen highlight. This runs independent of
   any scripted event, every single shot, no exceptions — this is the rule
   that produced bit-for-bit static frames when treated as optional.
4. **Every establishing and cutaway shot needs at least 2-3 environmental
   elements beyond the hero object** (e.g. water + riverbank + trees; stove +
   counter + a second kitchen object) so the subject reads as being somewhere,
   not floating against two flat color planes. An insert/macro shot is the
   one exception — near-empty background is correct there by design.
5. **Script discrete events, each locked to one spoken word**, same pattern as
   `brainrot/motion.py`'s `_cue_time`: an inward-squeezing pair of red arrows
   on a pressure/compression word; a gust of white puff-clouds entering from
   one side with a direction arrow on a wind word; a downward arrow + object
   depresses on a "press/firm" word; an odometer-style stat that **hard-cuts**
   to a new number on the beat (never tweens — a value flip, not a count-up);
   a small macro insert where a part visibly latches/locks on its own word;
   gray/white flow chevrons for a current or scouring effect (see The Look).
6. **Reserve one indicator that escalates across several beats**, distinct
   from the hard-cut counters above: a stack of upward arrows that grows in
   count and height over 3-4 consecutive beats as pressure/intensity builds
   narratively. This is the one place smooth progression belongs.
7. **The payoff transformation is a state change on the hero object itself**,
   not a new object: the flame changes shape and color when the windproof
   cage engages; the pot's valve pin visibly rises as the indicator. Never cut
   away from the object to show the "answer" — the object becomes the answer.
8. **Captions — exact behavior, no exceptions:** each caption is a short
   phrase (roughly 2-5 words) that fully **replaces** the previous one; it is
   never built by appending words to what is already on screen, and it never
   grows into a full sentence. The script's `captions` array holds complete,
   independent phrase strings with their own `at`/`until`, not word tokens
   meant to be concatenated — if the generator only has word-by-word narration
   timing, it must group words into phrase-sized captions *before* writing the
   script, not render them incrementally. White bold with heavy black stroke,
   no background box, positioned near but never over the hero object. A
   secondary yellow/gold term callout (same stroke style, larger) appears
   below it only on an insert or cutaway shot that is naming a part, and holds
   one beat longer than the primary caption. A dark rounded pill with white
   bold text is reserved for data badges only (temperature, elapsed time,
   distance, a running count) — never for narration text. An optional
   onomatopoeia layer (e.g. "TAC, TAC" for a mechanical bump) may appear in
   the yellow callout style, synced to a scripted event rather than to
   narration — it is a sound-effect graphic, not a caption, and must never
   replace or merge with the phrase caption that is active at the same time.
9. **Stat badges attach to the object, not the frame corner** — "118°C",
   "11 min" sit near the part they describe and update in place as the shot
   continues, they do not live in a fixed HUD position.
10. **Vary cheap secondary details between repeated beats** — if a secondary
    object recurs across several shots (a car crossing a bridge, a container
    passing through a process), change a trivial attribute each time (its
    color) so repetition doesn't read as a looped asset. Low cost, confirmed
    useful in the bridge reference.

## Gotchas to test for

- `InstancedMesh` for granular fill (coffee grounds, chickpeas) needs a fixed
  instance count decided at script-write time; do not grow the instance count
  at runtime mid-shot.
- A hard-cut stat flip (884 → 3.000) will look like a bug if accidentally
  interpolated — make sure nothing wraps it in `interpolate()`.
- The four shot types need their own camera rigs; reusing one camera object
  across shot types will carry unwanted FOV/position state between cuts.
- Deterministic flicker (flame, puffs) must be seeded per-instance by index,
  not by frame alone, or every flame triangle will flicker in lockstep.
- Keep every particle/event effect in the same flat-shaded 3D material as the
  hero geometry — a 2D sprite particle in an otherwise 3D flat-shaded scene is
  an immediate visual inconsistency (seen in the sky-blue POC's event
  particles).
- A caption or event pipeline driven by raw per-word TTS timing will tend
  toward word-by-word accumulation unless phrases are explicitly grouped
  before scripting — this is exactly how the accumulation bug reappeared
  after being flagged once already.

## What a POC needs before this is more than a spec

1. Build one shot type at a time, starting with "cutaway interior" alone
   (highest-value shot, most of the runtime), before attempting all four.
2. A 10s test exercising camera motion + ambient motion + one hard-cut event
   + one escalating indicator, rendered and checked as a contact sheet,
   before adding the insert/metaphor shot types.
3. Decide instancing limits for granular fill by testing render time on this
   machine, not by guessing a count.
4. Once validated, this follows the same six-step integration path as
   `motion-graphics-recipe.md`: move primitives into `motion/`, model/script
   JSON split, load as a skill, automatic contact-sheet review step.

## Reference

Four TikTok videos from `@conrazon_es`, analyzed frame-by-frame (not stored in
this repo — technique only, no footage copied): a windproof lighter
("cortavientos"), a ballpoint pen cutaway, a pressure cooker, and a moka pot
(the original reference image this recipe was requested from). A fifth video,
from a different channel, covering a bridge explainer (vigas, pilares,
socavación, junta de dilatación), confirmed the grammar holds on a
single-subject, multi-angle video with no metaphor shot.