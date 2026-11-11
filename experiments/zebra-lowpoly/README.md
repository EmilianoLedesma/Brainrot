# Why zebras have stripes: soft low-poly savanna, researched facts, director v3 (147.4 s, silent, default model)

The third film in the "one continuous world" grammar of [`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md) (after
[`cpu-lowpoly`](../cpu-lowpoly/README.md) and [`pothole-lowpoly`](../pothole-lowpoly/README.md)). New here: a calmer camera, looser framing, actions that never
overlap, stages that leave the set when the story moves on, and animals built from smooth organic primitives instead of blocks. A silent 1080×1920, 30 fps,
147.4 s (4422 frames) video. No queue or main-flow integration.

Model: the **default** one (`BRAINROT_CLAUDE_MODEL` unset, `claude-code` provider) for `write_story` and the director.

## Pipeline

1. **Research** (`reference.json`): 4 WebSearch queries, then pages read through the web-fetch agent: Caro et al. 2019 (PLOS ONE; about 60% verbatim), Kojima et al.
   2019 (PLOS ONE; abstract, methods, results, discussion verbatim) and Wikipedia "Zebra" (lead and species table verbatim; the Function section only as a model
   summary). Caro et al. 2014 (Nature Communications) sits behind a login redirect and could not be read: it rests on search summaries and is marked so. 17
   paraphrased facts, each with source ids and a `note` on how solid it is.
2. **Script**: `write_story.py` passes those facts to `brainrot.script.write_story` as `reference_context` (level 30, factual, Spanish). Title "Las rayas que
   estrellan moscas", 353 words. Hook: a fly dives at a zebra and cannot land. Order: the fingerprint-like pattern, the failed hypotheses (predators, heat), the biting
   flies correlation, Caro 2019 (landing), the coats, the painted cows, and what nobody knows yet. One word to watch: "los autores calculan" for a figure the paper
   only infers.
3. **Timing**: `timing.py` (`es-MX-JorgeNeural`, audio discarded): 358 words, narration ends at 146.91 s.
4. **Director v3** (`director.py`; it reuses the beat splitter, cue matcher, hold-cap fill and boundary snapping of `cpu-lowpoly/planner.py`). Beats are at most 6.5 s.
   Per beat the model returns a nature (`context`, `exhibit`, `cutaway`), a shot (distance, azimuth, height, move) and events (`action`, `highlight`,
   `term_callout`, `arrow`). Code rules, changed from the pothole film after the feedback:
   - **calm camera**: at most 30% of the beats may use a move other than `hold`; never two moves in a row; within a station the angle and height stay fixed;
   - **no overlaps**: every action has a duration (a table in `director.py`); on a station an action may not start before the previous one has ended;
   - cutaway only for real mechanisms (the magnified skin and mouthpart, the flight paths, the stripe pattern), at least 3;
   - arrows capped at 2, none by default; actions per beat length (1 from 4 s, 2 from 6.5 s); first and last beat savanna/context/wide; hold cap 7 s.
   Result in `plan.json`: 35 beats of 2.3-6.4 s; nature 7 context, 17 exhibit, 11 cutaway; 30 actions, 20 distinct; camera 32 holds, 2 push-ins, 1 pull-out
   (the closing one); angles 5 left, 12 front, 18 right; all beats at mid height (the model never asked for low or high); 0 arrows, 5 highlights, 9 term callouts.
5. **Script and render**: `build_script.py` -> `script.json` (35 waypoints with `nature` and `shot`, 30 `actions`, 14 events, 89 phrase captions; flights last 45
   frames). `Zebra.tsx` interprets it and throws at load if the demands are not met (first beat, calm camera, 3+ cutaways, 12+ distinct actions).

```powershell
# from the repository root
$env:PYTHONPATH="."
uv run --locked python experiments/zebra-lowpoly/write_story.py      # live model call; facts come from reference.json
uv run --locked python experiments/zebra-lowpoly/timing.py
uv run --locked python experiments/zebra-lowpoly/director.py         # live model call; --revalidate re-applies the code rules to the saved beats
python experiments/zebra-lowpoly/build_script.py
cd experiments/zebra-lowpoly; npm ci --cache ../../out/zebra-lowpoly-npm-cache; npm run render
cd ../..; python experiments/zebra-lowpoly/verify.py
```

## The world and the models

- A savanna: pastel grass, a waterhole, rocks, acacias with flat canopies far behind, grass tufts, hills, clouds. The hero is a herd of four zebras at the waterhole.
  In front of it, one round grassy stage per idea; every stage keeps its subjects inside about +-8 units, which is about 75% of the frame width at `medium`.
- Animals are not boxes: smooth ellipsoid bodies, tapered legs, necks, heads, snouts, ears, manes, tails and hooves from spheres, cylinders and cones, with the
  stripes painted per vertex (vertical bands on the torso that curve slightly, horizontal bands on the legs, a black muzzle). A horse, a cow, a lion and a hyena share
  the builder. A fly has a thorax, abdomen, big eyes, two thin wings and a mouthpart that can extend.
- Distances leave margin: wide 112, medium 88, close 62 (the hero is framed closer, x0.66). The pothole film used 50/34/17 and filled the frame.
- Stages enter when their beat starts (a soft spring drop-in) and shrink away 30 frames after it ends; a quick return reuses the same stage. Without this, the
  earlier stages pile up in front of the savanna (seen in the first render of this film). What an action already did is kept for the next visit.
- Nothing moves on its own: a lion only walks during `lion_stalk`, legs swing only while an animal is walking, wings beat only while a fly flies, the fly in the hook
  exists only during `fly_strike`. 20 actions across 8 stations: fly_strike, herd_move; pair_in, pattern_trace; lion_stalk, haze; sun_up, temps_read; fly_land,
  bite; approach, horse_land, zebra_bump, ring; coats_on, flies_test, head_test; paint, swarm, fade.
- The landing stage draws the flies' paths as dots at equal time steps: they bunch up on the horse (the fly slows down) and stay evenly spaced on the zebra (it does not).

## Numbers

- `verify.py`: 147.4 s, 1080×1920, 30 fps, h264, no audio, 0 black frames, no decode errors, 0 identical consecutive frames of 4422. `final.mp4` is 65.0 MB
  (ignored `out/zebra-lowpoly/`).
- Contact sheets inspected by hand: 37 dense stills and four 12-frame runs at 6 fps; 22 test stills before the renders. They fixed zig-zag stripes, subjects cropped by the
  stage, a tiny hero herd and fly, and the stage pile-up. The video was not watched in motion.

## Defects seen in the sheets

- Flights between far stations cross empty grass (the stages are 20 units apart and the camera flies at one speed), so a few frames show only ground and sky.
- The director used only the `mid` height and mostly the `right` angle: calm, but flat. The framing rule held (nothing is cropped), at the price of small animals in the wide
  predators stage and the lion reading as a cub.
- The skin patch for the hair detail is a pink pad with spikes and a grey fly: it reads as "hair" only with the caption. The fly is still a dark blob at distance.
- The cow looks like a short, heavy blob; the painted cow does read as striped, but the 6-versus-3 fly counts are hard to see at that size.
- 18 of 35 beats are under 4 s, where an action is not required by rule.
- Not watched in motion. The research facts are not checked beyond the sources listed; the Caro 2014 paper itself was not read.
