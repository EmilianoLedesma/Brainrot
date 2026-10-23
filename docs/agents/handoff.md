# Handoff — 2026-10-23

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
