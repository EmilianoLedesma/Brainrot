# Remotion animated explainer prototype

Original 145.2-second, 1080×1920/30fps scientific explainer: **Why metal feels colder**.
This is a separate visual experiment, with no production queue integration.

The actual renderer is **Remotion 4.0.538**, React and original SVG artwork. The
video-use approach supplies the editing workflow: cached speech first, parallel
animation authorship, word-boundary reveals, finished-video inspection and measured
audio. This version does not call video-use's FFmpeg assembly helper: Remotion
composes and encodes the complete animation directly.

See [reference review](REFERENCE-REVIEW.md) for inspected channel examples and
which visual techniques this experiment adopts. No reference footage, audio or
channel artwork is copied into the prototype.

## Reproduce locally

Requirements: Node.js 24/npm, a local Chrome-compatible browser (or Remotion's
downloaded browser), and the cached original prototype narration.

From this directory:

```powershell
npm ci --cache ../../out/remotion-explainer/edit/npm-cache
node prepare.mjs
npm run still
npm run render
```

If Chrome is not found, `npx remotion browser ensure` downloads Remotion's pinned
browser. Alternatively append `-- --browser-executable="<local browser path>"`
to `npm run render` / `npm run still`. The reviewed render used the installed Edge
browser; there is no developer-specific absolute browser path in source.

`prepare.mjs` reuses `out/video-use-prototype/edit/{narration.mp3,words.json,scene-plan.json}`.
These private/generated media files are deliberately ignored. Transfer them during
the repository's deliberate media handoff, or follow the
[first prototype's reproduction steps](../video-use-prototype/README.md) to create
them locally with the explicitly selected speech voice. No API or transcription
fallback is configured. The licensed DM Sans font is bundled here.

`npm run studio` starts the isolated interactive Remotion preview on port 5191.
`npm run render` writes `out/remotion-explainer/edit/final.mp4`, using at most two
rendering workers to keep the running Brainrot application usable. Art, layouts,
motion and word cue selection are in `Art.tsx`, `Spread.tsx` and `index.tsx`.

From the repository root, run measured media and filmstrip checks with the first
prototype's isolated Python environment:

```powershell
experiments/video-use-prototype/.venv/Scripts/python.exe experiments/remotion-explainer/finish_audio.py
experiments/video-use-prototype/.venv/Scripts/python.exe experiments/remotion-explainer/verify.py
```

Create that environment with the first prototype's locked setup when needed.
Results are saved as `verification.json`, `contact-sheet.jpg` and `verify/` beside
the finished video. Measurement checks do not replace inspecting the filmstrips
or listening to the finished narration.

## Visual approach and limits

The polished version retains ten chapters but stages thirty narration-led visual beats.
The opening hand no longer competes with temperature readings. Contact becomes a
material cutaway, then a simultaneous metal/wood comparison with changing skin
color and distributed versus local warming. Equal ice cubes enter on the spoken
placement cue; melting begins only after both materials are named. The final
comparison holds while the last line is spoken.

Oversized recognizable objects replace the earlier framed panels. The ten scenes
use alternating dark stages and cream interludes, schematic material cutaways,
travelling heat pulses, staged melting and selectively revealed
large labels. SVG shapes remain sharp at the full portrait resolution. Scene
reveals resolve exact phrases against the cached word timings; the scene plan
retains the original scientific sources. Ice melting is a qualitative illustration,
not measured experimental data. Dot fields show schematic energy spread rather
than literal molecular arrangements or measured temperatures.

The original English narration is intentionally unchanged so the two prototypes
provide a useful visual comparison. No Spanish voice, music, new speech, cloned
voice, generated footage or paid model call was used. This illustrates a scripted
agent-assisted authoring workflow; it is not an unattended video editing agent.
It is a simpler editorial illustration style than the channel's finished mixed
media production, and does not establish comparable retention or production cost.

Remotion has its own software license; inspect the installed package license and
[current licensing terms](https://www.remotion.dev/docs/license) before choosing
production deployment. See `public/OFL-DMSans.txt` for the bundled font license.
