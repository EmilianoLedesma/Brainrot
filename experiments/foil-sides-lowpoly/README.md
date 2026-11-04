# Foil sides low-poly (93.65 s, silent, script and shots planned by Brainrot code)

Why does aluminium foil have a shiny side and a matte side? A silent 1080×1920, 30 fps, 93.65 s (2810 frames)
low-poly explainer in the style of [`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md).
The script comes from Brainrot's real generator, the word timings from its TTS, the shot plan from a new planner
modelled on `brainrot/motion.py`. The video has no narration. No queue or main-flow integration.

## Pipeline

1. **Script:** `brainrot.script.write_story(topic, brainrot_level=2, reference_context=<the factual explanation>)`,
   factual mode, Spanish, through Codex. Saved in `story.json` (title "El secreto del aluminio", 240 words including
   the title). Reviewed and kept as generated.
2. **Timing:** `brainrot.tts.narrate()` with `es-MX-JorgeNeural`, audio discarded, per-word start/end in
   `words.json`. At the default rate the narration measured 88.68 s, under the 90 s minimum, so it was re-run at
   `-5%` rate (93.15 s). The video is the narration plus a 0.5 s tail.
3. **Plan:** `planner.py` (`plan()` from `brainrot.motion` groups the words into blocks; `design()` asks the model for
   one of the four recipe shot types and at most one event per block as a Pydantic model; the validator enforces the
   recipe: first block establishing, exactly one metaphor on the block about the rollers, `term_callout` only on cutaway or insert, verbatim cues and
   captions). Output: `plan.json`, with the model's raw shot/event kept next to the validated one.
4. **Script and render:** `build_script.py` turns `plan.json` into `script.json` (`shots[]`, `captions[]`,
   `events[]`, real word frames); `FoilSides.tsx` only interprets it. Remotion 4.0.538, `@remotion/three`,
   `three` 0.187.0, flat-shaded procedural geometry, every value a function of `useCurrentFrame()`.

```powershell
# from the repository root, with Codex or Claude logged in (the planner defaults to claude-code; FOIL_PLANNER_PROVIDER=codex switches)
$env:PYTHONPATH="."; uv run --locked python experiments/foil-sides-lowpoly/planner.py          # new model plan (or add --reuse to re-validate the saved plan)
python experiments/foil-sides-lowpoly/build_script.py                                         # plan.json -> script.json
cd experiments/foil-sides-lowpoly; npm ci --cache ../../out/foil-sides-lowpoly/npm-cache
python ../foil-sides-lowpoly/verify.py --stills   # from the repo root: 16 stills -> out/foil-sides-lowpoly/contact-sheet.jpg
npm run render                                    # -> out/foil-sides-lowpoly/final.mp4
python verify.py                                  # measure the MP4, write verification.json and contact-sheet-final.jpg
```

`out/` is ignored by Git. `story.json`, `words.json` and `plan.json` are small tracked data files; the narration audio is not kept.

## Numbers

- Generated script: 240 words, narration 93.15 s at `-5%` (88.68 s at the default rate), video 93.65 s.
- Planner blocks: **7** (10.1 to 18.4 s). Shot mix in the final plan: establishing ×2, cutaway ×3, insert ×1, metaphor ×1.
  Events: force_arrows ×2, split ×1, term_callout ×1, curl ×1.
- `motion.plan()` at its default 11 s target gave only 5 blocks (15-22 s); a target of 8 s gave the 7 above.

## Where the model or planner fit badly (for the planner, not the recipe)

- **Block length.** `plan()` only cuts at sentence ends and this script has 40-word sentences, so blocks 0, 1 and 4
  (14.9, 16.5, 18.4 s) overshoot the 8-12 s target. A comma-level split would fix it; left as a finding.
- **Truncated caption.** My first validator cut model captions at eight words and, for block 2, produced "...las
  pasan al". The TTS word list carries no punctuation, so the validator now rebuilds clause boundaries from
  `story.json`, and a caption is a whole clause (up to 13 words) or the model's own phrase, never a cut. Long captions
  render at 54 px instead of 64 px.
- **No event on a held cutaway.** Block 5 came back with `none`. The sky-blue test showed that ambient motion alone
  reads as static, so a named `curl` event (a corner of the sheet curls over to show its other face) was added as a
  reviewer override, and `curl` is now part of the planner's event vocabulary and guidance.
- **Weak callout.** The model chose "superficie" for the yellow term. Replaced by a reviewer override with
  "RODILLOS", fired on the spoken "rodillo" (the block narration only says it in the singular).
- **Codex plan vs Claude plan.** The Codex plan put its only `split` at the very end ("tocó") and never on the real
  reveal; the Claude plan put it on "sale" (block 3) and closed on an establishing shot. Codex also exited with code 1
  intermittently (on the script, the plan and once with a timeout), so the planner defaults to `claude-code`.
- **Variety.** Four of the seven shots are cutaways; the only insert is the roller close-up.
- **Tone level.** `brainrot_level` runs 0-100, so level 2 is the "Grounded" band, not "Playful" (20-39). The script
  was kept as generated, so it has no jokes.
- **Provider flakiness elsewhere.** `edge-tts` dropped the stream on several sections; the repo expects a retry, so
  the runner retried each section (repo code untouched).

## What is on screen

The hero is one foil sheet with a shiny face (pale facets with a travelling highlight) and a matte face (flat grey).
Shots: the roll on a kitchen counter (establishing, opens and closes); the sheet being squeezed thinner by red
arrows; the rolling-mill cross-section with two sheets between polished rollers (the one metaphor shot); the
laminated pair separating to show matte inner faces and shiny outer faces; a roller on the sheet (the face under the
roller turns shiny, yellow "RODILLOS"); the sheet corner curling over. Which scene a cutaway shows is chosen in the
component from the event kind (`force_arrows`, `split`, `curl`), not by the model. Palette: one mint background
(coral counter in the establishing shots), neutral greys for the object, red only for arrows, yellow only for the
callout, captions white with a heavy black stroke and no box.

## Limits

- Not watched in motion; only contact-sheet stills (16 before the render, 16 from the final MP4) have been inspected.
- No ambient sound bed was added (optional in the brief); the video is fully silent.
- Font is `Inter` with `Segoe UI`/`Arial` fallbacks; not bundled.
- Shiny and matte are colours and a highlight band, not a material simulation.
