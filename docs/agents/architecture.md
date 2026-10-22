# Architecture for contributors

The app has three local services: React/Vite, FastAPI and a long-running Python
worker. Supabase/Postgres stores jobs, saved content, publishing settings and
analytics. Local disk stores media by default. Vercel builds the static frontend;
it does not run the local generation worker or store durable videos.

## Code map

| Area | Entry points |
| --- | --- |
| Environment and startup | `brainrot/config.py`, `brainrot/dev.py`, `scripts/bootstrap.py` |
| HTTP API and browser access | `brainrot/api.py`, `web/src/api.js` |
| Workspace, queue, output | `web/src/pages/Workspace.jsx`, `VideoDetails.jsx`, `brainrot/outputs.py` |
| Execution | `brainrot/worker.py`, `brainrot/pipelines.py`, `brainrot/domain/`, `brainrot/application/` |
| Database contracts | `brainrot/db.py`, ordered `migrations/*.sql` |
| Media and computer handoff | `brainrot/media.py`, `brainrot/portable.py`, `brainrot/host.py` |
| Topic and Reddit stories | `brainrot/script.py`, `brainrot/pipeline.py`, `brainrot/reddit.py` |
| Speech and compositing | `brainrot/tts.py`, `brainrot/render.py`, `brainrot/assets/fonts/` |
| Repurposing | `brainrot/repurpose.py`, `brainrot/models.py` |
| Publishing and pacing | `brainrot/scheduler.py`, `brainrot/publish.py` |
| YouTube | `brainrot/youtube.py`, `youtube_metadata.py`, `youtube_sync.py`, `web/src/pages/YouTube.jsx` |
| Optional references and backgrounds | `brainrot/research.py`, `brainrot/library.py` |
| Diagnostics | `brainrot/observability/`, `docs/operations.md` |

## Job flow

The API validates input and saves a pending job with provider, intensity and
publishing choices. The worker reserves the local-media host, claims a job
through SQL, renews its job lease and dispatches through the pipeline registry.
SQL checks ownership on stage and outcome writes. Transient failures retry with
backoff; expired job leases are recovered. Permanent errors stop the attempt.

- **H2/topic:** save script → chapters → select background → title and paced
  narration → captions and vertical render → local files → publication schedule.
- **H2b/Reddit:** filter approved API reads → faithful retelling → H2 rendering.
- **H1/repurpose:** source download → captions or Whisper transcript → model-selected
  moments → face-tracked crop and source speech → local clips → schedule.

Retries reuse saved scripts and completed outputs. Inspect the chapter/clip state
before regenerating anything. A successful job does not imply that every platform
has credentials or has published it. Housekeeping runs pacing, due uploads, media
cleanup and periodic YouTube synchronization.

Publication claims prevent competing uploads. Queueing a target is idempotent.
Bulk publication rows all need non-null `metadata`, even when only the YouTube
row has options: PostgREST uses the union of columns in a bulk request.

## How writing guidance is injected

`script.py` explicitly reads `brainrot/skills/brainrot-storytelling/SKILL.md` and
combines it with the task prompt, premise-intent rules and intensity/slang
instructions. `youtube_metadata.py` explicitly reads the publishing skill and
uses finished narration and supplied attribution to draft cached metadata.
These skills travel with Git and apply to either supported local provider.

`llm.py` selects the saved provider and validates typed JSON responses. Local
Codex and Claude calls run in isolated temporary working directories with tools,
plugin discovery and MCP access disabled. Repository `AGENTS.md`, global skills
and interactive MCP configuration are not automatically injected into these calls.
The optional Wikidata MCP configuration supports interactive project sessions;
the app's reference search uses its own backend adapter.

Editing a runtime skill affects newly generated content; a retry keeps its saved
script or metadata. Prompt improvements do not prove audience retention gains.
Current H2 video editing remains deterministic FFmpeg compositing over backgrounds.
