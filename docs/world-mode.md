# Continuous 3D world edit

An experimental H2 option for generated stories. Instead of a background clip or keyword cards, the chapter becomes one 3D scene without cuts: a researched script,
a director that decides what the viewer sees at every beat, and a Remotion + three.js renderer that follows the narration word by word. It is chosen per job
(`params.world`, UI label "Continuous 3D world"), is mutually exclusive with `params.motion_graphics`, and applies to generated stories only. Web research is a separate
per-job option (`params.web_research`) that also works with the other edits.

## Flow

```text
write story (optionally after web research)      brainrot/investigate.py, pipeline.run_brainrot
design (stage "design", before narration)        brainrot/world/design.py, spec.py, skills/world-design
narrate                                          tts.narrate (unchanged)
direct (stage "direct")                          brainrot/world/director.py
render (stage "render")                          brainrot/world/render.py -> motion/world/ (generic.tsx)
upload, schedule                                 unchanged
```

- **Research** (`web_research`): `investigate.run` asks the selected local CLI (Claude or Chat GPT) to search and read pages with its own web tools, nothing else enabled
  (`llm.generate(..., web=True)`; the API provider is refused, never substituted). The answer is validated in code: http(s) sources only, every fact must cite a listed source,
  at least six facts, otherwise a friendly `PermanentError`. The writer receives the facts with their caveats as `reference_context`. It runs inside the `script` stage, so a retry
  reuses the saved story and never researches twice. Guidance: `skills/research/SKILL.md`.
- **Design** (`brainrot/world/design.py`): right after the script exists and before narration, the strong-tier model reads the topic and script and designs the world as data
  (`brainrot/world/spec.py`): a hero station that shows the world as a whole plus one stage per idea (4 to 9 in all), the pieces on each (presets such as person, tree, house, animal, bird,
  or compositions of box, ball, cylinder, cone and disc parts) and the actions each station can perform, written as effects (appear, disappear, move, scale, colour, glow, spin, ray, wear) with
  durations. `spec.check` validates everything in code (bounds, piece and part limits, effect targets, a framing rule so what matters is big enough at the camera distance, at most three grounds,
  no red or yellow rays because the recipe reserves them for arrows and callouts). A design with problems goes back once with the list; a second failure stops the job with a friendly error.
  Designs are cached under `out/world-designs/`. Because it runs before TTS, a topic that cannot be represented fails in minutes, not after narration. Model-written code is never executed.
  The earlier path (`director.choose_pack`, curated packs) still exists for programmatic use but the pipeline no longer uses it.
- **Direction** (`skills/world-direction/SKILL.md` plus the manifest derived from the designed world by `spec.to_pack`): the model chooses, per beat of the narration, the station in focus, the scene nature
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

## Designed worlds and curated packs

The generic renderer `motion/world/packs/generic.tsx` draws any valid world spec: the shared engine (calm camera, stage lifetimes, captions, soft low-poly look from the
[recipe](motion-graphics-recipe-lowpoly.md)) plus pieces and effects resolved as pure functions of the frame. The two hand-built packs (`zebra`, `birds`: manifest in
`brainrot/world/packs/<id>.json`, renderer `motion/world/packs/<id>.tsx`) remain as curated references and are reachable with `director.plan(..., pack_id)`; they are what the first
generic worlds are measured against. They also show what a designed world should aim for. To change what the model can draw, extend the presets or effects in `spec.py`, the skill and
`generic.tsx` together.

## Setup and limits

- `npm ci --prefix motion` installs Remotion, three.js and the renderer dependencies (pinned in `motion/package.json`; `bootstrap.py` runs it). `world.render.available()` checks
  Node, the Remotion CLI and three.
- Slow by design: the director takes minutes for a chapter and the render takes tens of minutes.
- Needs a signed-in Claude or Chat GPT CLI for research, design and direction (design and direction use the strong model tier). There is no API-provider path and no silent switch.
- Chapters are rendered independently; each is a complete, cut-free scene.
- The generic renderer has only been checked on a hand-written fixture and on stills; the quality of a model-designed world is unmeasured (see the pending doc). There is no
  protagonist subject with its own actions in designed worlds yet. Treat results as a review-first draft; respect the job's YouTube review/auto/off choice as for any other video.

Background and lessons from the hand-built test films: [low-poly recipe](motion-graphics-recipe-lowpoly.md) and the READMEs under `experiments/*-lowpoly/`.
