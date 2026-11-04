# Sky blue low-poly (first build of the low-poly recipe with all four shot types)

A 10-second, 1080×1920, 30 fps silent clip on why the sky is blue (Rayleigh scattering), built from
[`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md) to check that its four shot
types work together: establishing (0-60), cutaway interior (60-150), insert macro (150-220), metaphor cutaway
(220-280) and a closing establishing hold (280-300). Schematic: no number or factual source is shown on screen.
No queue or main-flow integration.

Remotion 4.0.538, `@remotion/three` 4.0.538, `three` 0.187.0 and `@react-three/fiber` 9.8.2, all pinned. Script in
`script.json` (`shots[]`, `captions[]`, `events[]`), interpreted by `SkyBlue.tsx`. Same conventions as
`../moka-cutaway-3d/`: every value is a pure function of `useCurrentFrame()` (no `useFrame`, no random values),
flat-shaded `MeshStandardMaterial`, procedural geometry only, lights multiplied by π (see that README).

## Run

```powershell
cd experiments/sky-blue-lowpoly
npm ci --cache ../../out/sky-blue-lowpoly/npm-cache
python verify.py --stills        # 10 stills (frame 180 = the split, 250 = the eye) -> out/sky-blue-lowpoly/contact-sheet.jpg
npm run render                   # -> out/sky-blue-lowpoly/final.mp4 (only after the contact sheet is approved)
python verify.py                 # measure the MP4, write verification.json and contact-sheet-final.jpg
npm run studio                   # interactive preview on port 5194
```

`out/` is ignored by Git.

## Decisions the recipe did not cover

- **Yellow sun.** The brief asked for a yellow sun, but the recipe reserves yellow for the term callout only. The
  recipe won: the sun is a warm off-white emissive icosahedron (`#FFF4DC`). Yellow appears once, on
  "DISPERSIÓN DE RAYLEIGH".
- **"Composed" white light.** At the word "blanca" the single white beam is replaced by five thin parallel stripes
  (peach, cream, white, pale blue, pale violet) that spread over 10 frames to the same total width. Tints are pale
  on purpose: no yellow (reserved), no saturated red (reserved), no literal rainbow. It stays mostly white.
- **Red/orange light.** The recipe keeps red for force arrows only, so the long-wavelength beam is orange
  (`#FF8A2B`, deflected 7°) and its single arrow is red. The scattered blue is a deep blue (`#1E4BD8`) because a
  pale blue is lost against the sky-blue background.
- **Silent events.** There is no narration, so an event fires on the frame where its named caption word first
  appears (`evAt()` in the component; words reveal every `wordGap` frames). If a voice is added later, replace
  `evAt()` with the transcript time.
- **Scatter streams.** Scattered blue segments are re-emitted every 20 frames, staggered per direction, so the
  scattering keeps happening instead of firing once (ambient motion in every held shot).
- **Shots.** Each shot is a `<Sequence>` with its own `<ThreeCanvas>` and camera, so no FOV or position carries over
  between hard cuts. Camera is static inside a shot; ambient motion is clouds drifting (driven by the global frame,
  so the closing shot continues where the first one left off), sun and tree sway, molecule wobble, beam shimmer,
  pupil breathing and travelling light pulses.
- **Atmosphere column.** 70 individual meshes, not an `InstancedMesh`: each molecule wobbles on its own seeded noise,
  and instancing is for static granular fill.
- **Eye.** A flattened sphere, iris and pupil seen face-on, not a true cross-section: the recipe's "model the half
  geometry" rule has nothing to cut here.
- **Second background colour.** Sky blue plus green hills and ground (two colours, as the recipe allows); the tree
  trunks are brown.
- **Captions.** Heavy black stroke from 16 hard text-shadows (no `paint-order` dependency), per-word spring reveal,
  no background box. The term callout is yellow, larger, and holds 8 frames longer than the caption.
- **Macro framing.** The first test at camera distance 5 pushed arrows and scattered segments out of frame;
  distance 7 keeps all four directions visible.
- **Frames, not seconds.** `script.json` uses integer frames (30 fps) like the other experiments.

## Recipe items not exercised here

Hard-cut stat flips, the escalating arrow stack, stat badges and the `sources` list (empty: nothing factual is
stated on screen) are not part of this topic.

## Limits

- Font is `Inter` with `Segoe UI`/`Arial` fallbacks; not bundled.
- Not rendered or watched in motion yet: only contact-sheet stills have been inspected. In the macro shot the
  caption can briefly overlap the downward blue segment.
