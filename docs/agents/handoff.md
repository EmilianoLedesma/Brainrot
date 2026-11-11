# Handoff — 2026-11-11

## World director redesign, first slice — 2026-11-11

The director no longer needs hand-built packs. After the script exists and before narration, a new `design` stage asks the strong-tier model to design the world as data; the director and a generic renderer work from it.
Plan and open items: [world-director-redesign](../world-director-redesign.md); behaviour: [world mode](../world-mode.md).

- Done: `brainrot/world/spec.py` (World spec: stations, presets and primitive parts, effects; `check` incl. a framing rule, at most three grounds, no red or yellow rays per the low-poly recipe; `to_pack` gives the director its manifest),
  `brainrot/world/design.py` + `skills/world-design/SKILL.md` (one repair round, friendly failure, cache `out/world-designs/`), pipeline order `design` → `tts` → `direct` → `render` (stage names in the dashboard EN/ES),
  `motion/world/packs/generic.tsx` (draws any spec on the shared calm-camera engine; registered as pack `generic`), `director.plan/direct` accept a world and the script carries it. Curated zebra and birds packs remain, unused by the pipeline.
- Validation run: `pytest tests` 490 passed (new tests in `tests/test_world.py` with `tests/world_fixture.py`), `npm run check --prefix motion`, `npm run build --prefix web`, stills of the generic renderer from a hand-written fixture
  (hero, a stage with a ray; looked right apart from small pieces, which led to the framing rule).
- Live check that ran: the design stage on the saved sunglasses script (job 8650e624…, Claude Opus tier) returned a valid world in 405 s: hero boardwalk plus seven stages (inuit, china, ayscough, uv_block, foster_stand, aviator_sky, life_stats),
  all validator rules satisfied; the pieces and actions looked coherent when listed (giant glasses, walrus, quartz, tinted lenses, UV block, sales stand, plane with polarising filter, pie of need versus style). Not seen rendered.
