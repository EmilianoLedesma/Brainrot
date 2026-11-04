# Shock absorber low-poly (146.97 s, silent, script and plan by Opus 5.5)

How a car's shock absorber works and why it damps bumps instead of letting the car keep bouncing. A silent 1080×1920,
30 fps, 146.97 s (4409 frames) low-poly explainer built from the consolidated
[`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md). The script comes from Brainrot's real
generator, the word timings from its TTS (audio discarded), the shot plan from a planner modelled on `brainrot/motion.py`.
No queue or main-flow integration.

## Model used (deliberate, for this run only)

`BRAINROT_CLAUDE_MODEL=claude-opus-5-5` with the `claude-code` provider, so both `llm.generate()` calls, the script
(`brainrot.script.write_story`, level 30 = Playful, factual) and the scene design (`planner.py`), ran on Opus 5.5 instead of the
default. Nothing else changed provider: `edge-tts` is not a model. The run changes the model AND adds the recipe/planner fixes at
the same time, so the effects below are not isolated; each finding is tagged as likely recipe-driven or model-driven.

## Pipeline

1. **Script**: `write_story` with the factual explanation as reference context (`story.json`): "El resorte que nunca deja de
   rebotar", 366 words. Checked against the storytelling skill before use (concrete hook, causal progression, earned ending): passed.
2. **Timing**: `timing.py` (`brainrot.tts.narrate`, `es-MX-JorgeNeural`, audio discarded) -> `words.json`: narration ends at
   146.48 s at the default rate (no slowdown needed). Video = narration + 0.5 s tail.
3. **Plan**: `planner.py` (`motion.plan()` groups words into blocks, `design()` asks the model for a shot type and at most one
   event per block as a Pydantic model, validated) -> `plan.json`.
4. **Script and render**: `build_script.py` -> `script.json` (shots with `camera.from/to`, `ambient`, `environment`; 95 phrase
   captions; events); `ShockAbsorber.tsx` interprets it. Remotion 4.0.538, `@remotion/three`, `three` 0.187.0.

```powershell
# from the repository root; the planner defaults to claude-code, SHOCK_PLANNER_PROVIDER=codex switches
$env:PYTHONPATH="."; $env:BRAINROT_CLAUDE_MODEL="claude-opus-5-5"
uv run --locked python experiments/shock-absorber-lowpoly/timing.py
uv run --locked python experiments/shock-absorber-lowpoly/planner.py        # --reuse re-validates the saved plan
python experiments/shock-absorber-lowpoly/build_script.py
cd experiments/shock-absorber-lowpoly; npm ci --cache ../../out/shock-absorber-lowpoly/npm-cache; npm run render
cd ../..; python experiments/shock-absorber-lowpoly/verify.py               # measurements + dense and fluidity contact sheets
```

`out/` is ignored by Git; `story.json`, `words.json`, `plan.json` and `script.json` are small tracked data files.

## Numbers

- Script 366 words; narration 146.48 s at the default rate; render 5 min 10 s, 44.8 MB.
- Planner: **12 blocks** of 7.6-17.8 s (the `plan()` default 11 s target was lowered to 8 s). Shots: cutaway ×8, establishing ×3,
  insert ×1, metaphor ×0. Events: force_arrows ×5, term_callout ×4 (`RESORTE`, `AMORTIGUADOR`, `PISTÓN`, `ACEITE`),
  flow_chevrons ×2, damp ×1. The validator made no corrections.
- 95 independent caption phrases (2-5 words, one single word), each replacing the previous.
- `verify.py` on the final MP4: 0 identical consecutive frames of 4409 (longest identical run 0), no black frames, no audio.

## What the recipe fixes did (recipe-driven)

- **Camera**: one move per shot over its whole duration (`camera.from` -> `camera.to`), unaffected by the caption rhythm;
  identical poses throw at load.
- **Ambient work cycle**: every shot has `ambient: {kind, period, moving}`; the scene runs a repeating 2 s cycle, a bump kicks the
  wheel, the piston strokes through the oil, the spring compresses and the suspension rings down. The fluidity sheet (6 fps, inside
  one establishing, one cutaway and one insert shot) shows a different pose in every frame of each run.
- **Phrase captions** are grouped from the word timing before the script is written, so accumulation cannot occur.
- **Environment**: establishing has wheel, suspension arm, chassis, road and coil spring; cutaway has coil spring, chassis mount, wheel
  hub mount and outer tube.
- **Colour**: red only on force arrows, yellow only on the four part-name callouts (checked against a parts list at load),
  grey/white only on the oil-flow chevrons.
- **Damping**: the suspension rings (spring alone) until the `damp` event at 93.6 s, then settles quickly in every shot.

## Model-driven or recipe-driven? (to discuss)

- The callouts were all real parts and needed no override, unlike the foil run. This is confounded: the planner guidance now carries
  an explicit parts list, so it may be the guidance, not the model.
- The model put the `damp` event at "frena cada rebote" (93.6 s), late: "Aquí entra el amortiguador" at 33 s would fit the story better.
  Looks model-driven.
- Variety is the same as before: 8 of 12 blocks are cutaways, one insert. Looks model-and-planner-driven, not recipe-driven.
- Five of 12 events are `force_arrows`; the model leans on arrows and used `flow_chevrons` only twice, although oil flow is the core
  of the mechanism.
- The script itself (hook, causal order, payoff) was strong on the first generation. Could be the model or the reference context.

## Defects seen in the sheets (mine, not the model's)

- **The red force arrows are nearly invisible**: in the cutaway they sit above the chassis plate and are cut by the top edge, so five of
  the twelve events barely register.
- The hero is small: the cutaway damper fills about 40 % of the frame width with empty teal above and below.
- The cutaway "wheel hub mount" is a plain grey block, not a recognisable wheel; the half-circle spring rings read oddly.
- The flow chevrons are clear in the insert but small in the cutaway.
- One phrase is a single word; the `damp` event has no on-screen marker other than the suspension settling.

## Model comparison (planner, no render)

Follow-up run to separate the model from the recipe fixes: the same `words.json`, two Opus 5.5 runs and two default-CLI-model runs
(`plan-opus*.json`, `plan-default*.json`), then a stricter v2 planner (`planner.py --v2`: up to three events per block, the 8-10 s
no-event cap, noun acknowledgement and `damp` exactly once written into the prompt, word timestamps shown) four more times
(`plan-v2*.json`). `audit.py` measures every plan against the recipe rules; results in `audit.json`.

- **v1 (one event per block, rules not in the prompt):** the default model returned placeholder beats, `none` events and leaked reasoning
  in `why` on 2-4 of 12 blocks; Opus returned a real event on every block. Both broke the 10 s cap (68-99 s in stretches over 10 s),
  acknowledged only 6-9 of 11 technical nouns, and placed `damp` late (93.6 s Opus, 113.8 s default).
- **v2 (rules in the prompt):** all four plans pass: longest stretch without an event 8.8 s, 11 of 11 nouns acknowledged, `damp` at about
  53 s, no validator corrections, no placeholders. The earlier gap came from prompt specificity, not capability.
- **Shared weakness:** `force_arrows` is 19-21 of 32-36 events: many are filler arrows on nouns ("importa", "largo"), duplicates at the same
  second, or flow chevrons on "calor"/"popote". The default model alternates shot types better (0 cuts back to the same type vs 1) but
  repeated `ACEITE` three times in one run. Suggested fix: a neutral part-highlight event so naming a part does not borrow red arrows.
- Two runs per model; the v2 prompt states the checks the audit measures. The renderer only draws the first event of each kind per
  shot, so the v2 plans have not been rendered.
- `build_script.py` now folds one-word leftovers into a neighbour of the same sentence (the old merge produced "perfecto El problema
  viene después"). `final.mp4` was rendered before that fix, so its captions still contain the old merge; `script.json` is rebuilt.

## Limits

- Not watched in motion; only the two contact sheets (36 dense stills, three 12-frame runs at 6 fps) were inspected.
- Font is `Inter` with `Segoe UI`/`Arial` fallbacks; not bundled.
