# Continuous-world schematic recipe

A third cookbook, different axis from the other two. `motion-graphics-recipe.md`
(vector) and `motion-graphics-recipe-lowpoly.md` (3D cutaway) both cut hard
between a fixed set of shot types. This one does not cut at all: one
continuous scene/diagram that the camera reframes while elements are added to
it over time, paired with short-replacement captions (never sentence
accumulation). Reverse-engineered frame-by-frame from three videos, all from
the same channel (`@stupydoo` on TikTok): a home-drainage/plumbing explainer
(138.9s, dark schematic look), a microwave-radiation explainer (168.4s, pastel
isometric look), and a toaster heating-element explainer (138s, pastel
isometric look). No reference footage, audio or channel artwork is copied —
only the technique.

Status: derived from contact-sheet review of all three videos end to end.
Nobody has built a POC against this one yet — every timing number is a
starting hypothesis, same caveat as the other two recipes.

## Why this is a separate recipe, not a variant of the other two

The two axes that actually vary independently, confirmed across all the
reference videos reviewed so far:

| | Hard cuts between shot types | Continuous growing world |
| --- | --- | --- |
| **Short-replacement captions** | `motion-graphics-recipe-lowpoly.md` | **this document** |
| **Sentence-accumulation captions** | (not seen) | the original map/UI recipe's Uber reference |

Do not assume a continuous world implies accumulating captions, or that hard
cuts imply short captions — pick each axis on its own merits. This recipe is
the continuous-world + short-caption combination.

## The look — two confirmed variants

Both variants share the same grammar (below); only the rendering skin
differs. Pick one per video, never mix them in the same video.

**A. Dark schematic** (the plumbing reference):
- Near-black/navy background with a faint scattered dot-grain texture over
  everything — not decorative noise to skip, it is consistently present in
  every frame of the reference.
- Objects are flat-shaded, mostly white-line/silver fixtures (sink, pipe
  runs) against the dark background — line-art-like, not fully rendered.
- Color-coding carries the whole story: blue = clean water, sickly
  yellow-green = foul/problem water or odor, orange-red = a newly introduced
  or currently-highlighted component, white = neutral narration.

**B. Pastel isometric diorama** (the microwave and toaster references):
- Light tan/wood or tile background, isometric 3/4 camera angle.
- Flat-shaded geometry with a visible paper-grain/cross-hatch texture
  overlay — gives an illustrated rather than clean-CG look. This is a
  deliberate post-process filter, not a rendering limitation to fix.
- Soft pastel accents (mint, coral, powder blue) on an otherwise
  neutral/cardboard object palette.
- Color-coding: orange-red = key term or highlighted phenomenon, black =
  neutral narration, and a dedicated wave/field color (purple or orange
  dot-density) for invisible phenomena (radiation, heat).

## World grammar — one scene, never a hard cut

This is the opposite default from the other two recipes: there is no
`<Sequence>` per shot type. Build one continuous scene and animate the camera
and the scene graph against `useCurrentFrame()`:

1. **The scene starts minimal** — often just the hero object alone, or even
   just its internal mechanism with no housing at all (the toaster reference
   opens on the bare heating element, no toaster shell yet).
2. **New elements are introduced one at a time, each on its own narration
   beat** — a second fixture, a tool, a casing panel — never all at once.
   Each introduction is a good moment for the UI-select highlight (below).
3. **The camera continuously reframes to keep the growing scene in frame** —
   push out as the diagram gets larger, pan toward whatever was just added,
   tilt up to follow a part that grows taller (the vent pipe reference). This
   is the only camera motion in this recipe; there is no cutting between
   fixed rigs like the other two recipes.
4. **The ending can loop into the opening** — the last frame of the
   reference plumbing video is pixel-for-pixel the same composition as its
   first frame. Worth doing whenever the topic naturally returns to its
   starting state; do not force it otherwise.

## Recipe

1. **Write the script as one continuous timeline, not a shot list.** Fields:
   `duration`, an `elements` array (each with `introducedAt`, geometry/asset
   reference, optional `removedAt`), a `camera` array of reframe keyframes
   (`at`, position/target/zoom — interpolated between them, never a hard
   reset), a `captions` array (see below), a `fields` array for wave/ripple
   phenomena (`originElementId`, `startAt`, growth rate, color, intensity —
   see point 5), and an `ambientEvents` array tied to narration timestamps
   (rain starting, fog shrinking) rather than looping independently of the
   story.
