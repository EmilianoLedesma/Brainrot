# Low-poly cutaway recipe

A cookbook for a different look than `motion-graphics-recipe.md`: a 3D low-poly
product explainer where the hero object is shown mid-section, with a continuous
narration and hard cuts between a fixed set of shot types. Reverse-engineered
frame-by-frame from reference videos: four from `@conrazon_es` on TikTok (a
windproof lighter, a ballpoint pen, a pressure cooker, and — the one that
started this — a moka pot), a fifth from a different channel (a bridge
explainer: vigas, pilares, socavación, junta de dilatación) that confirmed the
same grammar on a different topic, and a sixth from yet another channel
(`@construlandai`, a mountain-tunnel construction explainer) that exposed a
fluidity gap none of the others had surfaced — see "Sustained motion" below —
and a seventh (`@stupydoo`, a tree-house construction explainer, 164s) that
was reviewed at much higher frame density specifically to extract camera and
object-motion technique, confirming and refining the sustained-motion rule —
see "Two valid ways to sustain a shot" below.
No reference footage, audio or channel artwork is copied into any prototype —
only the technique.

Status: no longer a pure hypothesis. Four of this repo's own renders have
been reviewed frame-by-frame against this recipe — a 10s silent "why the sky
is blue" POC, a 93.65s silent "why aluminum foil has two sides" full test, a
10s silent "how a deadbolt lock works" POC built specifically to test the
camera/caption/environment fixes, and a 146.97s silent "how a car's shock
absorber works" full test (run with `BRAINROT_CLAUDE_MODEL=claude-opus-5-5`,
confounded with a model-upgrade experiment — see below) — each exposed or
confirmed something, listed below. The deadbolt test was the first one to
pass clean on camera motion, captions, environment and color. The shock-
absorber test confirmed the sustained-motion fix (the piston's continuous
oscillation is genuinely good) but surfaced two new gaps: object motion was
used as an excuse to skip camera motion entirely in the long cutaway hold,
and — the bigger one — one graphic composition was held for 20-30+ seconds
while the script named several parts that never got their own visual moment,
producing a video with far less visual variety than any reference despite
technically following the per-shot rules. Treat the rest of the document as
validated; treat anything still marked a hypothesis as genuinely untested.

**On the Opus 5.5 confound:** this test changed the model and the recipe at
the same time, so a clean result would not have told us which one to credit.
The script this run was noticeably stronger (clear hook, no repeated premise,
earned callback) than the foil script, but attribute that cautiously — it
could be the model, or ordinary variance between generations. Re-run the same
topic on the default model before concluding Opus 5.5 is why the script was
better.

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
- **The camera/caption/environment fixes landed cleanly on the first try.**
  The deadbolt-lock POC was checked by comparing specific full-resolution
  frames, not just a thumbnail contact sheet, and confirmed: a real push-in
  over the establishing shot, phrase-replacement captions with no
  accumulation, a richer establishing environment (door + frame + wall +
  floor), correct red/yellow color discipline, and — notably — real geometry
  progression *during* a single held caption, not only at cut points (the
  key-bitting profile visibly forms while "La llave empuja los pines" stays
  on screen). This confirms these fixes were specified concretely enough to
  implement correctly; contrast with the caption bug above, which was not.
- **Sustained motion is a different, higher bar than "not static," found from
  a sixth reference video (`@construlandai`, a tunnel-construction
  explainer).** Frame-by-frame inspection at 6fps (not just 1fps) showed two
  things this recipe had not yet asked for: (1) a tool or mechanism performs
  a complete, legible, *repeating* work cycle for the full duration of a held
  shot — a pickaxe swings and strikes repeatedly with rock-chip particles on
  every impact, not once — rather than a single idle wobble; (2) the
  underlying scene motion (a tunnel-boring machine's continuous forward
  travel through the rock, in that reference) runs as **one continuous move
  sustained across many caption changes**, decoupled from the faster
  word-level caption rhythm on top of it. The deadbolt POC's within-shot
  geometry change is a step toward this (point 2 above) but is a one-time
  progression, not yet a sustained repeating cycle — treat that as the next
  thing to test, not a new failure.
- **The model question is closed: the gap was prompt specificity, not
  capability.** A controlled planner test ran the same `words.json` through
  Opus 5.5 and the default model twice each, first against the v1 planner
  prompt (which never stated the max-hold cap or a per-noun rule), then
  against a v2 prompt that stated both explicitly. Under v1, the default
  model leaked reasoning text into output fields, returned empty "none"
  events on 2-4 of 12 blocks despite being told not to, and both models blew
  past the (unstated) 10s cap by 68-99 seconds. Under v2, both models scored
  identically: zero cap violations, 11/11 nouns acknowledged, zero
  placeholders, zero validator corrections. Conclusion: do not reach for a
  more expensive model to fix a planning defect before checking whether the
  defect is actually an unstated rule — this recipe's own planning bugs
  (the cap, noun coverage) were exactly that twice in a row now (the caption
  bug earlier was the same pattern, a different symptom).
