# Deadbolt low-poly (10 s silent test of the updated low-poly recipe)

How a deadbolt works: the key lifts the pins until their splits sit on the shear line, the cylinder can turn, and the bolt
retracts. A 10-second, 1080×1920, 30 fps silent clip with captions and graphics only, built from the updated
[`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md) to check the fixes from the
sky-blue and aluminium-foil tests. Schematic: no figure or source is shown. No queue or main-flow integration.

Remotion 4.0.538, `@remotion/three` 4.0.538, `three` 0.187.0, `@react-three/fiber` 9.8.2 (pinned). Script in `script.json`,
interpreted by `Deadbolt.tsx`. Same conventions as `../sky-blue-lowpoly/` (flat-shaded procedural geometry, lights × π,
every value a function of `useCurrentFrame()`).

## Run

```powershell
cd experiments/deadbolt-lowpoly
npm ci --cache ../../out/deadbolt-lowpoly/npm-cache
python verify.py --stills        # 20 stills (5 columns x 4 rows) -> out/deadbolt-lowpoly/contact-sheet.jpg
npm run render                   # -> out/deadbolt-lowpoly/final.mp4
python verify.py                 # measure the MP4, count identical consecutive frames, write verification.json
npm run studio                   # interactive preview on port 5196
```

`out/` is ignored by Git.

## How each failed rule is enforced

The component runs `validate()` when it loads, so a render with any of these defects fails instead of shipping:

- **Camera motion in every shot.** Each shot has `camera.from` and `camera.to` (position and target); the rig interpolates
  them over the shot with the frame. Identical poses throw. Establishing shots orbit and push in, the cutaway pushes in, the
  insert drifts and pushes in.
- **Required ambient field.** Every shot has `ambient: {kind, moving}`; a missing kind or an empty `moving` throws. The
  kind drives behaviour: `sheen-dust` (travelling highlight band on the metal plus drifting flat-shaded dust),
  `spring-wobble-sheen` (springs breathe, plus the sheen).
- **Replacement captions.** `captions[]` holds independent phrases (at most five words) with their own `at`/`until`; each
  is drawn whole, never built word by word, and a phrase that starts with the previous one throws. The yellow term callout
  (`PINES`, `LÍNEA DE CORTE`) names a real part and holds longer than its phrase.
- **Environment.** The establishing shots have door, frame, knob, strike plate, wall and floor; the cutaway has a door
  slab, lock housing, bolt and cam and screws (the check requires at least two). The insert is near-empty by design.
- **Metaphor shot.** Not used: the real mechanism is already visual.
- **Flow chevrons.** Not used: nothing flows in this topic. Red is only for the key-push, pin-push, turn and retract arrows.

## Decisions the recipe did not cover

- **Events without narration.** Each event fires at the start of its caption (`events[].caption` names it); there is no
  word timing in a silent test.
- **No plug rotation in the cutaway.** A half-modelled plug cannot rotate about its axis without the cut face turning
  away, so the cylinder turning is shown in the closing shot (the key turns 90°) and the cutaway ends with the pins aligned.
  The brief's "the cylinder spins but the bolt doesn't move until the pins line up" is therefore shown as: pins align
  (cutaway, insert), then key turns and bolt retracts (close). The bolt never moves before alignment.
- **The payoff is a state change on the object.** The close is the same door and deadbolt as the opening; the bolt leaves
  the gap between door and jamb.
- **Shear line as the protagonist colour.** It is a thin dark line that turns pale blue when every split is on it.
- **Backdrops.** A dark chamber backdrop behind the pins and keyway was added after the first test frames, because pins
  against the light door slab read as grey on grey.
- **Insert distance.** The first insert camera was too close for the pin to read; it was pulled back before the contact sheet.

## Checks

- `verify.py` compares every consecutive frame of the final MP4 (downscaled to 108×192): 0 identical pairs out of 300.
- Contact sheet: 20 stills across the clip (5×4), both before the render and cut from the finished MP4.

## Limits

- Not watched in motion; only stills have been inspected.
- The pins are small in the cutaway and the housing is a large block, so the mechanism reads best in the insert.
- The first caption overlaps the floor line in the opening shot.
- Font is `Inter` with `Segoe UI`/`Arial` fallbacks; not bundled.
