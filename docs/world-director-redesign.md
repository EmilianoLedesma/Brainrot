# World director redesign: the director designs the world

Status: first slice implemented 2026-11-11 (items 1 to 6 below, see the handoff for what ran and what did not); quality of model-designed worlds and the Opus comparison are still open.
Read [world mode](world-mode.md) first; it describes what exists today.

## How to continue (start here)

Everything below is ordered; do not skip ahead. Rules from `AGENTS.md` apply (stay on `master`, no new PR, no secrets in diagnostics, no public uploads, update handoff and index, commit and push only when asked).

**1. Baseline (5 minutes).** Pull, then `npm ci --prefix motion`. Run `uv run --locked python -m pytest tests -q`, `npm run check --prefix motion`, `npm run build --prefix web`. Expect 490 tests passing. Confirm in `.env` that
`BRAINROT_CLAUDE_MODEL` is empty (it pins every call and disables the strong/standard split) and that the Claude CLI is signed in. Do not start a second worker if one is running (`doctor --check-media`).

**2. Make a design to work with.** The model-designed world of the sunglasses story was a scratch file (`out/world-smoke/live_world.json`, git-ignored, may not exist on your computer). Recreate it, about 7 minutes, with the
story of job `8650e624-78c1-4ad6-bd91-e83882f073bc` (script in the `stories` table; read it, do not print credentials):

```python
# run from the repo root: uv run --locked python out/design_probe.py   (create the file; out/ is ignored)
import json
from brainrot import db, llm
from brainrot.world import design
j = "8650e624-78c1-4ad6-bd91-e83882f073bc"
r = db.client().table("stories").select("topic,script").eq("job_id", j).execute().data[0]
with llm.using_provider(db.get_job(j)["params"].get("llm_provider") or "claude-code"):
    w = design.design(r["topic"], r["script"])
open("out/world-smoke/live_world.json", "w", encoding="utf-8").write(w.model_dump_json())   # utf-8: the first probe forgot this and broke the next step
```

**3. Direct it live (this was interrupted).** With the world loaded (`spec.World.model_validate_json(...)`), build word timings from the script (about 0.38 s per word plus pauses; 336 words is about 149 s), then
`plan = director.direct(topic, script, words, seconds, world=world)` inside `llm.using_provider(...)`. Expect 3 chunked strong-tier calls of up to 900 s each; the result is cached in `out/world-plans/`. Print `director.summary(plan)` and
every `scene["notes"]` line: each note is a rule the model broke and code corrected. Many notes on the same rule means the skill text (`skills/world-direction/SKILL.md`) needs to say it more plainly. Then `script.build(plan, title, text, words)` and
`script.problems(...)` must be empty.

**4. Look at it.** Render stills of the generic renderer at the first frame of each station beat: write `{"pack": "generic", "script": <script>}` to a JSON file and run, from `motion/`,
`node node_modules/@remotion/cli/remotion-cli.js still index.tsx World ../out/world-smoke/s.png --props=../out/world-smoke/live_props.json --frame=<N> --gl=angle`. Check against the low-poly recipe, one list item per defect you find:
pieces readable at the camera distance, nothing overlapping or hidden, one saturated content colour, no red or yellow except arrows and callouts, rays end where the story says they end, hero shows the whole idea. Fix in this order of preference:
(a) the wording of `skills/world-design/SKILL.md`, (b) limits and rules in `brainrot/world/spec.py` plus a test, (c) the renderer `motion/world/packs/generic.tsx`. Re-run steps 2 to 4 after each change; the cache is keyed by the script and the world, so delete
`out/world-designs/` and `out/world-plans/` when the skill text changes.

**5. A full render, then watch it.** Make a silent narration of the right length (`ffmpeg -f lavfi -i anullsrc=r=24000:cl=mono -t <seconds> -c:a libmp3lame narration.mp3`) and call
`brainrot.world.render.render_video(audio_bytes, words, title, text, plan)`; it returns mp4 bytes (expect tens of minutes; `BRAINROT_WORLD_GL=angle` is the default). Watch the whole video in motion: calm camera, actions on the right words, stages entering and leaving.
Record the result (what looked good, what did not, timings) in the handoff.