- **Red force-arrows get used as filler once a model is told to acknowledge
  every noun within a time cap, found from the v2 planner test.** 19-21 of
  32-36 events across four plans were `force_arrows`, several on words with
  no actual force or direction ("importa", "largo") — the model reaches for
  the arrow as a generic default when it needs *some* event to satisfy the
  cap/coverage rules and nothing better comes to mind. This breaks the
  red-is-exclusively-force rule from The Look. Fix: give the event vocabulary
  a neutral option for "just acknowledge this part was mentioned," borrowed
  from the schematic-world recipe's UI-select highlight (a brief outline or
  pulse on the part, no color implying force or flow) — see the new `highlight`
  event kind below. Red arrows should only ever be chosen when something is
  actually being pushed, compressed, or directed.
- **A shot can sustain itself without camera motion, as long as something
  else is visibly continuous — found from a dense (3-5fps) frame-by-frame
  pass on a tree-house construction reference, a much closer read than any
  prior reference got.** Roughly half this video's shots are genuinely
  locked-off for 8-12+ seconds across several caption changes — the camera
  does not move at all — and they still read as alive because the object in
  frame is visibly *assembling itself* the whole time: reinforcement strips
  extend board-by-board along an edge, screws drive in one at a time, roof
  slats appear in sequence. The other half of the shots instead hold a slow,
  continuous camera orbit around the growing structure (the brick wall behind
  it visibly slides past, confirmed by comparing the background's position
  across a 10s window) while the object itself stays static. Both are valid;
  what's never acceptable — confirmed by the shock-absorber failure above —
  is a long hold where *neither* the camera nor the object is doing anything.
  See "Two valid ways to sustain a shot" in the Camera section below.
- **Introduced objects fly in and settle with a tiny arc and rotation — they
  never simply pop into existence, and this applies to every part, not just
  the ambient mechanism.** Confirmed repeatedly on the tree-house reference:
  a plank enters from off-frame on a curved path, rotates into its final
  orientation, and settles with a small bounce; several short pieces can
  converge on one assembly from different directions in parallel. This
  recipe's existing `ambient` requirement already covers the hero mechanism;
  this extends the same "no instant pop-in" rule to one-time introductions
  (a newly-added part, a tool entering frame) that aren't ambient at all.
