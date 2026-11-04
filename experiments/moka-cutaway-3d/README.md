# Moka cutaway 3D (first `@remotion/three` proof of concept)

A 10-second, 1080×1920, 30 fps silent low-poly clip: a moka pot cut in half on a gas ring, with ground coffee
above, a funnel in the middle and water below that starts to bubble, then steam. Lemons in a bowl, a blue tiled
wall and a dark counter complete the kitchen. One hard-coded caption, "Encima" (frames 120-200). Schematic: no
number, source or factual claim is shown. No queue or main-flow integration.

Built with Remotion 4.0.538, `@remotion/three` 4.0.538, `three` 0.187.0 and `@react-three/fiber` 9.8.2, all pinned.
Script in `script.json` (camera keys, bubble and puff births, caption, lemon periods, still frames), interpreted by
`MokaCutaway.tsx`. Everything is procedural geometry with flat-shaded `MeshStandardMaterial`; no textures or `.glb`.
Rules kept: all motion is a pure function of `useCurrentFrame()` (no `useFrame`, no random values; a seeded hash
and `noise2D` supply variation), shared `camAt`-style easing from `../remotion-explainer/coffee-sci/kit.tsx`.

## Run

```powershell
cd experiments/moka-cutaway-3d
npm ci --cache ../../out/moka-cutaway-3d/npm-cache
python verify.py --stills        # 10 stills (incl. frame 200, the steam) -> out/moka-cutaway-3d/contact-sheet.jpg
npm run render                   # -> out/moka-cutaway-3d/final.mp4 (only after the contact sheet is approved)
python verify.py                 # measure the MP4, write verification.json and contact-sheet-final.jpg
npm run studio                   # interactive preview on port 5193
```

`out/` is ignored by Git. `--gl=angle` is set in the npm scripts and in `verify.py`; WebGL needs it.

## `@remotion/three` gotchas found

- **Peer dependencies.** `npx remotion add @remotion/three` installs only the package; `three` and
  `@react-three/fiber` arrive transitively and are not in `package.json`. They are pinned here, with
  `@types/three`, so `npm ci` is reproducible.
- **Never `useFrame`.** The camera is moved from `useCurrentFrame()` by mutating `useThree().camera` in the
  render body (`Rig`), then `lookAt` and `updateMatrixWorld`. `ThreeCanvas` re-renders every Remotion frame.
- **Light intensities.** Since three r155 lights are no longer multiplied by π, so the brief's ambient 0.5 and
  directional 0.8 render about 40 % too dark and the hex palette looks muddy. The code uses `0.5 × π` and
  `0.8 × π`, which is the classic look those numbers describe. Pass `flat` to `ThreeCanvas` (no tone mapping), or
  ACES desaturates the flat colours.
- **Hand-cut half shells instead of a clipping plane.** Frustums are `CylinderGeometry(..., openEnded, thetaStart
  = π/2, thetaLength = π)` with `DoubleSide`, so the interior is visible. Clipping planes would need
  `renderer.localClippingEnabled` and a plane on every material, and still leave no cut face. The cut edges are
  thin boxes (`Strip`), the water cut face is a `ShapeGeometry`. The brief says the cut is in the XZ plane; that
  plane is horizontal, so the cut here is the vertical plane through the axis that faces the camera.
- **Hourglass.** The brief says the cones join at their wide base and also asks for an hourglass; the hourglass
  (joined at the narrow waist, like a real moka) is what is modelled.
- **`InstancedMesh` for the coffee.** 200 icosahedra cost one draw call. Matrices and per-instance colours are
  written once in `useLayoutEffect`, never per frame. The material colour must be white or instance colours are
  tinted. A dark half-frustum "bed" behind the grains hides the gaps.
- **Transparency.** Water and steam use `transparent` with `depthWrite={false}`; otherwise grains and bubbles
  vanish behind the water. Bubbles are meshes mounted only during their life window.
- **Shared vertices.** `IcosahedronGeometry` is non-indexed, so jitter is hashed from the vertex position, not
  its index, or the lemon and puff surfaces crack.
- **Speed.** Each still takes about 35 s (browser start plus shader compile); the 10-still sheet takes about 6
  minutes. Remotion's `--concurrency` matters more for the full render.

## Deviations from the brief

- 22 bubble births (shrinking gaps) instead of 6, so bubbles keep coming until the end; each rises for 25 frames
  and pops over 5.
- Puff births are 180-220 with a 40-frame life, so the last fades near frame 260 instead of 240.
- Camera target and distance are raised during the steam event (frames 200-300) so the puffs stay in frame.
- The 60 px caption is small at this size and sits over the moka at close range; `caption.size` and `caption.y`
  are in `script.json`.
- Font is `Inter` with `Segoe UI`/`Arial` fallbacks; not bundled.
- Not rendered or watched in motion yet: only the contact-sheet stills have been inspected.
