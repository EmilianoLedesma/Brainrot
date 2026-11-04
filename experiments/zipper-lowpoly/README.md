# Zipper low-poly (119.3 s, silent, default model)

How a zipper works: two tapes with staggered teeth, a Y-shaped slider (the cursor) that squeezes the rows together going up and pries them
apart going down, a pull tab, and the stops. A silent 1080×1920, 30 fps, 119.3 s (3579 frames) low-poly explainer built from the updated
[`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md): two valid ways to sustain a shot, no pop-in, a
push-in/pull-out detail, and the colourless `highlight` event. No queue or main-flow integration.

Model: the **default** one (`BRAINROT_CLAUDE_MODEL` unset, `claude-code` provider) for both `write_story` and the planner.

## Pipeline

1. **Script**: `write_story` (level 30, factual, Spanish) with the established facts as reference (`story.json`): "Los dientes de tu cierre no
   cierran nada", 323 words. Checked against the storytelling skill: concrete hook, causal order (parts, teeth stagger, the slider squeezes,
   the pull tab is only a handle, the wedge opens it, stops, failure), payoff answers the opening. One flag: "casi siempre es por un diente
   doblado o un cursor gastado" overstates the reference (it says only that a bent tooth or worn slider stops it closing well).
2. **Timing**: `timing.py` (`brainrot.tts.narrate`, `es-MX-JorgeNeural`, audio discarded) -> `words.json`: narration ends at 118.8 s at the
   default rate; video = narration + 0.5 s tail.
3. **Plan**: `planner.py` (`motion.plan()` blocks, then `design()` asks the model per block for a shot type, a `sustain` strategy and up to
   four events, validated) -> `plan.json`. Events: `highlight`, `force_arrows`, `term_callout`, `attach`, `pushin`.
4. **Script and render**: `build_script.py` -> `script.json` (the deliverable script: shots with `sustain`, `camera.from/to/follow`, `ambient`,
   `environment`; 85 phrase captions; events with targets); `Zipper.tsx` interprets it. Remotion 4.0.538, `@remotion/three`, `three` 0.187.0.

```powershell
# from the repository root; the planner defaults to claude-code, ZIPPER_PLANNER_PROVIDER=codex switches
$env:PYTHONPATH="."
uv run --locked python experiments/zipper-lowpoly/timing.py
uv run --locked python experiments/zipper-lowpoly/planner.py                 # --reuse re-applies the hold-cap fill to the saved plan
python experiments/zipper-lowpoly/build_script.py
cd experiments/zipper-lowpoly; npm ci --cache ../../out/zipper-lowpoly/npm-cache; npm run render
cd ../..; python experiments/zipper-lowpoly/verify.py                        # measurements + dense and fluidity contact sheets
```

`out/` is ignored by Git; `story.json`, `words.json`, `plan*.json` and `script.json` are small tracked data files.

## What was built for each recipe rule

- **Camera**: every camera-driven shot has `camera.from` -> `camera.to` over its whole duration (orbit and push, with `follow` making the
  target track the slider), independent of the caption rhythm. The jacket's denim bands and the wall stripes sit at different depths, so the
  background visibly slides past.
- **Two sustain strategies, chosen per shot**: `camera` (8 of 9 shots) or `assembly` (block 4, 52.6-75.5 s): the camera is locked
  (`from == to` is only legal when `sustain` is `assembly` and at least three distinct `attach` events exist, no more than 6 s apart).
- **No pop-in**: in the assembly shot the slider, every tooth (one after another, 3 frames apart), the pull tab, the tapes and the stops
  arrive on an arc, rotate and settle with a small spring bounce; nothing appears instantly.
- **Push-in/pull-out**: one `pushin` on the neck (88.3 s, about 5 s in, hold, out) on the same camera, no cut. The validator requires at
  least one in the plan.
- **Hold cap**: the planner prompt states the 9 s cap, and `fill_gaps()` enforces it in code by adding a neutral highlight on the nearest part
  noun. Longest stretch with no event or cut in the final plan: 7.8 s. Longest composition run: the 23 s assembly shot (it keeps building).
- **Named parts**: every part noun in the narration (cursor, cuña, diente(s), jalador, tela, topes) has an event within 3 s.
- **Ambient cycle**: `slider-cycle` (the slider travels up and back down every 4 s, teeth below it interlock, teeth above it pry apart, the pull
  tab swings) or `assembly-cycle` (parts arrive, then the same cycle). Required and checked at load.
- **Colours**: red only on the 3 `force_arrows` (the slider squeezing or prying the rows, each on a push or pull word); yellow only on the
  2 callouts (`DIENTES`, `TOPES`); pale blue for the 17 highlights; nothing flows, so no grey/white chevrons.
- **Captions**: 85 independent 2-5 word phrases grouped before the script is written; none crosses a sentence end.
- **Load-time checks** (`validate()` in `Zipper.tsx`) throw on a static camera outside assembly, a missing or wrong ambient field, fewer than
  three attach targets, an assembly stall, an accumulating caption, a non-part callout, or a missing push-in.

## Numbers

- Script 323 words, narration 118.8 s, render 4 min 25 s, 59.4 MB. 9 blocks of 9.3-23.0 s. 26 events: highlight 17, force_arrows 3,
  attach 3, term_callout 2, pushin 1. Shots: establishing 3, cutaway 3 (camera) plus 1 cutaway (assembly), insert 2.
- `verify.py`: 0 identical consecutive frames of 3579, no black frames, no audio.
- The first plan (`plan-v1-noassembly.json`) had no assembly shot: the prompt said to use it only where the narration introduces the parts one
  after another, and here the parts are named in different blocks. Making "exactly one assembly shot, on the scene naming the most parts"
  explicit fixed it; the validator then dropped 11 events and `fill_gaps()` re-added 4 highlights.

## Defects seen in the sheets

- The zipper fills the whole frame height, so the captions sit over it (the recipe says near the hero, never over it).
- The pull tab is the same grey as the slider; it only reads when it swings. The highlight boxes are large and washed out.
- In close-ups the red arrows are partly cropped by the frame edge; the denim bands are busy next to the teeth.
- The assembly shot's attaches are 5.1-5.4 s apart, between them only the slider cycle moves; the tapes and stops arrive on fixed defaults
  (the model attached only the slider, teeth and tab).
- Not watched in motion; only the 37 dense stills and three 12-frame runs at 6 fps were inspected. Font is `Inter` with fallbacks.