- **A detail callout can be a continuous push-in/pull-out on the same camera,
  not a cut to a separate insert shot.** The tree-house reference's dimension-
  line close-up (a measurement label pushed right up against the rail) is
  reached by the establishing camera smoothly zooming in, holding, and
  zooming back out — the same shot, not a hard cut to Insert Macro and back.
  Treat this as an alternative to cutting into a separate `<Sequence>` for a
  quick callout, not a replacement for Insert Macro's harder cuts on a truly
  separate, isolated part.

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
  mixed with each other, plus one colorless event kind for when none of the
  three apply:
  - **Red** — force/direction/pressure (arrows showing a push, a compression,
    a load). Reserve this strictly — see the `highlight` event kind below for
    what to use instead when a model (or a human) reaches for an arrow just
    to have *something* happen on a word that isn't actually a force.
  - **Yellow** — the on-screen technical-term callout, and only that (name
    the real mechanism part — "rodillos", "pilares" — never a generic word
    like "superficie").
  - **Neutral gray/white** — flow or current direction, distinct from force:
    small chevrons or short arrows showing water/air/material moving past or
    around something (confirmed in the bridge reference's under-water
    scour shot). Use this instead of red when nothing is being pushed or
    compressed, only carried or flowing.
  - **`highlight` (no reserved color, no arrow)** — a brief outline or pulse
    on a part, used purely to acknowledge "this is the thing being talked
    about right now," with no claim about force, flow, or a named term.
    Borrowed from the schematic-world recipe's UI-select highlight. Exists
    specifically so a planner satisfying a noun-coverage or max-hold-cap rule
    has a correct neutral choice instead of defaulting to a red arrow on a
    word with no actual force behind it (confirmed happening in the v2
    planner test: 19-21 of 32-36 events were `force_arrows`, several on
    words like "importa" and "largo" that aren't forces at all).
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

**Sustain motion across the whole shot, not per caption.** A shot type
(especially cutaway interior) often holds through several caption changes.
The camera/object motion for that shot is one continuous move computed over
the shot's full duration, not something recalculated or reset every time the
caption text changes underneath it (confirmed by the tunnel-construction
reference's boring machine, which travels continuously through a single
cutaway for 30+ seconds while captions cycle on top of it at the normal
word rate). Two independent rhythms, not one: the caption layer changes fast,
the scene/camera layer moves slowly and continuously underneath it.

**Object-level motion never substitutes for camera motion — confirmed broken
on the shock-absorber render.** That render's long cutaway hold had a
genuinely good, continuously oscillating piston (point 3 of the Recipe) and
*zero* camera movement for over 20 seconds — verified by comparing full-
resolution frames, not a thumbnail. The heading of this section says object
motion does not cover this requirement; that render is the proof of why it
needs saying twice. Camera motion and ambient object motion are two separate
required fields — satisfying one is never grounds for skipping the other.

**Two valid ways to sustain a shot (confirmed on the tree-house reference).**
The rule above ("camera motion is mandatory, object motion doesn't cover it")
still holds, but a dense frame-by-frame pass on a seventh reference video
showed the inverse failure mode is also avoidable without the camera doing
the work every time. Pick one per held shot, deliberately, not by default:

1. **Camera-driven hold** — the object is static or close to it; the camera
   does the continuous slow orbit/push described above. The background must
   visibly change position relative to frame over the hold (a wall, a fence,
   anything behind the subject) — if nothing behind the subject moves against
   the frame, the orbit isn't actually happening.
2. **Assembly-driven hold** — the camera is genuinely locked off, but the
   object is visibly under active, continuous construction the whole time:
   parts extend, attach, or get added one at a time, never all at once and
   never frozen mid-assembly for more than a beat or two. This is a
   legitimate substitute for camera motion specifically *when the shot's job
   is to show something being built* — it is not a general exception to the
   camera-motion rule, and does not apply to a shot that is simply narrating
   over an already-complete object (that shot still needs camera motion).

A held shot that qualifies for neither — static object, static camera — is
exactly the shock-absorber failure above and is never acceptable. When
picking which to use, favor the assembly-driven hold for "how it's built/put
together" beats and the camera-driven hold for "look at the finished
mechanism" beats.

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
   behavior — and it must be a complete, legible, repeating work cycle, not
   a subtle idle detail.** The script must name it explicitly — e.g.
   `ambient: {kind: "fill-rise" | "flame-flicker" | "surface-sheen" |
   "strike-cycle" | "bore-travel", ...params}` — and the renderer should
   treat a missing or null `ambient` field as a build-time error, not a
   silently static shot. "Legible work cycle" is the bar, not "something is
   technically moving": a tool should swing and strike repeatedly with an
   impact effect on every hit, a boring mechanism should travel continuously,
   a flame never stops flickering, water/metal surfaces carry a slow-moving
   sheen highlight, steam clusters are born small and keep accumulating. A
   single one-time progression (a part slowly changing shape once over the
   shot) is weaker than this bar and should be paired with a true repeating
   motion where the mechanism supports one. This runs independent of any
   scripted event, every single shot, no exceptions — this is the rule that
   produced bit-for-bit static frames when treated as optional, and the one
   still worth over-delivering on even after a render stops being static.
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
   gray/white flow chevrons for a current or scouring effect (see The Look);
   a colorless `highlight` pulse/outline on a part's own word when nothing
   about it is force, flow, or term-worthy — this is the correct choice for
   "just acknowledge this noun," never a red arrow reached for out of
   convenience (see The Look's `highlight` entry).
6. **Cap how long any single unchanging composition can hold the screen —
   confirmed missing on the shock-absorber render.** That render held one
   graphic (a cylinder with an oscillating piston) for 20-30+ seconds while
   the script named several different parts (varilla, carrocería, válvulas,
   aceite) that never got their own visual moment — the piston's ambient
   oscillation was mistakenly treated as enough to cover all of it. It is
   not: ambient motion satisfies point 3, it does not substitute for content
   variety. Reference videos never do this — the `@conrazon_es` videos cut
   every 2-4 words, and even the tunnel reference's long continuous camera
   move keeps traveling past genuinely new sub-subjects (the arch, then the
   blast, then the rebar, then the TBM) rather than holding one static
   composition. Rule: if roughly 8-10 seconds pass with no new event, no new
   callout, and no camera move toward a different part of the object, that is
   too long — either cut to a new composition or reframe toward whatever
   part the narration has moved on to. Every technical noun the script
   introduces (not just the ones that got picked as the term-callout word)
   should get *some* visual acknowledgment — a quick highlight, a brief
   reframe, a small part-specific event — not just be spoken over an
   unrelated held shot.
7. **Reserve one indicator that escalates across several beats**, distinct
   from the hard-cut counters above: a stack of upward arrows that grows in
   count and height over 3-4 consecutive beats as pressure/intensity builds
   narratively. This is the one place smooth progression belongs.
8. **The payoff transformation is a state change on the hero object itself**,
   not a new object: the flame changes shape and color when the windproof
   cage engages; the pot's valve pin visibly rises as the indicator. Never cut
   away from the object to show the "answer" — the object becomes the answer.
9. **Captions — exact behavior, no exceptions:** each caption is a short
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
   A short trailing fragment left over at a sentence boundary (e.g. the final
   word of one sentence, like "perfecto.") must get folded cleanly into
   either the caption before it or the one after it at script-write time —
   never concatenated onto the next phrase as literal adjacent text (seen on
   the shock-absorber render as "perfecto El problema viene después" showing
   as one caption). If grouping logic produces a fragment shorter than ~2
   words on its own, merge it into a neighboring phrase's *text*, don't let
   it render as a standalone beat that visually runs into the next one.
10. **Stat badges attach to the object, not the frame corner** — "118°C",
    "11 min" sit near the part they describe and update in place as the shot
    continues, they do not live in a fixed HUD position.
11. **Vary cheap secondary details between repeated beats** — if a secondary
    object recurs across several shots (a car crossing a bridge, a container
    passing through a process), change a trivial attribute each time (its
    color) so repetition doesn't read as a looped asset. Low cost, confirmed
    useful in the bridge reference.

## Alternative grammar: one continuous world (no cuts)

The shot grammar above (hard cuts between separate `<Sequence>`s, one camera rig per shot type) is not the only valid one, and for a
long script it produces few, long shots (the approved 13-shot plan for the CPU test averaged 12 s per shot). A microwave explainer
(`@stupydoo`, 164 s) was checked with ffmpeg scene detection at thresholds 0.15, 0.3 and 0.5: no hard cut at all (three weak changes at
the lowest threshold plus the end card). A 2 fps run shows a fixed isometric angle, a camera that only pans and zooms between parts
(flights of about one second), and one world that persists: the same floor, wall and mug throughout, parts placed once and left there.

Use this mode when the script introduces many parts in sequence:

- **One scene, one camera path.** The whole video is a single `<ThreeCanvas>`. The script holds `waypoints` (focus station + distance
  class `wide|medium|close`), one per beat of roughly 3-6 s. The camera leaves a few frames before the beat's first word, flies for
  about 1.2 s with an ease, and then drifts. Drift is a global function of the frame (small yaw and breathing), never reset per beat,
  so there is no jump at a waypoint.
- **Stations in narration order.** Parts sit in a row on a workbench, in the order the narration names them, with the hero (the chip)
  behind it. The camera walks along the row; neighbours stay partly visible, which is what gives continuity.
- **Parts accumulate.** A part flies in once (arc, rotation, spring) when the camera first heads for it, or shortly before its first
  event, and stays. A late beat can move a part to the hero (the heatsink flies onto the chip).
- **Every part runs a repeating work cycle** from the moment it arrives (lever toggling and current pulses, a stepping pointer,
  conveyor cubes, a spinning fan). This replaces the per-shot `ambient` field.
- **Planner:** beats instead of shots. `motion.plan()` only cuts on sentence ends, so split any beat longer than 6.5 s at the longest
  pause near its middle. The model returns `focus`, `dist`, a one-line `show` and up to three events (`highlight`, `force_arrows`,
  `term_callout`); there is no `attach`, `pushin` or `assembly`, because arrival and zoom are now the grammar itself. Code enforces:
  first beat chip/wide, last beat chip, one term per callout, red arrows only on a flow or motion word, the 9 s hold cap (a change of
  focus or distance counts as a change), and one flight of lead time between waypoints.
- **Colours:** unchanged. Current and "on" states use one saturated content colour (lime) on neutral parts; red, yellow and the
  colourless highlight keep their meanings.

Not yet settled: the CPU test is the first render of this mode (see `experiments/cpu-lowpoly/README.md` for what was and was not
checked). Fast flights across the whole bench can read as a blur; `close` on a station wider than the frame shows only part of it.

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
single-subject, multi-angle video with no metaphor shot. A sixth video, from
`@construlandai` (a mountain-tunnel construction explainer), surfaced the
sustained-motion requirement above: a continuous machine-travel move held
across 30+ seconds of caption changes, and tool strikes animated as a
complete repeating cycle with impact particles rather than a single gesture.
A seventh video, from `@stupydoo` (a tree-house construction explainer,
164s), was reviewed at far higher frame density (3-5fps dense windows at
several points, not just a sparse overview) specifically to isolate camera
and object-motion technique rather than visual style — it confirmed the two
valid sustain strategies above, the no-pop-in rule for introduced objects,
the push-in/pull-out detail callout, and (as a hook technique worth noting
even though this recipe's topics are rarely destructive) a cold open where
the finished structure explodes into tumbling, rotating debris for 2-3s
before cutting to the calm starting point.