**6. Fix narration for Spanish scripts, then run a real job.** `brainrot/tts.py` always uses `en-US-AndrewNeural`; the sunglasses job failed with `NoAudioReceived` on a Spanish sentence with that voice while `es-MX-JorgeNeural` produced it.
Choose the voice from the script language (a small detector in `tts.narrate`, an explicit voice override stays possible), add a test, then create a job from the dashboard with "Continuous 3D world" (and optionally "Research the web first") on a short topic.
Expected stages: `script`, `chaptering`, `design`, `tts`, `direct`, `render`, `upload`, `schedule`. On a retry the design and the plan come from the caches, so nothing is paid twice if the narration is identical.

**7. Decide the model question with data.** Repeat steps 2 and 3 on the same script with `BRAINROT_CLAUDE_MODEL_STRONG=sonnet` set for the process only, then with the default (opus). Compare for each: `scene["notes"]` count, design repair rounds (look for the log line
"world design needs a repair"), stations and actions actually used, wall time, and two stills. Write the table in this document and set the default tiers (`llm._TIER_DEFAULTS`, `.env.example`) accordingly; keep `strong` for design if direction shows no gain.

**8. Then the remaining features, one per commit.** (a) Subject-first direction for designed worlds: let the design name a protagonist piece with its own actions and make `spec.to_pack` return the `subject` block the director already understands (`director.models`, `design`).
(b) Richer presets and effects as real designs ask (animals that move their legs only during an action, a label-free bar or pie preset). (c) Cancel button for running jobs (below). (d) Tests for `POST /ideas`. (e) When the generic path matches the curated packs,
remove `director.choose_pack`, `catalog.menu` and the pack choice text.

**Done means:** a job with the 3D world on finishes from the dashboard on a topic that has no hand-built pack, the video was watched, `pytest`, `tsc`, the web build and the browser checks pass, and the handoff states what was and was not verified.

## The problem

The continuous 3D world edit works end to end offline, but the director only chooses among scenes that a developer built by hand. A pack
(`brainrot/world/packs/<id>.json` plus `motion/world/packs/<id>.tsx`) fixes the stations, props, actors and actions for one topic family. The director picks stations, shots,
and actions inside that vocabulary and nothing else. Consequence: a topic outside the two packs (zebras, birds on power lines) stops at the `direct` stage with
"no scene pack". This was seen on a real job, "La invención de los lentes de sol": the story and research were fine, `director.choose_pack` answered `none`.

The intended behaviour is the opposite: the topic and the generated script should be enough, and the director should decide the scenes and what they contain.
The pack rule ("the director only uses the manifest vocabulary") was a design choice made while integrating the experiments, not a product decision. Do not build more
hand-made packs as the answer; that is the thing to replace.

## Target flow

```text
topic -> (web research) -> script -> DESIGN -> narration (TTS) -> DIRECTION -> render
                                     ^ new                         ^ exists, adapted
```

1. **Design** runs right after the script exists and before narration, so it can overlap the narration and fail fast. Input: topic, script, research facts. Output, a validated
   JSON "world spec": the ideas of the video in order (stations), the setting of each, the pieces each station needs, the protagonist if any, and the actions each piece can perform
   with a duration. Example for sunglasses: snow goggles of ivory, smoky quartz for judges, a tinted lens with a light beam, ultraviolet rays stopped by a lens, a stall and a crowd,
   a plane and a polarising filter, a pie of "protection versus looks".
2. **Direction** runs after narration, as today (`brainrot/world/director.py`): beats from the word timings, scene nature, calm camera, actions locked to cue words, with the code-enforced
   rules. It reads the world spec instead of a pack manifest. The manifest and the spec should share one schema so existing rules (`design`, `_camera`, `beats`) keep working.
3. **Render** reads the spec and the script and draws everything with a generic renderer.

## Decisions to take or confirm

- **Pieces are data, not code.** The model describes each piece as a spec (base shapes, sizes, colours, parts, anchor points, which actions it supports). A generic renderer in
  `motion/world/` draws it. Never execute model-written code in the render: it cannot be validated before a render that takes tens of minutes, and it would run on the user's computer.
- **A base library** of low-poly building blocks the specs compose: rounded boxes, ellipsoids, cylinders, cones, discs, rays and beams, bars, pies, arrows, people, simple animals, ground
  stages (plinths), weather and light. The current zebra and birds renderers become reference pieces of that library; the two manifests become example world specs.
- **Generic actions**: appear, move along a path, scale, change colour, light up, split or grow (bars, pies), a ray reaching or being blocked, a character putting something on. Each has
  a duration so the existing no-overlap rule keeps working.
