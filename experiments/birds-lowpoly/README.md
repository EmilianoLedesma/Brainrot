# Why birds can perch on power lines: subject-first director v4 (134.8 s, silent, default model)

The fourth film in the "one continuous world" grammar of [`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md), made to test whether the
format stays consistent on a new topic (after [`cpu-lowpoly`](../cpu-lowpoly/README.md), [`pothole-lowpoly`](../pothole-lowpoly/README.md) and [`zebra-lowpoly`](../zebra-lowpoly/README.md)).
New here: the director identifies **the subject of the film** and the film is organised around it. A silent 1080×1920, 30 fps, 134.8 s (4045 frames) video. No queue or main-flow
integration.

Model: the **default** one (`BRAINROT_CLAUDE_MODEL` unset, `claude-code` provider) for `write_story` and the director.

## Pipeline

1. **Research** (`reference.json`): 3 WebSearch queries, then pages read through the web-fetch agent: BBC Science Focus (full Q&A, one number: 35,000 volts as an example),
   ScienceABC (a model-extracted rendering; the agent flagged loose physics such as "path of least resistance" and some unsourced claims) and the US Fish & Wildlife Service
   page on avoidance measures (full; no wingspan or spacing figures). APLIC guidance, the Physics Forums threads and the vendor pages came only from search summaries and are
   marked so. 12 paraphrased facts with source ids and notes. The explanation of why the current stays in the wire (the feet are close and the body resists far more than the
   short stretch of wire) rests on a forum search summary and is marked secondary.
2. **Script**: `write_story.py` passes those facts to `brainrot.script.write_story` as `reference_context` (level 30, factual, Spanish). Title "Por qué las aves no se electrocutan
   en cables", 338 words. Hook: a wire can carry 35,000 volts and the bird does not even ruffle. Order: voltage versus voltage difference, both feet on one wire, why the current
   stays in the wire, the open circuit, the twist (a second wire or the ground), spacing and wingspan, poles and flocks, the fixes, the linemen's bonding wand, and a closing line that
   calls the hook back.
3. **Timing**: `timing.py` (`es-MX-JorgeNeural`, audio discarded): 347 words, narration ends at 134.32 s.
4. **Director v4** (`director.py`; reuses the beat splitter, cue matcher, hold-cap fill and boundary snapping of `cpu-lowpoly/planner.py`). The new rule set, on top of the calm camera
   of the zebra film (at most 30% of the beats move, never two moves in a row, angle and height fixed inside a station, no overlapping actions on a station, arrows capped):
   - **identify the subject first**: `Film.subject` (`bird` or `eagle`, with a `why`) is part of the model's answer and is saved in `plan.json` (`subject`, `subject_model`). The
     model chose the small perched bird: "it lands, looks, grips the wire, ruffles its feathers when nothing happens and watches the eagle's danger".
   - **the subject has its own vocabulary** (`look_around`, `tilt`, `grip`, `fluff`, `hop`, `land`, `take_off`) locked to cue words, at least one in every beat of 3 s or more and two
     from 5.5 s, never overlapping each other; the stations keep theirs (current pulses, open and closed circuit, the eagle touching two wires, wingspan measure, covers, perch guard,
     bonding wand);
   - code also diversifies angles and heights across stations (never inside one) when the model does not.
   Result: 29 beats of 2.7-6.3 s; nature 4 context, 17 exhibit, 8 cutaway; 23 station actions (19 distinct); **39 subject actions in 28 of 29 beats**; camera 26 holds, 2 push-ins,
   1 pull-out; angles 9 left, 11 front, 9 right; heights 11 low, 14 mid, 4 high; 0 arrows, 7 term callouts, 4 highlights.
5. **Script and render**: `build_script.py` -> `script.json` (29 waypoints, 23 `actions`, 39 `subjectActions`, `subject`, 11 events, 89 phrase captions; flights 45 frames). `Birds.tsx`
   interprets it and throws at load if the demands are not met (a valid subject, calm camera, 3+ cutaways, 12+ distinct station actions, a subject action in most beats).

```powershell
# from the repository root
$env:PYTHONPATH="."
uv run --locked python experiments/birds-lowpoly/write_story.py      # live model call; facts come from reference.json
uv run --locked python experiments/birds-lowpoly/timing.py
$env:BRAINROT_LLM_TIMEOUT_SECONDS="900"                              # the director call is large; the default 180 s timed out once
uv run --locked python experiments/birds-lowpoly/director.py         # live model call, about 12 minutes; --revalidate re-applies the code rules to the saved beats
python experiments/birds-lowpoly/build_script.py
cd experiments/birds-lowpoly; npm ci --cache ../../out/birds-lowpoly-npm-cache; npm run render
cd ../..; python experiments/birds-lowpoly/verify.py
```

## How the subject is made the protagonist

- **Detail**: the most detailed model in the film: a 40×28 body with a painted gradient (coral breast, cream belly, blue-grey back), a head with eyes and highlights, an orange beak with
  a lower mandible, layered wings with four primary feathers each, a three-feather fan tail, and legs with toes that close around the wire (`grip`). The eagle comes from the same builder
  (white head, brown body, bigger beak), and the flock uses a muted palette of it.
- **Colour hierarchy**: the coral breast is the only saturated warm colour in an otherwise pastel scene; the potential colours (violet and teal) and the sky, grass and wood stay cool or neutral.
- **Presence**: the subject is on every stage and in the hero, framed near the centre of each stage, and in 28 of 29 beats it does something that follows the words.
- **Motion tied to meaning**: it flies in only on `land` and out only on `take_off`; poses are functions of the action and the frame (head yaw for `look_around`, head roll for `tilt`, crouch
  and toes for `grip`, a puff for `fluff`); nothing idles.
- Stages enter at the start of their beat and shrink away 30 frames after it ends, as in the zebra film, so the hero is never hidden.

## Numbers

- `verify.py`: 134.8 s, 1080×1920, 30 fps, h264, no audio, 0 black frames, no decode errors, 0 identical consecutive frames of 4045. `final.mp4` is 64.5 MB (ignored `out/birds-lowpoly/`).
- Contact sheets inspected by hand: 37 dense stills and four 12-frame runs at 6 fps; 11 test stills before the render fixed a grey breast (the colour gradient was wrong) and a hero bird that
  filled the first frame. The video was not watched in motion.
- Director cost: the first attempt timed out at the default 180 s; the successful run needed about 12 minutes.

## Defects seen in the sheets

- The subject's actions are repetitive: 5 distinct (18 `look_around`, 10 `tilt`, 5 `fluff`, 3 `land`, 3 `grip`); `hop` and `take_off` were never used and `look_around` opens most beats. The next
  director should cap how often one subject action may repeat.
- The danger stations carry less drama than the narration: the eagle's flash is a short spark and the bird leaves the frame, and the pole stage's flock and sway are small at medium distance.
- The lineman and the covers (fixes) are small and low-contrast; the translucent highlight dome hides part of the pole stage in two frames.
- 11 of 29 beats are under 4 s. One caption is a single word ("¿Cómo?", a one-word question sentence).
- Pulses along the wire are the only picture of the current; there is no picture of the voltage difference beyond the colour of the wires.
- Not watched in motion. The research facts are not checked beyond the sources listed; the physical explanation of why current stays in the wire rests on a forum summary.
