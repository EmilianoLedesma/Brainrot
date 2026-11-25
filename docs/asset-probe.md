# Asset probe: the model authors each video's 3D assets

Status: experiment, 2026-11-25. Not wired into the pipeline. Everything here runs by hand with `scripts/asset_probe.py`.
Context: [world director redesign](world-director-redesign.md) (the generic renderer this probe tries to replace) and [world mode](world-mode.md).

## What we are testing

**Question.** Can the strong-tier model (Claude: Opus, through the user's own signed-in Claude CLI) design and write the 3D assets of any topic, so that videos of any subject look as polished and as consistent as the hand-built packs, without a fixed asset library and without a person writing packs?

**Why it was asked.** The user's earlier tests (generic world path, `brainrot/world/spec.py` + `motion/world/packs/generic.tsx`) gave poor and inconsistent results even when the recipe was followed, while hand-written packs (`zebra.tsx`, `Pothole.tsx`, the HyperFrames pressure cooker, the moka cutaway) looked good. He did not want a library ("topics vary"), and did not want packs made outside the pipeline.

**Root cause found before the probe (2026-11-25, silent 10 s tests).**
- The Claude CLI is not what limits the director. The cap is the generic renderer: five presets plus box, ball, cylinder, cone and disc (limits: 12 pieces, 10 parts per piece, 48 parts per station), and camera framing constants (aim, distance, position) that are not tied to the size of what is shown (a sun out of frame, a hero too small).
- Design details that also hurt: the beat schema puts `why` after the decisions; the director cannot see images; beats are chunked in nines; code overrides model choices.

**Hypothesis.** Let the model write the assets as code against a small restricted kit with two worked examples, frame every shot automatically from the bounding box of the group it shows, then let the model look at the result (stills plus a time strip of the clip) and fix it. Later, the director would direct over assets that were approved this way.

## How the probe works

`uv run python scripts/asset_probe.py --topic "..." --text "<about 25 words of narration>" [--video] [--resume] [--no-review] [--stub reply.json]`

1. **Design.** One strong-tier call returns `designed.tsx` (the scene) and `notes` (recognition features, a plan `narration part -> shot -> action`, scale and layout decisions). The system prompt holds the rules, `motion/probe/kit.tsx` and two examples (`examples/puente.tsx`: diorama, layout and a timed action; `examples/olla.tsx`: cutaway technique).
2. **Static check.** Imports other than `react` and `./kit` are refused, as are tokens that reach the network, the page or the machine (`fetch(`, `eval(`, `window`, `document`, `process`, `Math.random`, `Date`...), missing exports, and shots that point at a group that does not exist. Failures go back to the model as a repair round (at most two).
3. **Render.** Remotion renders one still per shot (`--sequence`, 1080x1920 at scale 0.5). Cameras are computed from the group's bounding box (`motion/probe/index.tsx`), so the model only chooses `focus`, `az`, `el` and optionally `zoom` and `dy`.
4. **Clip and review.** A silent 10 s clip is rendered and eight frames become `time.png`. The model reads `sheet.png` and `time.png` with the CLI's `Read` tool (confined to a temporary folder holding only those images) and answers `ok` or `fix` with at most five concrete problems. If the CLI cannot read images the review is skipped, not fatal.
5. **Fix.** One call returns a patch (parallel `old` and `new` snippet lists), not the whole file, because a full rewrite of a 14,000-character scene took more than 15 minutes and timed out. A failed or empty patch keeps the first version and still writes `report.json`.
6. **Output.** `out/asset-probe/<topic>/` (`designed.tsx`, `sheet.png`, `sheet-v1.png` before the fix, `time.png`, `clip-silent.mp4`, `report.json`). `--resume` skips the design call and reuses that folder's `designed.tsx`.

Model calls per run: design, up to two repairs, review, fix (at most four). Timeouts: design 1500 s, fix 900 s, review 600 s.

**Kit (`motion/probe/kit.tsx`).** Shapes `Ball RBox Cyl Cone Capsule Torus Lathe HalfCyl Tube G`; environment `Slab` (ground block with visible layers), `Planks`, `Tiles`, `Scatter`, `Pine`, `Tree`, `Rock`, `Mound`, `Cloud`; motion `Act` (keyframes over the clip), `Move` (travel, loops, spin, bob, sway, pop), `useTime`, `ramp`, `mix` (gradual colour change). The harness provides time, a sky gradient and optional ground; per shot the camera slowly pushes in and drifts.

## What the reference videos taught (user's `Examples/` folder)

The folder has 14 short vertical explainers by other creators (candle lighter, ballpoint pen, taxi waiting time on a map, pressure cooker, bridge, mine rescue drill, drain trap, microwave and coffee machine, toaster, tunnel, tree house). The videos are third-party works: they are not in this repository (it is public) and `Examples/` is git-ignored. What was extracted and turned into prompt rules:
- The world is a diorama with structure: a ground block with a visible cross-section (soil layers), a textured surface (table grain, tiles, grass), a sky with clouds, scenery that says where it happens. Never an empty plane.
- Macro scale: one big hero, one idea per shot, angles that change from shot to shot.
- Motion is the explanation and is synced to the words: the car crosses when the narration says so, the flame lights, bubbles rise, a part slides in. No idle wobble.
- A restrained palette per video with value contrast between ground and sky; small figures only for scale.

## Results so far (4 topics, one run each; the prompt changed between runs)

Files in [`docs/asset-probe/results/`](asset-probe/results/): `sheet-v1.png` (first version), `sheet.png` (after the fix round), `time.png`, `clip.mp4`, `designed.tsx`, `report.json`. Earlier hand-made prototype for comparison: [`prototype-topics-sheet.png`](asset-probe/prototype-topics-sheet.png).

| Topic | Prompt state | Outcome |
| --- | --- | --- |
| Snow goggles of the Inuit (`inuit-goggles`) | kit with `Move`, plain-plane ground; saved files are the second run (the first run's files were overwritten) | Weakest. The saved run has a washed-out flat background with a translucent curved backdrop, a character floating above its shadow (harness bug: the ground was moved to the lowest object; fixed), a generic blue-cone figure, goggles that read as a visor, a tiny wide shot and an unreadable macro. The first run (not saved) had arrows in every shot, a too-small igloo and everything packed together; its fix round shrank and packed objects to satisfy framing. |
| Octopus camouflage, before (`octopus-before`) | same, flat sand ground | Recognisable octopus (eyes, suckers, curling arms), a chromatophore disc prop, red to grey-tan change reads. Flat sand, tiny wide shot, mantle cropped in close-up. |
| Octopus camouflage, after (`octopus-after`) | diorama, scenery and `Act` rules | Uses `Slab`, `Scatter`, `Act`, sky gradient; plan notes by narration part; fix round clearly improved the first version. Still: the octopus ends grey on pale sand (not matching its surroundings), colour change as shells with seams, one arm left orange, chromatophore macro hard to read, empty sky under the island in the wide shot, last two seconds almost static. 909 s in total (design 632 s). |
| Cash machine (`atm`) | adds `useTime`, `mix`, story rules, review with `time.png` | Best so far: a plaza with a bank and antenna, buildings, trees, bench, lamp posts, a person with a backpack, 27 `Act` calls, gradual screen state. Weak: the card reader close-up crops the machine and the arm has no body, the bank link is a faint dotted line, the screen jumps from blank to a check mark, the cash is tiny, scenery is thin outside the plaza. The fix round hit the 900 s timeout and the run crashed after the review; first version and review text were kept (no `report.json` for this run). This led to patch-style fixes, failure tolerance and `--resume`. |

**Reading of the evidence (n=1 per topic, so a direction, not a measurement).**
- Per-topic generation is viable: recognisable props, structured worlds and timed actions appeared without a library. Quality tracked the subject: machines and animals better than the human figure.
- The prompt rules visibly changed behaviour (diorama, plan by narration part, gradual colour). The review caught framing, scale and readability problems; before the story rules it missed that the demonstration did not prove the claim.
- The fix round can improve, regress or time out. It is the slowest and least reliable step.
- Cost is high: 4 to 15 minutes of wall time per topic and two to four strong-tier calls. Token cost was not measured.

## Next tests (two more topics, one with people and one without)

Run each topic once with the current prompt, and repeat one of them to see variance. Compare against the success criteria:
- the design uses `Slab`, `Scatter`, `Act` and `useTime`, and `notes` has the plan `part -> shot -> action`;
- wide shot: the hero is at least a third of the frame width and no empty sky or void shows under the ground;
- the change the narration describes is visible, gradual and logical (the camouflaged subject ends up where it matches); no part is left unchanged;
- no floating characters, no arrows (at most one), no cropped hero in close-ups;
- the review and the patch fix finish within the timeouts and the first version is kept if they fail.

Record each run in the handoff with the topic, prompt state, wall time, model calls, what failed and what held.

## Open questions and risks

- **Security.** The scene is model-written code executed in the Remotion headless browser. The static check is a regex allowlist, not a sandbox. `docs/world-mode.md` and `brainrot/world/spec.py` promise that model-written code is never executed; this probe is an explicit, local, manual exception. Do not connect it to the pipeline before choosing between a restricted sandbox (no network, no file access) and a richer declarative scene format.
- **Human figures** are the weakest part; a well-built figure example may be needed in the prompt.
- **Cost and time**: the design call is long (up to about 10 minutes). Options: shorter exemplars, a lower-effort setting if the CLI offers one, or splitting the scene into per-object calls.
- **Review blind spots**: motion is judged from eight frames only; logic errors are caught only if the review rules ask for them.
- **Not built**: the director over approved assets, audio, automatic repeat runs, unit tests for `scripts/asset_probe.py` (only stub runs in a cloud container were done), a Sonnet-versus-Opus comparison, license check before copying code from the reference repositories (`claude-animated-shorts` and `claude-animation-skills` are MIT; the `lemo-opuscar` documents are CC-BY-NC).

## Running it

1. `npm ci --prefix motion`, a signed-in Claude CLI (`claude auth status` shows `claude.ai`), Python with the project dependencies, Chrome (set `BRAINROT_BROWSER` to its path if it is not found).
2. `python scripts/asset_probe.py --topic "Cómo funciona un cajero automático" --text "..." --video`
3. Rename a topic's output folder before repeating the topic if you want to keep the earlier run.
4. The script forces `--provider claude-code`. The main flow rejects `BRAINROT_LLM_PROVIDER=''` (an empty value is not "unset" for `llm.generate`); leave the variable out or set `claude-code`.