- **Validation in code before TTS and before render**: every piece uses library parts only, sizes stay inside the stage (about 8 units from its centre), at most N pieces per stage for
  frame rate, every action names an existing piece, durations fit the beats. A spec that fails is repaired once by the model with the validator message, then the job stops with a friendly error.
- **Quality bar**: the hand-built films look better than anything composed from a generic library will at first. Test with the already generated sunglasses script
  (`stories` row of job `8650e624…`) and with one factual and one fictional topic before enabling the option by default. Keep the packs as an optional "curated" path until the generic one
  matches them.
- **Stays as is**: opt-in per job (`params.world`), no silent fallback to another edit or provider, YouTube review/auto/off, friendly errors, 90–180 s target, natural narration. The script is
  not rewritten to suit the visuals.

## Work items

Done (offline, with a hand-written fixture; see the handoff for any live check):

1. World spec schema, validator and mapping to the director's manifest: `brainrot/world/spec.py` (presets, primitive parts, effects, framing rule, recipe rules: soft palette, reserved red and yellow).
2. Design stage: `brainrot/skills/world-design/SKILL.md`, `brainrot/world/design.py` (strong tier, one repair round, friendly failure, cache in `out/world-designs/`).
3. Pipeline order: stage `design` runs before `tts`; `direct` receives the designed world; stage names added to the dashboard (EN/ES).
4. Generic renderer `motion/world/packs/generic.tsx` (pieces from specs, effects, rays, stage lifetimes, shared calm camera) registered as pack `generic`.
5. `director.plan` and `director.direct` accept a designed world; the script carries it (`script["world"]`).
6. Tests in `tests/test_world.py` with `tests/world_fixture.py` (validation accept and reject, director on a spec, design repair and cache, stage order).

Live result so far: the design stage on the sunglasses script returned a valid world in 405 s (hero plus seven stages, rules satisfied). The live director and any render of that world were not run.

Still to do:

- Run the director live on the designed sunglasses world (script and timings: `out/direct_live.py` was a scratch probe; rebuild it) and render it fully; then the same for one factual and one fictional topic. Run the design and direction stages live on more than one topic (factual and fictional) and look at full renders, not stills; tune the skill and the presets from what the model actually produces.
- More presets and effects as real designs ask for them (animals with legs that move only during an action, a subject with its own actions as in the birds film, text-free labels, bars and pies).
- Subject-first direction for designed worlds (the curated birds pack had it; `spec.to_pack` sets `subject: null`).
- The Opus comparison below, with the same script through both models.
- Remove or demote the curated packs once the generic path matches them; delete `director.choose_pack` then.

## Model tiers: strong for the director, standard for the rest

