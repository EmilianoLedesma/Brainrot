# Continuous 3D world edit

An experimental H2 option for generated stories. Instead of a background clip or keyword cards, the chapter becomes one 3D scene without cuts: a researched script,
a director that decides what the viewer sees at every beat, and a Remotion + three.js renderer that follows the narration word by word. It is chosen per job
(`params.world`, UI label "Continuous 3D world"), is mutually exclusive with `params.motion_graphics`, and applies to generated stories only. Web research is a separate
per-job option (`params.web_research`) that also works with the other edits.

## Flow

```text
write story (optionally after web research)      brainrot/investigate.py, pipeline.run_brainrot
narrate                                          tts.narrate (unchanged)
direct (stage "direct")                          brainrot/world/director.py
render (stage "render")                          brainrot/world/render.py -> motion/world/
upload, schedule                                 unchanged
```

- **Research** (`web_research`): `investigate.run` asks the selected local CLI (Claude or Chat GPT) to search and read pages with its own web tools, nothing else enabled
  (`llm.generate(..., web=True)`; the API provider is refused, never substituted). The answer is validated in code: http(s) sources only, every fact must cite a listed source,
  at least six facts, otherwise a friendly `PermanentError`. The writer receives the facts with their caveats as `reference_context`. It runs inside the `script` stage, so a retry
  reuses the saved story and never researches twice. Guidance: `skills/research/SKILL.md`.
- **Pack choice**: `director.choose_pack` asks the model which scene pack fits the topic, or `none`. No fitting pack stops the job with a friendly message; it never falls back
  to another edit by itself.
- **Direction** (`skills/world-direction/SKILL.md` plus the pack manifest): the model chooses, per beat of the narration, the station in focus, the scene nature
  (`context`, `exhibit`, `cutaway`), a camera shot (distance, angle, height, move), actions locked to cue words, highlights, term callouts and, rarely, arrows. With a subject pack
  it first names the subject (for example the small bird) and gives it its own actions. Long narrations are directed in chunks of nine beats, each call limited to 900 s.
  Code then enforces the rules the model may break and notes every correction in `scene["notes"]`: first and last beat on the hero station, nature versus distance,
  actions per beat length, no two actions overlapping on one station, a calm camera (at most the pack's share of moves, no two moves in a row, angle and height fixed inside a station,
  variety across stations), at least the pack's cutaways, arrow cap, and a hold cap filled with highlights. A beat the model skipped gets a defensive default.
- **Reuse on retry**: the plan is cached under `out/world-plans/` on the computer that runs the worker, keyed by the narrated words and timings. A retry that re-narrates
  identically does not call the model again. The cache is a convenience, not a durable record; deleting it only costs a new director call.
- **Script**: `world/script.py` turns the plan and the word timings into the JSON the renderer reads: waypoints (the camera pose per beat), station and subject actions, events and
  independent two-to-five-word caption phrases. No model is involved, and `script.problems` rejects what the renderer would refuse before the long render starts.
- **Render**: `world/render.py` runs `remotion render index.tsx World` with `--props` (`{pack, script}`), then mixes the narration with the same loudness filter and
  `render.check_video` as the other edits. `BRAINROT_WORLD_GL` overrides the Chromium GL backend (default `angle`).

## Scene packs

A pack is a manifest `brainrot/world/packs/<id>.json` plus a renderer `motion/world/packs/<id>.tsx` exporting `make<Id>(script)`, registered in `motion/world/WorldVideo.tsx`.
The manifest lists the hero station, the stations and their notes, the nouns that point at them, each station's actions with duration in frames, optional subject candidates, actions
and per-station defaults, glossary, and the caps. The director only uses what the manifest lists; nothing is generated as code at run time. Current packs:

| Pack | World | Subject |
| --- | --- | --- |
| `zebra` | savanna with a herd, stages for the coat, predators, heat, hair, flies, coats and cows | none |
| `birds` | country road with a power line, stages for voltage, feet, path, circuit, eagle, spacing, pole, fixes and a lineman | small bird or eagle |

A topic outside the packs' worlds cannot use this edit yet. To add a family: write the manifest (`catalog.check` validates it, and `tests/test_world.py` runs the director
defaults on every pack), write the renderer with every animated value a pure function of `useCurrentFrame()`, register it, and run `npm run check --prefix motion` and a still render.

## Setup and limits

- `npm ci --prefix motion` installs Remotion, three.js and the renderer dependencies (pinned in `motion/package.json`; `bootstrap.py` runs it). `world.render.available()` checks
  Node, the Remotion CLI and three.
- Slow by design: the director takes minutes for a chapter and the render takes tens of minutes.
- Needs a signed-in Claude or Chat GPT CLI for research, pack choice and direction. There is no API-provider path and no silent switch.
- Chapters are rendered independently; each is a complete, cut-free scene.
- The packs are tuned on two hand-built films (zebras, birds). Known rough edges: few distinct subject actions in the birds pack, small secondary models, a thin set of
  stations per topic. Treat results as a review-first draft; respect the job's YouTube review/auto/off choice as for any other video.

Background and lessons from the hand-built test films: [low-poly recipe](motion-graphics-recipe-lowpoly.md) and the READMEs under `experiments/*-lowpoly/`.