2. **Captions never accumulate — same hard rule as the lowpoly recipe.** Each
   caption is a short phrase that fully replaces the previous one. This
   recipe adds one extra behavior not needed there: two captions may appear
   **simultaneously** when the beat is a direct comparison (e.g. "HIRVIENDO"
   in the hot-zone color stacked above "FRÍA" in the neutral color, both
   visible over the same frame) — this is a deliberate exception to "one
   caption at a time," not a loophole for accumulation. Each caption's color
   must match the color-coding category of what it is describing (see The
   Look); never pick a caption color decoratively.
3. **Introduce components with a UI-select highlight**, not a camera cut: a
   colored rectangle/outline flashes or pulses briefly around a part the
   instant it is first mentioned or newly added to the scene. This replaces
   the "insert macro" shot type from the other recipes — there is no separate
   close-up <Sequence>, the highlight does the job of directing attention
   within the one continuous frame.
4. **A tool performing a real action is a valid scene transition.** A hammer
   breaking open a floor panel, a drain snake corkscrewing down a pipe — the
   tool's animation IS the transition into the next reveal, motivated by
   physical cause rather than a cut. Model the tool, animate it acting on the
   scene, and let the reveal follow from that action (the camera pushes
   through the hole the hammer just made, for example).
5. **Invisible phenomena get a wave/field visualization, not an icon.**
   Radiation, heat, current, sound: render as a growing ripple or a
   dot-density field radiating from its source, colored per The Look's
   field color, with density or spacing indicating intensity (sparse dots =
   weak/cold, dense dots = strong/hot). This is how both pastel-variant
   references show an otherwise invisible effect; do not substitute a stat
   number or an arrow for this category of event.
6. **Metaphors are a single simple household object, not a full second
   cutaway.** When an analogy helps (the plumbing reference's water-seal
   explained via a cup and a striped rod), reach for the cheapest possible
   real object instead of building a parallel scene — this recipe treats
   metaphor as an inexpensive aside, not a dedicated shot type.
7. **The solution is demonstrated acting on the scene, not just stated.** If
   the narration proposes a fix, animate it happening in the diagram (a
   bucket tips and pours into the drain) rather than cutting to a title card
   or relying on the caption alone.
8. **Ambient motion is still mandatory and still causal.** Carry over the
   lowpoly recipe's non-null `ambient` field requirement, but tie it to the
   story here specifically: rain intensifies because the narration is
   describing a flood, a smell-cloud shrinks because the narration is
   describing evaporation. An ambient effect with no narrative cause reads as
   decoration in this recipe and should be cut rather than added for its own
   sake.
9. **Reverse-exploded assembly is a valid opening or closing move.** Starting
   from the bare internal mechanism and building outward into the whole,
   recognizable, branded object (or the reverse) is this recipe's version of
   an establishing shot — confirmed in the toaster reference, which ends on
   the fully-cased product after spending most of its runtime on the
   internal wire grid alone.

## Gotchas to test for

- A continuously growing scene will run out of frame if the camera does not
  keep pulling back — decide the final zoom level early and work backward,
  rather than discovering the scene no longer fits near the end.
- Fix each color's meaning once per video and never reuse it for a different
  category mid-video — the dark-schematic reference never once uses its
  green (problem) color for anything but odor/foul water, across 138.9s.
- Simultaneous dual captions need enough vertical separation and distinct
  colors to read as two separate labels, not one broken line — do not stack
  them without a clear color or size difference.
- The paper-grain/cross-hatch filter (variant B) is a post-process step over
  otherwise normal flat-shaded 3D, not a different modeling technique —
  applying it inconsistently (some frames textured, some not) will be more
  visible than skipping it entirely.
- A tool-action transition only works if the tool's motion is unambiguous
  before the reveal — cutting to the result without showing enough of the
  swing/turn/push reads as a jump cut, not a motivated transition.

## What a POC needs before this is more than a spec

1. Build the continuous-camera-plus-growing-scene mechanic alone first, with
   no fields/highlights/tools yet — confirm the reframing-camera approach
   works technically before layering on the other techniques.
2. A 10-15s test adding exactly two new elements with one UI-select highlight
   each, checked as a contact sheet, before attempting a field visualization
   or a tool-action transition.
3. Decide early which look variant (A or B) a given topic calls for — pick
   by whether the subject is infrastructure/mechanical (favors A) or a small
   household object/phenomenon (favors B) — rather than defaulting to one.

## Reference

Three videos from `@stupydoo` on TikTok, analyzed frame-by-frame (not stored
in this repo — technique only, no footage copied): a home drainage/plumbing
explainer (dark schematic look, 138.9s), a microwave-radiation explainer
(pastel isometric look, 168.4s), and a toaster heating-element explainer
(pastel isometric look, 138s).