Decision (user, 2026-11-11): the director uses the most capable model; everything else (script, ideas, web research, YouTube metadata, repurpose selection) uses a cheaper one such as Sonnet.
Verified in code: `llm.generate(..., tier=...)` passes `--model` to the Claude CLI; `strong` resolves to `opus` and `standard` to `sonnet` (`llm._TIER_DEFAULTS`). The world director asks for `strong`
(pack choice and beat direction); a call that names no tier is now `standard` (it used to fall through to the CLI's own default model, which could be Opus on some plans). Overrides, in order:
`BRAINROT_<CLAUDE|CODEX>_MODEL_STRONG` or `_STANDARD`, then `BRAINROT_<CLAUDE|CODEX>_MODEL`, which pins every call and therefore disables the split, then the built-in default. Codex has no
built-in default, so set its tier variables in `.env` to get the same split. Covered by `tests/test_llm.py`. The future design stage should also ask for `strong`.

Still worth measuring before treating Opus as settled: run the same sunglasses script through design and direction with both models and compare validator corrections per beat (`scene["notes"]`),
design repairs, beats with the intended station and actions, time and tokens per call (the unchunked director took about 12 minutes on the experiments) and three stills. If the code-corrected
direction stage shows no gain, keep `strong` only for design.

## Pending feature: cover (portada) for every generated video

Requested 2026-11-11. Decision: option "frame with title": one still frame of the video with the title on it, generated automatically after the render and attached when the video is published. The title already exists
(`stories.title`, and the YouTube title from `brainrot/youtube_metadata.py`); no new model call is needed. No AI image generation, no paid API.

Precise steps:

1. **Cover composition.** Add a Remotion composition `Cover` next to `World` in `motion/index.tsx` (1080x1920, one frame). Props: `{title, frame source}`. Style: the captions look of the recipe (white bold sans, heavy navy stroke, no pill), the title in at most three lines,
   auto-sized, inside the safe area (about 60 px side margins, away from the top 250 and bottom 400 px where feeds put their UI). Render with `remotion still` (the 3D smoke renders in this redesign use the same call).
2. **Which frame.** 3D world edit: the renderer stills of the hero at its wide shot after the opening action has started (the first `sun_glare`-like action; take the frame at the action's midpoint from `script["actions"]`). Other edits: extract one frame with `ffmpeg -ss <t> -i video.mp4 -frames:v 1` at about 30% of the duration
   (check that it is not black with a mean-brightness test, else try 50%), then composite the title over it as a Remotion `Img` background. Start with the 3D path and the ffmpeg path together; keep the frame choice in one function `cover.pick_frame(plan_or_video)`.
3. **New module `brainrot/cover.py`:** `make(video_bytes, title, plan=None) -> bytes` (PNG, at most 2 MB; convert to JPEG quality 90 if over). Offline test with a tiny video made by ffmpeg `testsrc` and a stubbed Remotion call.
4. **Storage (additive migration, do not edit existing ones).** Add `cover_path text` to `story_chapters` (migration `015_chapter_cover.sql`). Upload with `db.upload_job_media(job_id, "story_chapters", chapter_id, f"stories/{story_id}/{index:02d}.png", data, "image/png")`
   so the deletion fence applies. Update the media-cleanup and delete functions of migrations 006 and 008 in the new migration (they enumerate `audio_path` and `video_path`; add `cover_path` to the same unions with `create or replace function`) and extend the SQL tests that cover deletion.
5. **Pipeline.** In `brainrot/pipeline.py` add a stage `cover` after `render` and before `upload`, scope `chapter:N`; set `cover_path` in the same update that sets `video_path` and `status="ready"`. A retry reuses an existing cover for a ready chapter (the existing skip of ready chapters already does it). Add the stage name to `web/src/i18n.jsx` (EN/ES) and a failure must not fail the job when only the cover failed: log it and continue without a cover (a cover is optional, the video is not).
6. **API and dashboard.** Return `cover_url` with the output gallery items and show the image in Output and in the video details view; a "Regenerate cover" button is optional, later.
7. **Publication.** `brainrot/publish.py` `post_youtube` (and the manual upload path `brainrot/youtube.py` `upload_claimed`): after the video upload succeeds, call YouTube Data API `thumbnails.set` with the cover when the chapter has one. Before building this, check the current YouTube rules for custom thumbnails on Shorts and the
   channel requirements (a verified channel may be needed; image size and format limits) and write what you find in `docs/integrations.md`. A thumbnail failure must not mark a published video as failed: record it in the publication's metadata and keep the video published. Instagram and TikTok are not connected yet; when they are, use the same
   `cover_path` (Instagram accepts a cover image or a frame offset; TikTok a frame offset, check both APIs then).
8. **Tests and docs.** Unit tests for `cover.make`, the pipeline stage order and the optional-failure behaviour, an SQL test for the migration and cleanup, a browser check that the cover appears in Output. Update `docs/architecture.md`, `docs/integrations.md`, the handoff and this list.

Done means: a finished job shows a titled cover in Output, a deleted job removes its cover from storage, and a published YouTube video carries it (or the publication records why it did not), with the real YouTube behaviour checked by hand once on a private upload.

## Related pending items found in the same session

- **Cancel button for active jobs.** Requested 2026-11-11. Today only pending jobs can be cancelled (`domain/jobs.py` allows `PENDING -> CANCELLED`; migrations 006 and 008 mark jobs cancelled
  when deleting). A running job needs: an API route, a SQL function that marks the lease owner's job cancelled without breaking lease ownership, idempotency and deletion guards (additive migration
  only), a cooperative check in the worker between stages, killing of long subprocesses (Remotion, the model CLI), and a Cancel button in the queue with a confirmation. Not started.
- **Narration voice follows the script language.** `tts.VOICE` is always `en-US-AndrewNeural`, even for Spanish scripts. On the sunglasses job one short sentence returned `NoAudioReceived`
  with that voice while `es-MX-JorgeNeural` synthesised it. The job kept failing in `tts`. Left untouched on request; a language-aware voice choice is the likely fix.
- **Video ideas has no tests.** Add an API test for `POST /ideas` (dedupe, avoid list, 502 on failure) and a browser check for Tools → Video ideas → Use this topic.
- **A Vite dev server started for browser checks** may still be running on port 5173.
