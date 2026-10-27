# Silent vector motion-graphics recipe

A cookbook for the look the user asked for: clean, light-pastel, After-Effects-style
vector animation driven by a small script file, no narration. Proven on two
proofs of concept (`experiments/remotion-explainer/coffee-sci/`,
`experiments/remotion-explainer/zebra-stripes/`). Nothing here is wired into the main
Brainrot flow yet; the last section lists what that integration needs.

Status: rendered and checked frame by frame from contact sheets. Nobody has watched
full playback or listened to the sound bed. Treat timings as a starting point.

## The look (what the user approved)

- Light pastel stage per phase (cream, peach, mint, butter, sky, lilac). One strong
  accent (coral), ink for text and outlines, one green for "this is the answer".
- Reference: the first sample the user shared (bold kinetic type, UI cards, a hero
  object that changes shape, colour panels sweeping between beats).
- **Never add:** corner brackets, timecode, section label, progress line, film grain,
  vignette, chromatic aberration, dark "film" grading. The user rejected all of them
  twice. The only text outside the content is one small caption when values are
  illustrative.
- Silent: no speech. Short synthesized sound effects are fine (see Sound).
- Motion blur stays light (shutter 140, 4 samples).

## Ingredients

All in Remotion 4.0.538 (exact pins; `@remotion/paths`, `@remotion/noise`,
`@remotion/motion-blur` are added to `experiments/remotion-explainer/package.json`).

| Tool | Used for |
| --- | --- |
| `evolvePath` | trim-path draw-on of strokes (rope, axes, curves, steam, check marks) |
| `interpolatePath` | shape morph (bean to cup rim, straight stripes to wavy stripes) |
| `spring`, `Easing.bezier` | overshoot pops, graph-editor ease curves (`EZ.out`, `EZ.inout`) |
| `noise2D` | handheld camera roll, steam wobble |
| `CameraMotionBlur` | light motion blur on fast moves |
| SVG layers | everything is vector shapes, not HTML boxes |

Reusable primitives live in `experiments/remotion-explainer/coffee-sci/kit.tsx`:
`Tube` (outlined, highlighted stroke that accepts an `evolvePath` dash), `Halftone`
(dot-shaded disc lit from up-left, pass `t={0}` so the memo holds), `Glyphs`
(per-glyph spring text animator, `ca={false}` for no colour fringe), `Dial` (gauge with
needle and counter), `camAt` (camera keyframes with bezier easing), helpers `pts`,
`toD`, `seg`, `ez`, `clip`.

## Recipe

1. **Pick one hero object** and keep it on screen the whole video. It draws on, morphs,
   shrinks into a corner, and returns at the end. This shared element is what makes the
   video feel edited instead of slide-by-slide. Drive it with one keyframe table
   (`T` seconds to x, y, scale) through `interpolate` with `EZ.inout`.
2. **Write the script first** as JSON: `duration`, `phases` (`[start,end]` per phase),
   `texts` (`at`, `until`, `text`, `size`, `color`, `y`, `font`, `wave`), `cam`
   (`at`, `zoom`, `cy`), `dials` (`at`, `until`, `label`, `unit`, `from`, `to`, `x`, `y`,
   `max`, `decimals`), `sfx` (`at`, `kind`), and a `sources` list. The component only
   interprets the script; changing the graphics means editing the JSON.
3. **Four phases, about 4 to 5 seconds each**, one pastel background colour each:
   hook, structure (cards or parts), evidence (chart or experiment), answer card.
   Backgrounds change with a skewed colour panel that sweeps in over about 0.5 s
   (`left = W - ease(p) * (W + w)`, `w = 1.5 W`, `skewX(-12deg)`); the base colour
   switches while the panel covers the frame. Content is drawn above it and keeps moving.
4. **Hook beat:** question as kinetic type in two halves (top and bottom of the frame),
   hero draws on, then morphs. Text slams use `Glyphs` with `wave` for a little bounce.
5. **Structure beat:** a UI card grid like the reference's project grid. Cards slide in
   with a stagger, bars fill with `EZ.out`, verdict marks draw on with `evolvePath`.
   Dim the losers and enlarge the winner.