- NOT run: the live director on that world (started, then stopped on request, nothing recorded), any full render of a model-designed world, a complete pipeline job (the job's narration still fails, see below), the Opus-versus-Sonnet comparison,
  the browser checks after the stage-name change. Nobody has watched a video from this path. Quality of model-designed worlds is unknown beyond the listing above.
- Known gaps: designed worlds have no protagonist subject with its own actions; presets are minimal (animals do not animate legs); the piece scale and framing rule were tuned on one fixture; `out/world-smoke/live_world.json` was saved in the
  Windows default encoding by a probe script (scratch only, ignored by git).
- Unrelated open items, unchanged: the sunglasses job still fails in `tts` (`NoAudioReceived`, English voice on a Spanish script; a Spanish voice works), the cancel button for running jobs, tests for `/ideas`. All in the pending doc.

## Committed state, model tiers and video ideas — 2026-11-11

- Everything from today is committed on `master` (not pushed): the continuous 3D world edit and web research, the Accounts hub, the world-director redesign plan, model tiers and the video-ideas tool.
- **Model tiers**: the world director asks for `strong` (Claude: opus), every other call is `standard` (sonnet), including calls that name no tier (research, metadata, repurpose, motion design were
  falling back to the CLI default before). Codex has no default: set `BRAINROT_CODEX_MODEL_STRONG` / `_STANDARD`. `BRAINROT_CLAUDE_MODEL` pins every call and disables the split. `tests/test_llm.py` covers it.
  Whether Opus beats Sonnet for the director is unmeasured (plan in the pending doc).
- **Video ideas** (user's work, committed as found): `POST /ideas` (`brainrot/ideas.py`, standard tier, five "how X works" / "what if" topics, avoid list, language, provider) and a Tools → "Video ideas" screen
  (`web/src/pages/Ideas.jsx`, copy in `integrations-copy.js`) whose chosen topic opens New job with the topic filled in. It has no automated tests and no browser check yet, and I did not run it.
- Validation run before the commit: `pytest tests` 486 passed, `npm run build --prefix web`, `npm run check --prefix motion`. Not run: Playwright checks after the ideas change, any live job.
- Open work lives in [world-director-redesign](../world-director-redesign.md): design-then-direct redesign, Opus measurement, cancel button for running jobs, TTS voice by script language, fail-fast on a missing pack.

## Pending: world director redesign — 2026-11-11

- A real 3D-world job ("La invención de los lentes de sol", web research on) produced a good Spanish script, then failed in `tts` (`edge_tts.NoAudioReceived`, always English voice) and would have stopped at `direct`
  anyway: the live pack choice returned `none` because only the zebra and birds packs exist. The sunglasses pack was started and discarded (manifest deleted, renderer never written) because the user pointed out
  that the director, not hand-made packs, should decide scenes and content.
- Full plan, decisions, work items, the Opus evaluation and the other open items (cancel button for running jobs, voice by script language, fail fast on missing pack): [world-director-redesign](../world-director-redesign.md).
- Model tiers (user's work, verified and tightened 2026-11-11): the director asks for `strong` (Claude: opus), every other call is `standard` (sonnet), including calls that name no tier. Codex needs `BRAINROT_CODEX_MODEL_STRONG/_STANDARD` in `.env`. `tests/test_llm.py` covers it; whether Opus beats Sonnet for the director is still unmeasured.
- Not committed. Nothing else changed in this step.

## Accounts hub — 2026-11-11

- The Workspace (`#/console`) no longer has a YouTube button or screen. A new top-level view, Accounts (`#/accounts`, nav "Accounts"/"Cuentas", `web/src/pages/Accounts.jsx`), centralises
  connected accounts and per-platform performance. `pages/YouTube.jsx` is now the YouTube part of that hub: a compact connection card (status badge, connect/disconnect, collapsed
  Google setup; refresh only appears after starting Connect), a "Performance by platform" table with an All/YouTube/Instagram/TikTok filter, then the existing automation settings,
  upload steps, upload activity and channel retention. Retention now opens in the hub (Insights below the page) instead of switching the Workspace to Output.
- Instagram and TikTok are disabled "Coming soon" cards and empty filter states only; no backend, no routes, no credentials. Their connection, publishing and metrics are not built.
- The New job form's YouTube section links to Accounts when the channel is not connected. New copy lives in `integrations-copy.js` (EN/ES).
- Validation run: `npm run build --prefix web`, and the Playwright checks `check_integrations.py` (updated for the hub), `check_workspace.py` and `check_video_details.py`, all passing against a
  local Vite server with simulated API responses; the hub was also read in the browser against the live API (Spanish text, connected channel, four performance rows). Not run: Python tests
  (no backend change), a real Google connect, a real upload.
- Not committed. A Vite dev server I started on port 5173 for the checks may still be running.

## Continuous 3D world edit integrated into the main flow — 2026-11-11

The researcher, the director and the continuous-world recipe from the hand-built films are now runtime features (details: [world mode](../world-mode.md)). The sections below
describe the experiments and say "not wired"; that was true when they were written and is superseded here.

- Done: `llm.generate(..., web=True, timeout=...)` (research-only browsing through the local CLIs; the API provider is refused); `brainrot/investigate.py` plus `skills/research`
  (validated facts with caveats feed the writer); `brainrot/world/` (pack manifests for zebra and birds, `catalog`, `beats`, `director` with chunked calls and code-enforced rules,
  `script`, `render`, plan cache under `out/world-plans/`); `skills/world-direction`; `motion/world/` (shared kit, `WorldVideo`, both packs refactored into `make<Pack>(script)`
  factories so the script arrives as a prop, `World` composition, three.js dependencies pinned in `motion/package.json` and the lock).
- Wired: job params `world` and `web_research` (API validation: world excludes motion_graphics and is brainrot-only; `_safe_row`), pipeline stages `direct` and `render`
  (world skips the background clip, reuses the saved story), research inside the `script` stage, dashboard checkboxes and EN/ES copy, the browser-check payload.
- Validation actually run: `pytest tests` 484 passed (SQL tests included, none skipped in this run), `scripts.checks.pipeline`, `npm run check --prefix motion`, `npm run build --prefix web`,
  and one still render per pack from runtime props with synthetic narration and a defaults-only plan (the birds still was inspected: bird, wires, caption render correctly).
- NOT run: any live model call (research, pack choice or director), a full video render through the pipeline, the Playwright browser check, any live job or upload. The director prompt
  and the typed answers were exercised only through guidance building and model construction, so the first real run may need prompt or chunking adjustments (the experiments needed about
  12 minutes of director time unchunked). Nobody has watched a runtime-rendered video.
- Limits and next work: only two packs (zebra, birds), so most topics get a friendly "no scene pack" stop; the plan cache is per computer; chapters render independently; birds pack
  still has few distinct subject actions and thin danger stations; no per-stage progress inside the long render; the GL flag may need `BRAINROT_WORLD_GL=swangle` on headless Linux.
  A new topic family needs a manifest plus a renderer (see world-mode).
- Not committed.

## Birds on power lines: subject-first director v4 — 2026-11-11

Nothing here is wired into the main Brainrot flow; it lives in `experiments/birds-lowpoly/` and the recipe section "Alternative grammar".

- User asked for another topic to test format consistency ("why can birds perch on power lines without being electrocuted") and, mid-task, that the director must identify the
  main subject of the video and give it more detail (animations, movement, etc.) so it is the protagonist.
- Research: 3 WebSearch queries plus Science Focus, ScienceABC (model-extracted) and the US Fish & Wildlife Service page read through the fetch agent. APLIC, the forum threads and vendor
  pages came only from search summaries and are marked so in `reference.json`; 12 paraphrased facts.
- Built `director.py` v4: the model must return `subject` (bird or eagle) and `why`; the subject has its own vocabulary of actions locked to words (code requires one per beat of 3 s or
  more and two from 5.5 s) plus the calm-camera rules of the zebra film; `Birds.tsx`: a detailed bird and eagle from one builder, poses driven by the subject actions, ten stages (countryside
  hero plus nine stages with poles and wires), potential colours violet and teal, flights 45 frames; `build_script.py` carries `subject` and `subjectActions`.
- Result: subject bird, 29 beats, 39 subject actions in 28 of 29 beats, 23 station actions (19 distinct), 26 holds, 0 arrows. Render 134.8 s, 1080×1920, 30 fps, 64.5 MB, no audio, 0 black
  frames, 0 identical consecutive frames of 4045.
- Validation actually run: `tsc --noEmit`, 11 test stills before the render (fixed a grey breast and an oversized hero bird), one full render (timestamp checked), `verify.py`, 37 dense stills
  and four 6 fps runs inspected by hand. Not run: the repository tests, any live Brainrot job; nobody has watched the video in motion. The first director call timed out at the default 180 s;
  it succeeded with `BRAINROT_LLM_TIMEOUT_SECONDS=900` set for the process only (no `.env` change), in about 12 minutes.
- Remaining defects (README): only five distinct subject actions (`look_around` dominates, `hop` and `take_off` unused), the danger stations are less dramatic than the narration, small
  lineman and covers, a one-word caption.
- Integration into H2 is still not started. This film shows the director rules (nature, calm camera, subject, actions with durations) are topic-independent in code, while stages, animals and
  actions are still hand-written per topic, and the director call is slow (about 12 minutes) so a production flow would need chunked calls.
- Not committed.

## Zebra stripes: calm camera, organic models, researched facts — 2026-11-11

Nothing here is wired into the main Brainrot flow; it lives in `experiments/zebra-lowpoly/` and the recipe section "Alternative grammar".

- User asked for a new topic (not the CPU again): "why do zebras have stripes", with a calmer camera than the pothole film, less tight framing, no elements that
  obstruct or overlap each other, no needless element motion, and organic low-poly shapes rather than only blocks.
- Research: 4 WebSearch queries plus Caro 2019, Kojima 2019 and Wikipedia read through the fetch agent. Caro 2014 (Nature Communications) was behind a login
  redirect: its claims rest on search summaries and are marked so in `reference.json`. 17 paraphrased facts with source ids; the script is grounded on them.
- Built `director.py` (v3: calm camera cap, fixed angle and height per station, no action overlaps, rare arrows), `Zebra.tsx` (savanna, organic animals with
  per-vertex stripes, an animated fly, eight stages that enter and leave with their beats, distances 112/88/62), `build_script.py` (45-frame flights) and `verify.py`.
- Result: 35 beats (nature 7/17/11), 30 actions (20 distinct), 32 holds, 2 push-ins, 1 pull-out, 0 arrows. Render 147.4 s, 1080×1920, 30 fps, 65.0 MB, no audio,
  0 black frames, 0 identical consecutive frames of 4422.
- Validation actually run: `tsc --noEmit`, 22 test stills before the renders (fixed zig-zag stripes, cropped stages, tiny hero, stage pile-up), three full renders
  (timestamps checked), `verify.py`, 37 dense stills and four 6 fps runs inspected by hand. Not run: the repository tests, any live Brainrot job; nobody has watched
  the video in motion. The CPU video was not touched, as asked.
- Remaining defects (README): flights between far stages cross empty grass, the director used only `mid` height and mostly the right angle, the hair patch and the cow
  read weakly, many beats are under 4 s.
- Integration into H2 is still not started; this film adds evidence that the director rules can be made topic-independent, but the stages, animals and actions are
  still hand-written per topic.
- Not committed.

## Potholes polish: director v2, softer look, cutaways — 2026-11-11

Nothing here is wired into the main Brainrot flow; it lives in `experiments/pothole-lowpoly/` and the recipe section "Alternative grammar".

- User feedback on the first render: keep low-poly but softer, too little variation (asked whether the director even ran: it did, but it only chose focus
  and distance), arrows add nothing so they must not always appear, wanted a harder and more specific director demanding more elements and more camera and
  element motion tied to the script (no decorative spinning), and then asked the director to decide the NATURE of each scene (detail explanations as close
  cutaways that open objects to explain parts and how they work).
- Built `director.py` (v2): per beat a nature (context/exhibit/cutaway), a shot (distance, azimuth, height, move) and events (`action` locked to cue words,
  `highlight`, `term_callout`, rare `arrow`), with code rules (cutaway count, actions per beat length, camera variety, drift cap, arrow cap, hold cap, first
  and last beat). `build_script.py` now writes `waypoints` with shot and nature, plus `actions`. `Pothole.tsx` rewritten: rounded boxes, soft light, camera
  poses and moves, action-driven exhibits (nothing loops), cutaway interiors. First director's plan and script kept as `*-v1-director1.json`.
- Result: 37 beats, nature 5/17/15, 31 actions (23 distinct), all 9 camera moves, 0 arrows. Render 136.2 s, 1080×1920, 30 fps, 90.8 MB, no audio, 0 black
  frames, 0 identical consecutive frames of 4086.
- Validation actually run: `tsc --noEmit`, 12 test stills (fixed a washed-out image, floating cracks in cutaways, z-fighting), one full render (timestamp
  checked), `verify.py`, 37 dense stills and four 6 fps runs inspected by hand. Not run: the repository tests, any live Brainrot job; nobody has watched the video
  in motion. The CPU video was not re-rendered with the softer look or director v2.
- Remaining defects (README): the patched street shows only for the last ~2 s, tight cutaways crop the exhibit, some actions are subtle.
- Integration: still not started; see the notes in the section below. Director v2's rules would live in code that validates a model-produced film spec.
- Not committed.

## Potholes, researched facts in the continuous world — 2026-11-11

Nothing here is wired into the main Brainrot flow; it lives in `experiments/pothole-lowpoly/`.

- The user asked whether the script is researched; it is not in the normal flow (model knowledge only; `research.py` is an optional Wikidata reference
  picked in the dashboard). They asked for real research on a new topic, "how potholes form", with a director and the continuous style, one scene
  with a car, roads, houses and surroundings, and said that if the result is convincing and visually consistent they want this flow integrated into H2.
- Built: research (3 WebSearch queries, two pages read in full, 17 paraphrased facts with source ids in `reference.json`), script from those facts
  (332 words), timing (135.71 s), a topic wrapper over the CPU planner (`HERO` constant added there), `build_script.py`, `Pothole.tsx` (a town, a
  swerving car, 8 cutaway exhibits) and `verify.py`. Render: 136.2 s, 1080×1920, 30 fps, 64.8 MB, no audio, 0 black frames, 0 identical consecutive
  frames of 4086.
- Validation actually run: `tsc --noEmit`, 13 test stills before the render (two defects fixed), one full render (timestamp checked), `verify.py`, 37
  dense stills, four 6 fps runs and three late frames inspected by hand. Not run: the repository tests, any live Brainrot job, and nobody has watched the
  video in motion.
- Remaining defects (details in the experiment README): the final beat is crowded and the patched street is low contrast, the car is seen mostly in the
  hook, no moment where the car hits the pothole (the writer omitted it).
- Integration, not started: the pieces that are manual today are (1) research, which needs a tool-enabled stage because `llm.py` runs with tools and MCP
  disabled; (2) the world: stations, exhibits and the town were written by hand per topic, so an automated flow needs either a reusable library of
  exhibit primitives that the director composes, or a model-written scene per topic; (3) per-topic planner vocabulary, which would become a model-produced
  spec validated in code; (4) retries and the job lease around a 6-8 minute Remotion render, which `brainrot/motion.py` already handles for the card mode.
- Not committed.

## CPU low-poly, one continuous world — 2026-11-11

Nothing here is wired into the main Brainrot flow; it lives in `experiments/cpu-lowpoly/` and `docs/motion-graphics-recipe-lowpoly.md`.

- User asked for a processor explainer in the style of a microwave reference (`@stupydoo`), with a director planning the scenes instead of
  letting them generate themselves, and asked whether to combine low-poly 3D with HyperFrames. Recommendation given, not tested: keep one
  engine (Remotion + `@remotion/three`); HyperFrames only has an 8 s test in the repo and no check that it renders a 3D canvas.
- ffmpeg scene detection on the reference (164 s): no hard cut. The user chose to redesign the plan as one continuous world instead of 13
  hard-cut shots. New section "Alternative grammar: one continuous world" in the low-poly recipe; the cut grammar remains documented.
- Built: script (`write_story`, claude-code, default model, level 30, 367 words), timing (161.08 s), planner with beats instead of shots and
  `split_long()`, `build_script.py` (waypoint camera), `Cpu.tsx` (one scene, 12 stations, 37 waypoints) and `verify.py`.
  Render: 161.57 s, 1080×1920, 30 fps, 74.4 MB, no audio, 0 black frames, 0 identical consecutive frames of 4847.
- Second pass after the user chose "corregir": planner `--revalidate` (no model call) and `snap_boundaries()`, callouts no longer collide
  with on-part effects (TRANSISTOR now lands on its part, REGISTRO restored), lower camera pitch and closer `wide`, desk props, a branch-
  prediction fork in the pipeline, an orange heat state. The first render's plan and script are kept as `*-v4-first-render.json`.
- Validation actually run: `tsc --noEmit`, two full renders (output timestamp checked before reading sheets), `verify.py` on each, test
  stills before each render, and contact sheets inspected by hand (37 dense stills, four 6 fps runs around flights). Not run: the
  repository tests, any live Brainrot job, and nobody has watched the video in motion.
- Remaining defects (details in the experiment README): some wide/medium frames still show a lot of desk, heatsink `close` fills the frame,
  highlight boxes are large and flat, the wrong-guess cube is small in wide shots, script flags ("miles de millones" versus "millones de
  interruptores"; the closing 1 GHz line; fixing them means regenerating script, timing and plan).
- Not committed. `story.json`, `words.json`, `plan*.json`, `script.json` are untracked data files; renders are in the ignored `out/cpu-lowpoly/`.

## Low-poly 3D experiments, planner and recipe — 2026-11-04

Nothing here is wired into the main Brainrot flow; every piece lives under `experiments/` or `docs/`.

Built (each folder has its own README with commands and numbers):
- `hyperframes-pressure-cooker` (8 s HyperFrames graphics test), `elevator-cables-2d` (10 s Remotion 2D), `moka-cutaway-3d` (first
  `@remotion/three` proof of concept), `sky-blue-lowpoly` and `deadbolt-lowpoly` (10 s silent tests of the low-poly recipe),
  `foil-sides-lowpoly` (93.65 s), `shock-absorber-lowpoly` (146.97 s) and `zipper-lowpoly` (119.3 s).
- The three long ones use real Brainrot code for the script (`brainrot.script.write_story`) and the word timing (`brainrot.tts.narrate`,
  audio discarded; the videos are silent), a planner modelled on `brainrot/motion.py` (`plan()` blocks, then a Pydantic `design()` that picks
  shot types and events), a deterministic phrase-caption grouper (`build_script.py`), `script.json` for the Remotion composition, an
  `audit.py` (shock absorber) and a `verify.py` that measures the MP4 and pulls contact sheets.
- Recipes: `docs/motion-graphics-recipe-lowpoly.md` (consolidated from the renders: sustain strategies, no pop-in, push-in/pull-out,
  `highlight`, hold cap, phrase captions) and `docs/motion-graphics-recipe-schematic-world.md`.

Validation actually run: `tsc --noEmit` in each Remotion project; full renders checked with `verify.py` (duration, 1080x1920/30 fps, no audio
stream, black frames and identical consecutive frames both 0); contact sheets inspected by hand (dense, plus 6 fps runs inside single shots);
planner audits on four v1 and four v2 plans. Not run: the repository tests, any live Brainrot job, any video watched in motion.

Findings worth keeping:
- Model question closed: Opus 5.5 versus the default Claude model made no difference once the planner prompt stated the rules (hold cap,
  noun coverage, `damp` once). The earlier gap was prompt specificity. The default model is used for later runs.
- A model told to acknowledge every noun reaches for red arrows. A neutral `highlight` event plus a code check (a `force_arrows` cue needs a
  force or motion word) fixed it; the planner enforces the 9 s hold cap in code (`fill_gaps()`), and a term may be used once per video.
- Caption grouping must fold a one-word leftover into a neighbour of the SAME sentence (a glued "perfecto El problema viene después" shipped
  once). Load-time `validate()` functions in the compositions reject static cameras outside assembly shots, missing ambient fields,
  accumulating captions and non-part callouts, and caught a planner/renderer parts-list mismatch before encoding.
- Codex exited with code 1 intermittently on structured calls, so the planner runs used the Claude provider at the user's request; `edge-tts`
  dropped streams and the experiment `timing.py` retries each section without touching repo code.

Remaining work and limits:
- Shock absorber: red arrows cropped in cutaways, small hero, three consecutive cutaway shots restart the camera at each cut, plain hub block.
  Zipper: captions sit over the hero, pull tab is the same grey as the slider, highlight boxes are heavy, close-up arrows cropped.
- Rendered videos and contact sheets are in the ignored `out/` folders, not in Git; re-run each README to recreate them.
- `AGENTS.md` lost its Codex-preference lines in a user edit but still has the sentence "Do not silently fall back to another provider or
  paid API." directly after them; check that it reads as intended.
- Integration into `motion/` and a runtime skill is still the six-step path listed in `motion-graphics-recipe.md`; not started.

## Claude Code integration check — 2026-10-27

Verified the user-indicated PowerShell session owns a running native Claude Code
child. Brainrot independently launches CLI requests; it does not attach generation
to an existing interactive session. Resolved Claude Code 2.1.312 through the actual
adapter, using its isolated temporary directory and filtered child environment.
The adapter's subscription authentication check passed. Required visible flags
are present; hidden --max-turns was accepted by a help-only parser check.
All 33 tests in tests/test_llm.py passed without model usage. Current configured
default remains codex; no model override is configured for Claude. No live model
request, provider change, process restart, generation or publication occurred.
This verifies executable/authentication/adapter contracts, not a live structured
model response or remaining subscription quota. No secrets or machine PIDs saved.

## Follow-up readiness validation — 2026-10-27

This inspection supersedes conflicting machine-presence claims below. Installed
uv through the available Python pip, then `uv sync --locked --python 3.14` passed;
the environment reports Python 3.14.10. Standard `uv` is now on PATH. Local startup
prerequisite check passes; FFmpeg, ffprobe, Codex and Claude executables, bundled
caption font and runtime storytelling skill are present. Executable presence does
not establish provider authentication. No model calls were made.

Validation: 368 pytest tests passed, 107 SQL tests skipped because modern Postgres
binaries are not configured (only an old 9.2 installation was found). No complete
SQL validation is claimed. Seven offline pipeline/FFmpeg checks, web production
build and motion TypeScript check passed. Six agent-entry documentation files had
no broken local links. Installed Playwright Chromium because the checked Edge
path was absent. Browser smoke initially exposed a stale expected request payload;
updated it to include the existing false motion_graphics field. Full desktop/mobile
browser smoke then passed with synthetic API responses. Temporary Vite closed;
no production API, worker, generation, publication or live model test was started.
Updated development instructions for Chromium installation when Edge is absent.

Read-only database-backed media audit succeeded. A subsequent legacy Storage
recovery restored eight ignored local files, including all six backgrounds and one
story audio/video pair. Final audit: 14 referenced files, six missing story files.
The user explicitly said to skip unavailable media for now; no records were deleted
and the worker's existing missing-media startup guard remains unchanged. Full
worker startup remains blocked by those missing references. No further recovery
or media regeneration is requested.

Concurrent commits appeared on master during this check, including the browser
expectation fix; preserved them. This agent did not commit or push. Remaining local
prerequisite for full SQL validation is modern PostgreSQL plus PG_BIN configuration.
No credential values were printed or recorded.

## Incoming session orientation — 2026-10-27

Read agent orientation, handoff, architecture, development, product decisions,
documentation index, computer-switching guide and IDE contributor instructions.
Reviewed root environment variable presence with user authorization; no secret
values were printed or recorded. Configuration presence does not establish valid
credentials, provider authentication or service health.

Current branch is `master`. Existing changes to `AGENTS.md` and untracked IDE
instruction directories were preserved. This session changed only this handoff.
No services, workers, model calls, database checks, generation, uploads or tests
were started. No commit or push. Await the next concrete development request;
inspect source and live state for its affected flow before making changes.

### Setup and verification on this computer — 2026-10-27

Installed `uv` (winget); bootstrap, `brainrot.dev --check` and `doctor` ran. Offline
suite: 368 passed, 107 skipped (only PostgreSQL 9.2 installed, so SQL tests skip; no
database validation claimed). Web build, `npm run check --prefix motion` and
`scripts.checks.pipeline` passed. Read-only Supabase probe found `local_media_host`
(014) and `youtube_metadata_drafts` (012) present. Codex CLI not installed here;
Claude CLI present. 14 referenced media files missing until a media import. Corrected
stale docs: retry now exists (operations), `web/.env` only for standalone Vite,
migrations 008–014 (deployment, integrations), motion check and Postgres note
(development). No services started, no commit or push.

Follow-up: Codex CLI was only bundled in the VS Code ChatGPT extension, so it was
installed globally with npm (`@openai/codex`, same ChatGPT login). `sync-media`
recovered the 6 backgrounds still in Supabase Storage (8 of 14 files at that point;
doctor now reports 6 missing, all `stories/*` audio/video of finished jobs that exist
only on the other computer). Added opt-in `BRAINROT_ALLOW_MISSING_MEDIA=1`
(`portable.blocking_missing`, used by `dev.py` and `worker.py`; documented in
`.env.example`; one new test, 369 passed / 107 SQL skipped). Default behavior is
unchanged: without the flag the worker still refuses to start. With it, the full
stack was started on 5173/8001 and the worker took the host reservation; all four
existing jobs are done, so no queued work depends on the missing files. Retrying or
re-rendering those four jobs needs the media import first. Not committed.

## Silent vector motion-graphics recipe and two PoCs — 2026-10-27

User wanted the "first sample" look (Download.mp4, an AI-delegation explainer: kinetic
type, UI cards, hero object that changes shape) as light pastel, After-Effects-style
vector animation, silent, driven by a script, with no frame (no corner brackets,
timecode, label, progress line) and no film filters (grain, vignette, chromatic
aberration). Built without the repo's motion skill.

- Recipe: `docs/motion-graphics-recipe.md` (look, tools, ten steps, sound, render
  commands, gotchas, integration checklist).
- Dark first attempts, kept for reference only: `experiments/remotion-explainer/delegation/`
  and `coffee-sci/Coffee.tsx`; the user rejected their film look.
- Target look: `coffee-sci/CoffeeLight.tsx` + `script-light.json` (coffee science, 16 s) and
  `zebra-stripes/` (`ZebraStripes.tsx`, `script.json`, 18 s; facts from the sources
  already verified for the earlier narrated `zebra/story.json`). Shared primitives are in
  `coffee-sci/kit.tsx`; `coffee-sci/sfx.py` synthesizes the sound bed (numpy, no speech).
- New dependencies in `experiments/remotion-explainer/package.json` (exact 4.0.538):
  `@remotion/paths`, `@remotion/noise`, `@remotion/motion-blur`.
- Validation: `npx tsc --noEmit` clean; contact sheets of 12 stills per video and a frame
  from each final render. Renders (ignored `out/`): `out/coffee-sci/coffee-light.mp4`,
  `out/zebra-stripes/zebra-stripes.mp4`, 1080×1920, 30 fps, with sound effects muxed.
  Nobody has watched full playback or listened to the sound bed.
- Limits: schematic values are labelled illustrative; flies and counts in the zebra
  video are not data; the 18–22 % and 90–96 °C coffee figures were attributed to the
  Specialty Coffee Association from memory and not source-checked. Not integrated into
  `motion/` or `brainrot/motion.py`; the recipe lists the steps. Not committed.

## Claude Opus 5.5 time-perception film — 2026-10-27

User requested a new English film on years feeling faster with age, explicitly
using Claude Opus 5.5 and Lemo Data Storytelling. This task overrides the normal
Codex validation preference only for this film; no project defaults changed.
Subscription login verified; three successful creative calls reported exactly
`claude-opus-5-5` in sanitized CLI model metadata: story, direction, compact chart
source. No paid model API or other provider fallback. The broad full-film code
request exceeded Windows argv size initially, then timed out at 1200 s after
moving references to stdin. No usable source came from that long request. After
the user asked for status, a small low-effort request to the same Opus model
returned the chart/transform layer. Use bounded smaller calls going forward.

Added `experiments/lemo-time-perception/`. Existing Brainrot guidance generated
337 Grounded words; Guy speech measures 127.0275 s. Per-utterance TTS caching
recovered flaky streams without regenerating the saved Opus script. Opus's
sixteen-beat direction and chart artwork use pinned Lemo Data Storytelling:
cream paper, pencil, calendar/recollection illustrations, actual survey/sample
counts. Local code supplies vertical camera/caption/render infrastructure.
Sources are reviewed, hash-recorded and executed locally with unchanged Lemo
engine. Fonts Newsreader/Caveat/IBM Plex Mono are bundled with OFL notices/hashes.

The scientific premise is qualified: retrospective judgments, routine and
landmarks are a plausible account, not a proven sole age mechanism. Dataset
numbers are participants/recruitment design, not memory counts or time-speed
outcomes. No fabricated age curve, brain scan or causal percentage. Qualitative
drawings are marked illustration. No progress bar or persistent upper header.
Local review shortened labels and removed a misleading strike-through of a
negative finding. The final beat starts at the concluding paragraph for reading
time. A Windows default-encoding issue in age-group labels was fixed with UTF-8;
101.7–110.1 s was rerendered and assembled on exact frame boundaries, preserving
the narration. Corrected data/source now reproduce the proper labels directly.

Ignored `out/lemo-time-perception/` includes `final.mp4`, `watch.html`, poster,
SRT, voice/timing, model audit, direction/authorship/source-review records, real
style/final/action sheets and verification. Final: 127.033333 s, 1080×1920,
30 fps, H.264/AAC, 11,101,176 bytes; −16.07 LUFS / −1.48 dBTP. Complete decode,
duration/dimensions/codecs/size, black-interval and model-audit checks passed.
Text reading checks passed; inspected actual final timeline/action sheets,
including the corrected age labels. Engine/font provenance, docs links, syntax
and `git diff --check` passed. No full production suite rerun: runtime code was
unchanged. This is a directed local prototype, not a new dashboard/queue mode;
no sensory watch/listen or audience-retention claim. No job, worker, upload,
service restart, commit or push. Earlier uncommitted experiments were preserved.
Complete normal-speed headless playback of the corrected final file reached its
end with no page/media errors; report is in `playback.json` beside the output.

## Agent-selected procrastination cartoon — 2026-10-27

User requested one English Lemo film on why procrastination can prioritize
immediate emotional relief, with the agent choosing the style. They prohibited
the coffee film's progress bar/fixed upper header and then requested more camera
movement/effects. Preserved Grounded delivery. Live Codex compared midcentury-toon,
one-line and paper-popup, selecting midcentury-toon. Saved choice/reasons are local
outputs, not a guessed style assignment. The existing Brainrot storytelling call
generated 326 original words; Guy narration measures 123.53 s. A subsequent live
Codex call read the selected guide and DIRECTOR.md to produce eighteen beats.

Added `experiments/lemo-procrastination/`: original character/desk/laptop/phone
drawings using the actual pinned Lemo printed-cel engine, eighteen timed beats,
side/overhead/hand-detail views, camera tracks/pushes/pulls, depth-plane parallax,
circle reveals and object/color-plane wipes. Bottom speech captions remain;
there is no progress indicator, persistent heading, step header or completion
quote card. Only a small diegetic DRAFT label appears on the laptop. A sparse
original synthesized score and 49 quiet timed foley events support the voice.
The final action remains unfinished and the illustrative discomfort stays visible.

Style-frame review led to distinct overhead views, connected sleeves/hands,
corrected worried mouth shape and removal of one unreadably short prop label.
Upstream readcheck then passed. Outputs under ignored `out/lemo-procrastination/`:
`final.mp4`, `watch.html`, `poster.jpg`, SRT, saved narration/words, agent choice,
direction/timed data, source/credits and verification/contact-sheet artifacts.
Final is 123.533333 s, 1080×1920, 30 fps, H.264/AAC, 17,347,231 bytes. Complete
decode, duration/codec/dimensions/size and black-interval checks pass; measured
audio −16.05 LUFS / −1.37 dBTP. Inspected final timeline and 0.2-second action/
transition sheets. Selected style hashes/docs links and Python/JS syntax pass.
Full normal-speed headless browser playback of the actual final file reached
its end without page or media errors; this verifies playback, not sensory review.
`git diff --check` passed.

Limits: an authored directed film, with scene code tied to its saved eighteen-beat
plan, not a generic autonomous animation mode or queue integration. This explains
a common psychological account, not a universal brain cause; visuals are original
metaphors, not scans or data. Technical checks/sheets do not establish sensory
watch/listen or viewer retention. Reuses project-owned pinned Lemo core tools and
the coffee experiment's locked browser/audio dependencies; original Lemo code is
unchanged with MIT notice/hash records. User constraints override its step-card
defaults. No Claude, paid model/media API, worker/job, upload, restart, commit or
push. Earlier uncommitted work is preserved. Docs index/notices updated; no full
production suite rerun because production code is unchanged.

## Coffee video A/B comparison — 2026-10-27

The user requested an actual Grounded coffee-science video through the current
Brainrot/Remotion flow, then the same topic through Lemo-Opuscar integrated for
comparison. They explicitly changed the requested language to English. Generated
one original 331-word title/script with `script.write_story`, provider `codex`,
level 0 and researched reference context. Reused one Guy narration and its word
times for both films: measured speech 128.5025 s. No Claude or paid model API.

Implemented a portable, local experiment in `experiments/coffee-comparison/`.
Baseline invokes unchanged `brainrot.motion.render_video`; its real Codex design
call succeeded, producing four devices across eight scenes. The process-local
timeout was 900 s; no `.env` or normal runtime setting changed. This supersedes
the older claim that no live runtime scene-design call had succeeded. It still
does not establish a queue job with the dashboard checkbox.

Lemo uses a pinned MIT subset at `413a6bd6d78ebd3bdd5abaec9538a26867f890df`,
including the actual isometric engine, frame renderer, readcheck, event exporter
and procedural sounds. A separate Codex call reads its directing/style guides;
exact spoken cues become ten timed shots after short/adjacent beats are merged.
Original coffee geometry illustrates roast, pores, surface area, uneven flow and
dilution. Fixed a platform depth-sorting defect found in actual style frames.
Guides/tools are repo-owned with hashes/notices; no global plugin or machine path.

Ignored outputs under `out/coffee-comparison/`: `baseline/final.mp4` (128.6 s,
9,439,867 bytes), `lemo/final.mp4` (128.5 s, 8,966,817 bytes), optional
`lemo/voice-only.mp4`, synchronized `comparison.html`, side-by-side
`comparison.mp4`, saved script/audio/timing/shot props, contact sheets and reports.
Both main films are 1080×1920, 30 fps, H.264/AAC. All three exports pass complete
decode, duration/dimensions/codecs/size and black-interval checks. Main films
measure −16.03 LUFS; peaks −1.50 and −1.43 dBTP respectively. Upstream label
reading-time/bounds checks, 19 vendored hashes, Python/JS syntax and
`git diff --check` passed. Reviewed final timeline sheets and transition strips.
Full-speed headless browser playback of both actual films to their ends passed,
with audio selection and restart exercised and no page/media errors. Fixed an
audio-source switching AbortError exposed by the first browser run, then repeated
the complete playback successfully. This checks playback behavior, not sensory
editorial quality. Separate experiment Python dependencies have a hash-pinned
lock; installation against that lock was checked.

Limits: this is a directed coffee prototype and local shared-audio bridge, not
an arbitrary-topic autonomous editor or new queue/dashboard mode. The model's
direction is adapted to a finite coffee scene vocabulary. Lemo final adds quiet
procedural effects; its voice-only control isolates the picture. Some scenes
hold for long narration passages; transitions remain simpler than the channel
reference. Technical checks/contact sheets do not establish a full sensory
watch/listen, retention gains or reference-channel production quality. No worker,
database job, publication, service restart, commit or push. Existing handoff
review edits were preserved; docs index and third-party notices were updated.
No full offline suite rerun: production code was unchanged. See the experiment
README for reproduction and facts/credits.

## Lemo-Opuscar review — 2026-10-27

Reviewed `lemomo-ai/lemo-opuscar` main: README/licensing, directing and technique
guides, style index, whiteboard/isometric/visual-investigation guides, core tool
reference, frame renderer, reading-time checker and procedural sound helpers.
Source review only: no installation, demo playback, rendering, model calls, jobs,
uploads or new tests. Preserved the earlier MoneyPrinterTurbo handoff edits.

Proposed adaptations, not implemented: a few repo-owned visual style guides for
the current Remotion renderer; a saved shot/timeline plan tied to existing TTS
timings; continuous subject/camera transitions; metadata-driven on-screen label
duration/bounds checks; optional event-timed procedural sounds; and actual
full-speed audiovisual review alongside stills. Upstream readcheck depends on
declared text/bounds and does not verify all visual overlap or comprehension.

Upstream is an agent-driven film-authoring workflow, not a drop-in queue backend.
Its docs target Claude, default to shorter landscape films and recommend WSL on
Windows. Compatibility/quality with Codex and Brainrot's 90–180 s vertical output
remain untested. Keep existing provider choices, portable setup and output rules.
Code/docs are MIT; demo films/stills have separate CC BY 4.0 terms and some voice
tracks are excluded. Preserve notices for reused source and inspect asset credits.
Only the handoff changed; no commit/push. `git diff --check` passed.

## MoneyPrinterTurbo review — 2026-10-27

Reviewed upstream `harry0703/MoneyPrinterTurbo` main via its README, license,
task/material/video services, model schema, LLM search-term generation, music
service and search cache. Compared these with Brainrot's pipeline, library,
FFmpeg renderer, TTS and Remotion adapter. This was a source review, without
installing or running upstream code, model calls, jobs or uploads; no new tests.

Recommended adaptations, not implemented or approved for implementation: an
optional narration-led stock-footage montage using the existing media library;
persisted timed scene/asset choices for retries; image-to-clip motion; caption
presets; optional local music; and atomic validated material downloads plus a
bounded search cache. Upstream chronological search terms and sequential clips
do not establish precise sentence-level semantic alignment or an autonomous
visual editor. Keep Brainrot's provider choices, SQL ownership/publication
controls, duration rules and deliberate media handoff. The upstream MIT license
requires retaining its notice when incorporating substantial source portions.

Repository was clean on `master` at `10cba90` before this review. Only this handoff
was edited; no commit or push was requested. The last completed test run remains
the 475-test run recorded below, not a new validation on October 27.

Read this with the latest user request and `git status`; this is a dated snapshot,
not a live dashboard. Do not assume another checkout has its credentials, media
or migrations just because this development machine does.

## Repository organization and final save — 2026-10-23

The other session finished and committed/pushed the runtime motion work as
`5fac0f6` on `origin/master`. The tree was clean before this follow-up. The user
authorized organizing the repository and committing/pushing all remaining work.
This status supersedes the older waiting/uncommitted notes below.

Grouped explicit operator checks under `scripts/checks/`, invoked from the root
as `python -m scripts.checks.pipeline`, `.database`, and `.live`. Moved pip
entrypoints and hashed exports to `requirements/`, and distribution documentation
to `docs/distribution/`. Folded pytest settings into `pyproject.toml`. Updated
current commands, dashboard help, license notice pointers, archive requirements,
README and documentation index; historical plans/snapshots keep their old paths.
Python package versions/hashes are unchanged. Added `scripts/README.md` for the
new command map. Licenses and tool entrypoints remain at the root.

Validation: dashboard production build, motion TypeScript check, seven offline
pipeline/FFmpeg checks, operator module imports, pip includes, documentation links,
lockfile consistency, and source archive secret/integrity checks passed. All
475 offline tests passed, including disposable local PostgreSQL 18 tests. No live providers,
Supabase checks, generation jobs, or platform uploads were started for this task.
Live model-driven scene design and end-to-end motion limitations below still apply.

## Earlier commit and push status — 2026-10-23

While runtime edits were on hold for commit, the user requested a polished general
README using Markdown and no CSS. Reworked the product overview, feature/input
tables, quick start, integration status, local-media/deployment boundaries,
development commands, documentation navigation and dual-license credit. Preserved
the old detailed lifecycle, stages, metrics, pacing and operator guidance in
`docs/pipeline-reference.md`, linked from README and the documentation index.
Local file links and README navigation anchors passed checks; no CSS was added.
This was documentation-only work, without service restarts or new runtime tests.
The user then authorized pushing independent changes while leaving work that
depends on the other session. Committed and pushed README, pipeline reference,
and documentation index as `6ae9243` to `origin/master`. The README describes the
committed standalone prototypes and leaves unfinished runtime integration out of
setup commands. Documentation link and no-CSS checks passed for all three files.
Shared handoff and runtime changes remain uncommitted for the other session.

Committed and pushed the independent licensing/source-packaging files to
`origin/master` as `011f4d7`. The user explicitly asked to wait for another session
to finish runtime motion edits before committing those files. Runtime changes
and the broader handoff remain uncommitted; inspect both staged
and unstaged differences before resuming. Do not treat this as a clean tree.

Pre-push checks: 474 offline tests passed, including disposable local Postgres18;
frontend production build, motion TypeScript check, offline pipeline self-checks,
source archive secret/integrity checks passed. Another session changed runtime
scene-design code during these checks, so validate the finished runtime changes
again before committing them. No live model calls, generation or uploads were
started by this commit/push task. No PR or new branch was created.

## Prototype and local dashboard — 2026-10-23

### Licensing and GitHub upload package

Follow-up: the user asked to include Apache licensing. The current original-source
grant is **MIT OR Apache-2.0**, at the recipient's choice. `LICENSE` states the
choice; full texts are `LICENSE-MIT` and `LICENSE-APACHE` (the latter retrieved
from Apache's official site), with attribution in `NOTICE`. README, upload guide,
third-party notices and archive requirements reflect this choice. This supersedes
the initial MIT-only setup described below; third-party licenses are unchanged.

The user requested free use with recognition and files ready for GitHub. Added
root MIT `LICENSE`, copyright Emiliano Ledesma and Brainrot contributors (holder
name taken from the configured Git author), plus `THIRD_PARTY_NOTICES.md` and
`GITHUB_UPLOAD.md`. MIT requires copyright/license retention; a visible credit
in every video is not required. Fonts, video-use and Remotion retain their own
terms. Imported media is not relicensed by the project.

`scripts/package_source.py` packages the current source, including uncommitted
changes, into ignored `out/releases/brainrot-github-source.zip`. It excludes local
agent settings, credentials, installed dependencies, private/generated media and
Git metadata; checks configured secret values without printing them; and verifies
ZIP integrity. README/index link the notices and guide. No GitHub repository,
commit or push is created. Preserve other in-progress working-tree changes.

### Motion-graphics option wired into the main flow (latest)

- New Job (Generate) has a "Motion graphics edit" checkbox (EN/ES copy, review row). It sends
  `motion_graphics` to `POST /jobs`; stored in `params` only when true; rejected for repurpose;
  visible in the job view. `pipeline.produce(..., motion_graphics=)` skips background selection and
  calls `brainrot/motion.py` instead of `render.render`. Everything else (script, TTS, upload,
  schedule, YouTube modes, insights, retries) is the shared path.
- `motion/` is the runtime Remotion project (generic `Motion` composition, `Transition`, font,
  lockfile). `scripts/bootstrap.py` runs `npm ci --prefix motion`. Worker needs Node on PATH; if
  `motion/node_modules` is missing the job fails with a friendly "run npm ci --prefix motion".
- Validation: new tests for plan/API/pipeline pass; full run was 418 passed, 56 errors, all SQL
  tests needing local Postgres (same errors without these changes). Web build passes. A real
  `motion.render_video` render of the zebra narration (123 s) passed `check_video` in ~2.5 min,
  8.4 MB.
- Scene devices: `motion.design()` makes one extra call to the job's provider with
  `brainrot/skills/motion-graphics/SKILL.md` (stat, compare, checklist, steps, stamp, alert, none;
  facts only from the narration, ~1 in 3 scenes plain, no repeats back to back). Validation drops
  malformed beats; a failed call logs and renders keyword punches only. `motion/Devices.tsx` draws
  them; checked with stills built from hand-made props (all six devices render), and a unit test
  covers validation with a faked model.
- Restart needed: an API or worker started before this change rejects `motion_graphics` (422 "check
  your input") because request validation is strict. Restart `brainrot.dev` after pulling.

**Pending (not done):**
- The live Codex call for `design()` has NOT succeeded yet: one try hit the 180 s CLI timeout
  (`BRAINROT_LLM_TIMEOUT_SECONDS`), a second was stopped. Confirm the schema is accepted and see how
  long it takes (raise the timeout or shrink the prompt if needed) before relying on it.
- No end-to-end render with model-chosen devices, and no live worker job with the checkbox on.
- Visual polish: devices sit below the keyword punches in a fixed layout; check overlaps with
  captions and long labels on real output. The checkbox is not shown on queue/inspect rows beyond
  the job view field. Render takes minutes per video (concurrency fixed at 2).
- Prototype commit `61fd3de` was pushed earlier; this work is committed in the following commit.

### Zebra-stripes test video (latest)

The user asked for a fresh test video, "why zebras have stripes", edited like the
`QClZnH2NDIM` reference but with focus-grabbing elements used sparingly (bubbles
were only an example). Built as a second composition, `Zebra`, in
`experiments/remotion-explainer/zebra/` (`Zebra.tsx`, `Quad.tsx`, `story.json`),
registered beside `Explainer` in `index.tsx`. `video-use-prototype/prepare.py` gained
a `--story` option (default unchanged). Narration came from Brainrot's existing TTS
(Guy, no paid API): 316 words, 123.4 s. Narration assets are staged in
`experiments/remotion-explainer/public/zebra/`.

The script was written by hand, not by the main flow: it did not run `script.py`, the
`brainrot-storytelling` skill, intensity rules or the Codex provider. Facts were
checked against Caro et al. 2014 (Nature Communications), Caro et al. 2019 (PLOS ONE,
horseflies) and Kojima et al. 2019 (PLOS ONE, painted cows); source links are in
`story.json`. Against the skill: length and factual progression fit, but the hook is
the generic "everyone assumes X" opening the skill discourages.

Output: ignored `out/zebra-stripes/edit/final.mp4` (copy `zebra-v1.mp4`), 1080×1920,
30 fps, 123.4 s, 25.6 MB, decodes cleanly, audio mastered by the video-use helper.
About 85% of sampled frames change. Eight scenes, one device each: stripe draw-in and
idea chips, counters and ✕/✓ rows on a study card, alert and blood-drop, speed gauges
with a bounce shockwave, dotted coat comparison, flick meters, blurred fly's-eye view,
runway lights. Study visuals are schematic and labelled illustrative.

Not done: nobody has played it end to end or listened; review was contact sheets and
stills only. Known weaknesses: the zebra silhouette is crude, the same hero pose repeats
in four scenes, there is no morphing, the fly in the landing scene is too small, and the
landing panels leave the lower screen empty. Not committed.

### Motion and editing pass on the Remotion explainer

The user supplied a target reference, Stupy Doo `QClZnH2NDIM` (Spanish, ~142 s;
language difference is intentional). Reviewed it as downloaded video through 3-second
contact sheets and frame-change measurement (ignored `out/inspiration-review/`). It
changes almost every frame, rarely hard-cuts, keeps one hero object (a phone) through
every scene, and proves each claim with a prop (stamped documents, counters, labelled
experiments, per-keyword text). The polished v2 render changed only ~27% of sampled
frames at 10 fps and held static diagrams for seconds. Gaps named: continuous motion,
hero object continuity, evidence props, morphing instead of cutting.

Implemented in `experiments/remotion-explainer/` only (`index.tsx`, new `Overlay.tsx`):
per-beat camera punch-in, floating props, drifting dot grid, four rotating scene
transitions (side wipe, vertical wipe, iris, staggered bars), narration-timed pop-up
speech bubbles, alert cards and stamps, and a four-word spoken caption with the active
word popping. Pop-up text only restates that scene's narration; cues come from the
cached `words.json`. No new speech, provider, database or upload calls.

Local outputs in ignored `out/remotion-explainer/edit/`: `final-v1.mp4` (first prototype),
`final-v2.mp4` (30-beat polish), `final-v3.mp4` (motion pass, no pop-ups) and
**`final-v4.mp4`** (current; `final.mp4` is a copy of it). v4: 145.2 s, 1080×1920,
30 fps, 34,380,411 bytes, no decode errors, audio −16.0 LUFS / −1.5 dBTP via the
video-use two-pass loudnorm helper. About 90% of sampled frames change at 10 fps.
Vendored video-use helpers match the pinned hashes in `provenance.json`. A re-render
reproduced a complete file; Remotion downloaded its headless browser into its cache
on first use. The dashboard on 5173 and API on 8001 were not touched.

Not done: nobody has played v4 end to end or listened to it; only stills at pop-up cue
times were inspected, before the final overlay position tweak. `verify/critic.md` is
the old v1 critique and does not cover v2–v4. Remaining product gaps versus the
reference are the hero object, evidence props such as counters and stamped documents,
and morphing between diagrams. Production integration is still undecided. Uncommitted:
`brainrot/dev.py`, `.gitignore`, docs and all of `experiments/`. No commit or push.

### Earlier direction: polish the 2D Remotion explainer

The user explicitly chose to improve the Remotion video rather than pursue the
additional 3D-like Monopoly reference. The new source stages thirty word-timed
visual beats across the same ten narration chapters. The opening hand overlap and
global decorative drift were removed. Contact develops into schematic cutaways
and simultaneous metal/wood comparisons, with distributed/local energy spread
and visible skin cooling. The payoff now returns to the mechanism. Narration and
its original factual sources are retained; no production integration or upload.

The earlier Remotion output is preserved locally as
`out/remotion-explainer/edit/final-v1.mp4`. `finish_audio.py` uses the pinned
video-use two-pass normalization helper, targets −16 LUFS and −1.5 dBTP, and
copies the video stream unchanged. `verify.py` now extracts all thirty visual
beat midpoints in addition to chapter-boundary filmstrips and the ending.
Final measured outcome and review are recorded in the local verification report;
the earlier rendering measurements below describe the previous version.

### Follow-up: channel research and actual Remotion prototype

The user requested several Stupy Doo videos be investigated and a new prototype
made with Remotion or a video-use-supported tool. Reviewed the existing moth Short
plus actual downloaded shoelace (`giSlwCqtrMA`), shell (`ULowbuFTq1g`) and bee-play
(`nv5ViFsvwhY`) videos through timecoded frames and automatic captions. Findings,
source links and limitations are in
[the reference review](../../experiments/remotion-explainer/REFERENCE-REVIEW.md).
Reference footage remains ignored under `out/stupy-channel-review/`.

Implemented [a separate Remotion experiment](../../experiments/remotion-explainer/README.md)
using pinned Remotion 4.0.538, React, bundled licensed font and original SVG art.
Reused the first prototype's narration and word timings for a direct visual
comparison. No new speech/provider calls, production generation edits or uploads.
Video-use supplies the editing/review workflow and filmstrip helper; Remotion
actually composes/renders this version, without the upstream FFmpeg assembly step.

Final: `out/remotion-explainer/edit/final.mp4`, **145.20 seconds, 1080×1920,
30fps, H.264/AAC, 27,625,360 bytes**. TypeScript check passed; full media decode,
duration/size/codec checks passed. Twenty scene samples, nine cut filmstrips and
ending samples are saved beside it, along with measurements and independent
critique. Final output hash is recorded in `verification.json` and critique.
Audio measures **−20.0 LUFS, 2.7 LU range, −4.6 dBFS true peak**; no listening
assessment or full real-time playback was performed. Source and reproduction
instructions are portable; generated speech must be transferred or recreated.

Three review passes corrected encoding and fingertip contact defects. Remaining
limits: opening decorative hand partly overlaps a temperature label; illustration
is flatter and compositions hold longer than the reference channel. The lattice
is schematic. Treat this as a complete reviewable prototype, not equivalent
channel production quality or an unattended editing pipeline. No integration,
commit or push was requested. Existing Brainrot dashboard still returned HTTP200
at localhost5173 during this work; no services were restarted.

The user approved a standalone video-use explainer prototype before deciding on
production integration. Implemented it under
[`experiments/video-use-prototype/`](../../experiments/video-use-prototype/README.md),
with separate locked Python dependencies, bundled licensed DM Sans, an original
365-word factual script, ten animated diagram scenes, and pinned selected MIT
video-use helpers (`43cfc566833548093455c9d4a46bd69913b7e552`). Three Codex agents
authored animation sections in parallel; another agent critiqued the finished file.

The finished local file is `out/video-use-prototype/edit/final.mp4`: **145.20 seconds,
1080×1920, 24fps, H.264/AAC, 4,963,266 bytes**. Narration is 145.178 seconds. The
output directory also contains a scene plan, exact word timings, transcript/SRT,
per-scene cached renders, EDL, contact sheet, cut-boundary filmstrips and measurements.
These are ignored local artifacts; transfer them deliberately or reproduce them on
another computer. No global skill installation is needed by the source.

The prototype uses Brainrot's existing TTS and Pillow/FFmpeg animations, then the
actual video-use concat/EDL finishing and inspection helpers. Guy is explicitly
selected for this experiment: Andrew returned audio with sentence boundaries but
failed with requested word boundaries in live probes. Production voice settings
were not changed. No ElevenLabs transcription, paid model API, Claude validation,
database job or publication call was used by the prototype. This demonstrates an
interactive agent workflow; it is not an unattended editor or a queue integration.

Full media decode passed, with all nine visual cut boundaries and opening/ending
sampled. Audio measures **−14.3 LUFS, 2.9 LU loudness range, −0.9 dBFS true peak**.
Audio performance was not assessed by listening. Critique led to corrected ice heat
paths, a melting cue anchored after the actual spoken setup, and an explicit hot
surface contact diagram. Remaining visual pacing/style polish needs user review;
the prototype does not establish retention improvements or match the reference's
full visual variety. No integration decision has been made.

The user also asked to run Brainrot while work continued. Dashboard is available
at `http://localhost:5173`, API at `http://127.0.0.1:8001`, with a live worker host
reservation. API/frontend HTTP checks pass. Existing queue activity is separate
from the prototype. Local process records/logs are ignored under `out/dev-services/`;
inspect them before stopping anything. An earlier launcher also keeps a frontend
on 5189 with the wrong root; the working dashboard is on 5173. No tracked PIDs.

Fixed `brainrot.dev` to launch Vite from `web/`; the repository-root working
directory produced a 404 dashboard. Vite needed unsandboxed startup to read its
config/dependencies. Added `.vite/` to ignored generated files. The affected
portability/launcher test file passed **26 tests**, including disposable local
Postgres, using a fresh workspace test directory. Earlier runs hit sandbox/Postgres
and shared-temp permissions; the fresh-directory run passed. Prototype sources
compile and vendored hashes verify. No commit or push requested for this work.

## Reference discussion recovered — 2026-10-23

The user resumed the generation-capabilities discussion. Read the original local
conversation and inspected the saved reference's sampled frames, automatic Spanish
transcript, metadata and media duration. Reference: Stupy Doo's
`https://www.youtube.com/shorts/F7nZV4p5c40`, about memory across metamorphosis,
approximately 155 seconds. The ignored `out/reference-review/` directory on this
computer contains the video, transcript and contact sheet; these are local review
artifacts, not portable runtime dependencies. Audio performance was not assessed.

The earlier request prioritized computer portability, authorized factual writing
improvements, and deferred discussion of AI agents for video generation/editing.
No editor or animation engine was selected. Source inspection confirms that the
storytelling guidance includes the factual progression, while H2 still loops a
background with word captions. Matching the reference's visual approach would
require scene planning, topic-specific assets/diagrams, animation and narration
timing, with selective labels. This is a proposed direction, not an implemented
feature or an approved choice of tool/provider.

Initial recommendation: evaluate a local Remotion-based animated explainer mode
with one complete 90–180-second prototype before queue integration. Use an original
visual style, a small reusable scene library, structured model-produced scene plans,
and existing narration word timings. Save narration, plans and assets for selective
revision/retry. Review the applicable Remotion license before adoption. This remains
a recommendation awaiting the user's direction, not an implementation commitment.

The user then suggested `https://github.com/browser-use/video-use`. Reviewed its
README, skill/install guidance, dependencies and rendering/transcription/timeline
helpers through GitHub; nothing was installed or executed. It is an MIT-licensed
agent editing workflow plus Python/FFmpeg helpers, with optional animation engines
including Remotion, Manim and HyperFrames. Its default source-footage workflow
uses ElevenLabs Scribe. Revised recommendation: evaluate that agent editing
workflow for one local explainer prototype, adapting generated narration and word
timings to avoid unnecessary retranscription, then choose the animation engine
from actual results. Integration needs a dedicated tool-enabled editor stage:
current generation calls deliberately disable tools and external skill discovery.
Keep any adopted guidance/helpers project-owned, preserve license notices, pin
dependencies and retain existing duration, output, lease and publication controls.
No adoption, provider expense or installation has been authorized by this review.

The initial context-review turns changed only this handoff and ran no generation
or tests. The later authorized prototype and dashboard work is recorded above.

## Previous implementation session — 2026-10-22

The user wants to develop and generate locally from either their main computer
or another computer. They clarified that they do not want a central hosting
redesign. The solution uses independent checkouts, the same Supabase database,
and a verified media transfer when switching. AI-driven video editing is for a
later discussion. Factual storytelling improvements were authorized now.

The current branch is `master`. The user requested committing and pushing this
batch directly on that branch, without a new PR. Check Git status and history for
the exact commit and remote state. The user also requested this root `AGENTS.md`
and agent documentation structure.

## Implemented this session

- Locked Python dependencies, pip exports and Python 3.14 setup; a bootstrap
  script preserves existing settings. A local launcher starts API/worker/Vite
  with matching frontend credentials and origins.
- Checkout-root environment loading, project-local face detector and Whisper
  caches, and a bundled licensed Anton caption font.
- Streaming, checksummed media export/import with path validation, project
  identity checking and conflict protection; paginated missing-media audits.
- Migration 014 and a renewable local-media host reservation prevent updated
  workers on independent computers from consuming one shared queue concurrently.
  The migration is applied to this machine's configured Supabase project.
- Optional factual narrative progression: observation, mechanism/evidence,
  plausible alternative, distinguishing evidence, consequence. No invented
  studies or compulsory debunking. Fiction and source fidelity rules remain.
- A five-minute speech deadline cancels stalled provider streams and uses the
  existing retry policy, preserving saved scripts.
- Fixed mixed-platform scheduling: every bulk publication row includes an empty
  metadata object unless it has platform-specific metadata. Otherwise PostgREST
  filled missing metadata with NULL and violated the database constraint.

## Validation and live state

- Fresh locked Python environment: full offline suite passed **470 tests**.
  SQL tests used disposable local Postgres 18. Scheduling regression coverage
  also passed separately. Frontend production build passed.
- Codex-only factual preview about metal versus wood: 326 words, coherent
  heat-transfer explanation. No Claude usage for live validation.
- Exported and restored the real local media into a separate directory with
  checksum verification. The final snapshot contained 15 files, and all 12
  database-referenced paths were present. This is not an automatic sync service.
- Live API/dashboard smoke passed. A second synthetic host reservation was
  denied while this computer held its reservation.
- The existing job `daac226e-0eed-41c4-a517-89c637fabd17` completed speech and render,
  then exposed the scheduling bug. After the fix, retry reused its saved video
  and completed the generation job. Its original automatic YouTube upload was
  subsequently confirmed **published** in the database. TikTok and Instagram
  remain scheduled without their required credentials. No extra upload was
  created solely as a test. The older failed job
  `46a02463-092b-45b5-a767-5c04f3de3101` was not retried in this recovery; inspect
  its current state before taking further action.
- API and worker were reloaded; frontend remains at `http://localhost:5173`, API
  at `http://127.0.0.1:8001`. Inspect live state and ignored service metadata before
  reusing or stopping processes. No tracked PIDs or credentials belong here.
- Agent/runbook links and documentation-index coverage were checked with no
  broken local links or missing document entries; `git diff --check` passed.

## Remaining work and limits

1. Complete an actual second-computer setup using the
   [handoff guide](../moving-between-computers.md). Tests simulate relocation and
   restoration on Windows; another physical machine and other OSes remain to verify.
2. Pull the updated `master` on the other computer. Transfer credentials securely,
   sign in to the CLI there, and make a fresh
   media export after the last generation. Never copy a venv or `node_modules`.
3. Review the completed standalone video-use prototype before deciding on an AI
   editor integration, visual direction and animation engine. The production H2
   renderer still uses backgrounds and captions. Reference Short reviewed:
   `https://www.youtube.com/shorts/F7nZV4p5c40`.
4. H1 and approved Reddit H2b end-to-end checks remain separate from successful H2
   generation. H2 topic input does not require Reddit credentials.
5. Interrupted remote upload reconciliation, other platform authorization and
   analytics, and multi-host shared-file processing remain separate future work.
   Prompt checks do not establish improved viewer retention.

The original reliability plan under `docs/superpowers/` is historical. Its old
branches, credential blockers and cloud-only storage assumptions are superseded
by current code and the focused guides linked above.
