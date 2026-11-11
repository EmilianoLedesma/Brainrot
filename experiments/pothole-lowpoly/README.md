# Potholes, one continuous world, researched facts, director v2 (136.2 s, silent, default model)

How potholes form, in the "one continuous world" grammar of [`docs/motion-graphics-recipe-lowpoly.md`](../../docs/motion-graphics-recipe-lowpoly.md),
the same one as [`cpu-lowpoly`](../cpu-lowpoly/README.md). The script is grounded on **researched, sourced facts**; the world is a town (street, car,
houses, trees, poles, hills) with a sidewalk of road-block exhibits; and a stricter **director v2** decides the nature of every scene, the camera and
what moves. A silent 1080×1920, 30 fps, 136.2 s (4086 frames) video. No queue or main-flow integration.

Model: the **default** one (`BRAINROT_CLAUDE_MODEL` unset, `claude-code` provider) for `write_story` and the director.

## Pipeline

1. **Research** (`reference.json`): 3 WebSearch queries, then two pages read in full through the web-fetch agent: Practical Engineering ("How Do
   Potholes Work?", Wesley Crump, 2020) and Wikipedia ("Pothole", about 40k of 73.7k characters; the unread tail is references). Tensar (industry)
   and an FHWA LTPP summary came only from search summaries, so facts that rest on them are marked `single` or kept general. 17 paraphrased facts,
   each with its source ids. "Alligator cracking", "pumping of fines" and "blocks breaking out" are not in the Practical Engineering page; the
   script says "piel de cocodrilo" and "bombea" from Wikipedia and that page's wording respectively.
2. **Script**: `write_story.py` passes those facts to `brainrot.script.write_story` as `reference_context` (level 30, factual, Spanish). Title "El
   bache nace bajo el asfalto", 332 words. Hook: "Ese hoyo que acabas de esquivar no empezó en la superficie."
3. **Timing**: `timing.py` (`es-MX-JorgeNeural`, audio discarded): 338 words, narration ends at 135.71 s.
4. **Director v2** (`director.py`, which reuses `planner.py` and, through it, `cpu-lowpoly/planner.py` for beat splitting and the hold-cap fill). Beats
   are split to at most 5.5 s. For each beat the model returns:
   - the **nature** of the scene: `context` (the town as a whole), `exhibit` (a road block performing the idea) or `cutaway` (the block is cut open
     and we look inside), chosen from what the narration does; cutaway is for "how does it work / what is it made of";
   - a **shot**: distance, azimuth (left/front/right), height (low/mid/high) and a **move** inside the beat (push_in, pull_out, orbit_left/right,
     pan_left/right, crane_up/down, drift);
   - **events** locked to cue words: `action` (a named action of that station), `highlight`, `term_callout` and `arrow`.
   Code then enforces: nature vs distance (context = wide, cutaway = close, road is always context), at least 8 cutaways on at least 5 stations
   (promotes beats if the model used fewer), actions per beat length (1 from 3.5 s, 2 from 5.5 s, filled with defaults and a note otherwise), no
   repeated camera pose, no third beat on the same side, drift limited to a quarter of the beats, at most 3 arrows and only on a flow word, first and
   last beat road/context/wide, a `patch_street` action somewhere, and a 6 s hold cap. Result in `plan.json`: 37 beats of 2.3-5.5 s; nature 5 context,
   17 exhibit, 15 cutaway (on 6 stations); 31 actions, 23 distinct; 9 camera moves (all used, drift only 3 times), 12/13/12 beats by angle and
   10/16/11 by height; 0 arrows, 9 highlights, 9 term callouts.
5. **Script and render**: `build_script.py` -> `script.json` (37 waypoints with `nature` and `shot`, 31 `actions`, 18 events, 90 phrase captions).
   `Pothole.tsx` interprets it and throws at load if the director's demands are not met (first beat, distinct consecutive shots, 6+ moves, 8+ cutaways,
   18+ actions).

```powershell
# from the repository root
$env:PYTHONPATH="."
uv run --locked python experiments/pothole-lowpoly/write_story.py     # live model call; facts come from reference.json
uv run --locked python experiments/pothole-lowpoly/timing.py
uv run --locked python experiments/pothole-lowpoly/director.py        # live model call; --revalidate re-applies the code rules to the saved beats
python experiments/pothole-lowpoly/build_script.py
cd experiments/pothole-lowpoly; npm ci --cache ../../out/pothole-lowpoly-npm-cache; npm run render
cd ../..; python experiments/pothole-lowpoly/verify.py
```

## The look (softer than the first version)

Rounded boxes (`RoundedBoxGeometry`, cached) for blocks, houses and the car, faceted icosahedra only for rocks, tree crowns and clouds; a hemisphere light
plus a softer directional light, percentage-closer shadows with a blur radius, fog, a gentler palette and a navy caption stroke instead of black. Blue is
the content colour (water), yellow only for term callouts, white translucent highlights, red only for rare arrows (none in this render).

## Motion that follows the script

- Nothing moves on its own. The car only exists during a `car_pass` action; a wheel appears only during its action; cloud and rain, truck and cones,
  sealant, the drain flow and the new asphalt layer all come from actions. An exhibit with no action in progress rests.
- Each action has a fixed duration and is either persistent (cracks grown, pool risen, ice lifted, patch filled stay) or transient. 23 actions across
  9 stations: car_pass, patch_street; reveal, wheel_pass, wear; crack_grow, flex; rain, seep, pool; press, pump, erode; loosen, eject; freeze, thaw;
  truck_in, throw, roll; seal, drain, thicken.
- A `cutaway` beat slides the block's front half away and shows the interior: packed base rocks, soil grains, asphalt aggregate, fissures, water cubes
  between the rocks, the void, the ice lens. The slide is eased in and out around the beat so there is no pop.
- The camera has a pose per beat (azimuth, elevation, distance, target); flights blend one pose into the next in 36 frames and the beat's move runs
  inside the beat. No hard cuts.

## Numbers

- `verify.py` on the v2 render: 136.2 s, 1080×1920, 30 fps, h264, no audio, 0 black frames, no decode errors, 0 identical consecutive frames of 4086.
  `final.mp4` is 90.8 MB (ignored `out/pothole-lowpoly/`).
- Contact sheets inspected by hand: 37 dense stills and four 12-frame runs at 6 fps; 12 stills before the render fixed a washed-out image (light too
  strong, near-white sidewalk), floating crack lines in cutaways and z-fighting on the void. The video was not watched in motion.
- Earlier versions are kept for comparison: `plan-v1-director1.json` and `script-v1-director1.json` (first director, 31 beats, ambient loops, hard look).

## Defects seen in the sheets

- The street is patched at 134 s (the last beat), so the patched street is on screen for about two seconds; the director put `patch_street` only there.
- Cutaway beats are tight (close distance): the exhibit fills the frame and is sometimes cropped; the town is only a backdrop in those.
- 19 of 37 beats are under 3.5 s, where an action is not required by rule; 9 of those have no action (some only a highlight).
- Not every action is easy to read in one pass: `wear` and `roll` are subtle, and `thaw` leaves only a thin dark void.
- Still silent and not watched in motion; the research facts are not checked beyond the sources listed.
