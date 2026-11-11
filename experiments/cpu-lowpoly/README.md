# CPU low-poly, one continuous world (161.6 s, silent, default model)

How a processor works: transistor, logic gates, adders, ALU, clock, control unit and program counter, registers, cache, RAM, pipeline,
cores, heat and heatsink. A silent 1080×1920, 30 fps, 161.57 s (4847 frames) low-poly explainer. It is the first test of the
"one continuous world" grammar in [`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md): no cuts, one
camera that flies between stations, parts that arrive once and stay. The reference is a microwave explainer (`@stupydoo`) that has no hard
cut in 164 s. No queue or main-flow integration.

Model: the **default** one (`BRAINROT_CLAUDE_MODEL` unset, `claude-code` provider) for `write_story` and the planner.

## Pipeline

1. **Script**: `write_story.py` calls `brainrot.script.write_story` (level 30, factual, Spanish) with a short list of established facts as
   reference. Title "Dentro de tu procesador no hay inteligencia", 367 words. The hook is an unanswered mechanism ("no sabe qué es una
   foto... y aun así los muestra todos") and the ending calls it back. Two flags in the text: it says "miles de millones de transistores"
   at the start and "millones de interruptores" at the end, and the closing "mil millones de pulsos por segundo" is 1 GHz, below a modern chip.
2. **Timing**: `timing.py` (`brainrot.tts.narrate`, `es-MX-JorgeNeural`, audio discarded) -> `words.json`: 374 words, narration ends at
   161.08 s at the default rate.
3. **Plan**: `planner.py` -> `plan.json`. `motion.plan()` blocks, then `split_long()` cuts any block over 6.5 s at the longest pause near its
   middle, then the model returns per beat a focus station, a distance (`wide|medium|close`), a one-line description and up to three events
   (`highlight`, `force_arrows`, `term_callout`). Code validates it. 37 beats of 2.2-6.5 s.
4. **Script and render**: `build_script.py` -> `script.json` (37 waypoints, 103 phrase captions, 44 events; captions use the zipper
   experiment's grouper). `Cpu.tsx` interprets it. Remotion 4.0.538, `@remotion/three`, `three` 0.187.0.

```powershell
# from the repository root
$env:PYTHONPATH="."
uv run --locked python experiments/cpu-lowpoly/write_story.py      # live model call
uv run --locked python experiments/cpu-lowpoly/timing.py
uv run --locked python experiments/cpu-lowpoly/planner.py          # live model call; --reuse re-applies the hold-cap fill to the saved plan
python experiments/cpu-lowpoly/build_script.py
cd experiments/cpu-lowpoly; npm ci --cache ../../out/cpu-lowpoly/npm-cache; npm run render
cd ../..; python experiments/cpu-lowpoly/verify.py                  # measurements + dense and fluidity contact sheets
```

`out/` is ignored by Git; `story.json`, `words.json`, `plan*.json` and `script.json` are small tracked data files.

## The world

- A desk with a wall behind it, a motherboard with the chip (hero) in the middle, and a workbench in front. The workbench holds 12 stations
  in the order the narration names them; the camera walks along it. Environment: tiled wall, planked desk, mug, pencil, wall outlet.
- Camera: a fixed isometric-style direction (fov 24). Each beat is a waypoint; the camera leaves 12 frames before the beat starts, flies
  for 36 frames with an ease, and a global slow yaw and breathing keep it moving between waypoints.
- Parts arrive on an arc with a spring bounce when the camera first heads for them (or 20 frames before their first event) and stay. The
  chip's lid lifts and slides aside at 8.3 s; the heatsink flies from its station onto the chip at 145.7 s.
- Hook: three floating icons (photo, game, text) stream black and white cubes into the chip, then shrink away.
- Every part has a repeating work cycle: transistor lever and current, gates with a travelling pulse, adder bits and carries, ALU
  with a changing +/- and lights, clock needle and pulses, program-counter pointer stepping over memory cells, register slots, cache levels
  lighting in turn, RAM cells, conveyor of instructions, core tiles, spinning fan.
- Colours: lime is the current and "on" state; red only on 9 `force_arrows`; yellow only on 10 term callouts; pale blue for 25 highlights.

## Planner decisions

- The approved first plan had 13 hard-cut shots (`plan-v2-13shots.json`, assembly shot included; the very first plan without an assembly shot is
  `plan-v1-noassembly.json`). It was replaced before building, because the reference has no cuts. Two further plans are kept for comparison:
  `plan-v3-22beats.json` and `plan-v3b-24beats.json` (beats from sentence ends only, averaging 7 s, too sparse).
- Two validator bugs were fixed on the way: "sumadores" mapped to `gate` left the assembly shot with two distinct targets (now `adder` is
  its own station), and a same-kind-within-1.5-s rule dropped the second `attach` when the narration says two parts 1.2 s apart.

## Second pass (fixes after the first render)

The first render is kept as `plan-v4-first-render.json` and `script-v4-first-render.json`. Changes:

- Planner: `--revalidate` re-applies the validator to the saved raw model beats with no model call. `snap_boundaries()` moves a beat boundary to
  0.3 s before a word whose station the next beat focuses, so the TRANSISTOR callout now lands when the transistor is on screen (14.1 s, was on
  the chip). A callout no longer collides with an on-part effect, which brought back REGISTRO (10 callouts instead of 9).
- Camera: lower pitch (more wall), `wide` 46 / `medium` 32 / `close` 20, and a `close` on a station wider than 8 units backs off by 1.3.
- World: keyboard, mouse, notebook, two wall frames and a plant fill the empty desk.
- Pipeline: the belt forks; a cone guesses a side, and on every second 8 s cycle a dark cube takes that side and is thrown off (wrong guess).
- Heat: from 130 s the die turns orange and warm cubes rise from it (from the heatsink top after it is installed). Orange is a heat colour,
  not one of the reserved force/term/flow colours.

## Numbers

- `verify.py` on the second render: 161.57 s, 1080×1920, 30 fps, h264, no audio, 0 black frames, no decode errors, 0 identical consecutive
  frames of 4847. `final.mp4` is 74.4 MB (ignored `out/cpu-lowpoly/`). 37 waypoints, 44 events (25 highlight, 10 term_callout, 9 force_arrows).
- Contact sheets inspected by hand: 37 dense stills and four 12-frame runs at 6 fps around flights (into transistor, clock, pipeline, back
  to chip). The video was not watched in motion.

## Defects still seen in the sheets

- Some `wide` and `medium` frames still show a lot of orange desk; the heatsink `close` shots fill the frame with the fan.
- The pale-blue highlight boxes are large and flat; captions in white sit over the cream bench in some frames.
- The wrong-guess cube is small and dark in `wide` pipeline shots; only the fork and the cone read clearly.
- Script flags remain: "miles de millones de transistores" at the start versus "Millones de interruptores" near the end, and the closing
  "mil millones de pulsos por segundo" (1 GHz). Fixing them means regenerating the script and the timing, so the plan would change too.
- Fast flights along the whole bench were not checked for blur in motion.