6. **Evidence beat:** pick one of two forms.
   - Zoned chart: tinted bands for each regime, an `evolvePath` curve, a cursor with an
     echo trail that changes colour per zone, a dial that reads the cursor value, and a
     dwell in the interesting zone.
   - Side-by-side comparison: two copies of the hero, small agents (dots with flapping
     wings and echo trails) approach both, counters read the outcome.
7. **Answer beat:** a white source card slides up with a spring (`damping 14`,
   `stiffness 90`, start `translate(0, 2300)` so it never peeks in early), one huge
   figure or phrase, a zone bar or two chips, and a small source line. The hero comes back
   below it.
8. **Camera null:** wrap all world content in one transform: `translate(540 960)`,
   `rotate(noise)`, `scale(zoom)`, `translate(-540 -cy)`. Text overlays and dials stay in
   screen space.
9. **Rhythm:** something changes at least every 1.5 s. No static hold longer than about
   2 s except the deliberate dwell.
10. **Facts policy:** only state facts the repo has a source for (`sources` in the
    script). Anything schematic gets the caption "illustrative values, not a
    measurement" during that phase. Say "best supported" or "still a hypothesis" where the
    literature says so; do not turn a hypothesis into a claim.

## Sound

`experiments/remotion-explainer/coffee-sci/sfx.py` renders a mono WAV from the script's
`sfx` array (`hit`, `tick`, `whoosh`, `riser`) with numpy only; no samples, no speech.
Mux with `ffmpeg -i silent.mp4 -i sfx.wav -c:v copy -c:a aac -shortest out.mp4`.
Cue ideas: `whoosh` on each panel sweep, `hit` on text slams and on the answer, `tick`
on card reveals and counters, `riser` before the key reveal.

## Render and check

```sh
cd experiments/remotion-explainer
npx tsc --noEmit
npx remotion still <dir>/index.tsx <CompId> out.png --frame=N     # spot checks
npx remotion render <dir>/index.tsx <CompId> silent.mp4 --concurrency=4 --crf=18
python -I <dir-with-sfx>/sfx.py <dir>/script.json sfx.wav
```

Always build a contact sheet before the full render: 12 stills with `ffmpeg ... hstack`
and `vstack`, then look at it. Two renders each took under a minute on this machine.

## Gotchas learned

- `CameraMotionBlur` feeds fractional frames: do not `Math.round` the frame in springs
  or text timing.
- `interpolatePath` needs identical command structure: build both paths from the same
  point count (all `L` segments, 240 points, smooth enough).
- A closed shape must start at the same angle in both paths or the morph twists.
- `evolvePath` must be recomputed from the current (morphed) path each frame.
- `Halftone` draws thousands of circles: pass a constant `t` so React memo holds.
- A CSS `drop-shadow` on an SVG group leaves a visible haze box; use a flat offset
  shadow rect instead.
- Any text on two layers at the same `y` overlaps; fade the earlier one out first.
- `Remotion still` rejects frames at or past `durationInFrames`.

## What main-project integration needs

Not done; these are the steps, in order.

1. Move `kit.tsx` and the script interpreter into `motion/` (the Remotion project that
   `brainrot/motion.py` already drives) as props-driven compositions.
2. Have the model write only the script JSON (phases, texts, dials, sources), validated
   against a schema, instead of freeform TSX. This is the main quality lever: the tuned
   primitives stay fixed, the model chooses content.
3. Add this recipe as an explicit skill that the motion-graphics generation loads (the
   runtime only sees skills that application code loads). Keep the "never add" list in it.
4. Add an automatic review step: render a contact sheet, check it, retry once on
   failure. Respect the repository rule that live generation is not run solely as a test.
5. Narrated mode is a separate path (word timings drive `texts[].at`); this recipe is
   silent by design.
6. Update the third-party notices if new dependencies ship (the three Remotion packages
   are already in the experiment's lockfile).

## Examples

- `experiments/remotion-explainer/coffee-sci/CoffeeLight.tsx` with `script-light.json`:
  the light pastel reference implementation (grind cards, zoned extraction chart, source
  card). `Coffee.tsx` is the earlier dark version and is not the target look.
- `experiments/remotion-explainer/zebra-stripes/`: the second PoC, built by following
  this recipe (hero stripes morph, five-idea card grid, fly landing comparison, source
  card).
