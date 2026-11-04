# Elevator cables 2D (silent motion-graphics experiment)

A 10-second, 1080×1920, 30 fps silent vertical clip: four people in an elevator cabin hang from
six grey cables and one gold cable. One grey cable frays and snaps at frame 150; the cabin jolts, the
people react, and the remaining cables hold. Captions: "No depende de uno," and "sino de varios."
This is a schematic metaphor about redundancy: no number, source or factual claim is shown.

It follows [the motion-graphics recipe](../../docs/motion-graphics-recipe.md) and the layout of
`experiments/remotion-explainer/`: script as JSON (`script.json`), component that only interprets it
(`ElevatorCables.tsx`), one shared camera null, no corner brackets, timecode, vignette or film grain.
No queue or main-flow integration.

## Files

- `script.json`: frame timings for the break, the reaction and the jolt, caption cards, camera keyframes, floor numbers.
- `ElevatorCables.tsx`, `index.tsx`: Remotion 4.0.538 composition `ElevatorCables` (SVG, frame-driven; no random values).
- `verify.py`: contact sheet before the render, measurements after it.
- Reused from `../remotion-explainer/coffee-sci/kit.tsx`: `camAt`, `EZ`, `ez`, `seg`, `clip`, `wiggle`, constants.
  `evolvePath` (from `@remotion/paths`) draws the frayed strands. `Glyphs` is not used: it is full-width and
  centred and cannot hold the highlighted-word box, so the caption card repeats its per-glyph spring inline.

## Run

```powershell
cd experiments/elevator-cables-2d
npm ci --cache ../../out/elevator-cables-2d/npm-cache
python verify.py --stills        # 10 stills incl. frame 150 -> out/elevator-cables-2d/contact-sheet.jpg
npm run render                   # -> out/elevator-cables-2d/final.mp4 (only after the contact sheet is approved)
python verify.py                 # measure the MP4, write verification.json and contact-sheet-final.jpg
npm run studio                   # interactive preview on port 5192
```

Needs Node.js 24, ffmpeg and a Chrome-compatible browser (`npx remotion browser ensure` downloads one).
`out/` is ignored by Git.

## Notes and limits

- Characters are drawn at the requested sizes (head radius 28 px) and the cabin is sized to fit them.
- The font is `Inter` with `Segoe UI`/`Arial` fallbacks; it is not bundled, so another computer may render a
  different bold sans.
- While the camera dollies out (frames 170-250) the second caption card overlaps the lower part of the cabin.
- Not rendered, played or reviewed in motion yet: only the contact-sheet stills have been inspected.
