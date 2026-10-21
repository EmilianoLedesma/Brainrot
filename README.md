# brainrot

Generates and auto-publishes short vertical video (YouTube Shorts, Reels, TikTok)
from three sources:

- **H1 — repurposing**: a YouTube link becomes 9:16 clips with face tracking and captions.
- **H2 — brainrot**: a topic becomes an LLM-written story narrated over a looping background.
- **H2b — Reddit narrator**: filtered subreddit posts, rewritten and chaptered, through the H2 pipeline.

All persistent state lives in Supabase: rows in Postgres, media in the `media`
Storage bucket. Nothing on the local disk is expected to survive a job.

## Layout

    brainrot/db.py         Supabase client, leased job/stage helpers, media upload
    brainrot/api.py        FastAPI: job creation plus read-only views for the dashboard
    brainrot/worker.py     leases pending jobs, runs the matching pipeline, retries/recovers
    brainrot/domain/       job states and the pipeline contract (no I/O)
    brainrot/application/  retry policy, pipeline registry, stage tracking and pacing policy
    brainrot/observability/ structured execution logs and Prometheus metrics
    brainrot/pipelines.py  H1/H2/H2b adapters and default pipeline registration
    brainrot/llm.py        typed generation via Claude Code, Codex or explicit Anthropic API
    brainrot/script.py     topic -> story, Reddit post -> retold story
    brainrot/tts.py        edge-tts narration with per-word timings
    brainrot/render.py     ffmpeg: looping background + narration + karaoke captions
    brainrot/pipeline.py   H2/H2b: script -> chapters -> rendered video
    brainrot/reddit.py     H2b: subreddit scan and post filtering
    brainrot/repurpose.py  H1: YouTube -> transcript -> moments -> 9:16 face-tracked clips
    brainrot/scheduler.py  publication queue and retention-based chapter pacing
    brainrot/publish.py    uploads due publications to the three platforms
    brainrot/cli.py        operator commands
    web/                   Vite + React dashboard (new job, job list, gallery)
    migrations/            SQL applied by hand in the Supabase SQL editor, in order
    tests/                 pytest suite; SQL tests run against a throwaway local Postgres
    test_db.py             Supabase round-trip check (needs credentials)
    test_live.py           rollback-only live worker/API smoke with synthetic operations
    test_pipeline.py       offline self-checks for captions, chaptering, reframing
    docs/                  reliability baseline, spec and plan

## Setup

1. Create a Supabase project.
2. Apply every file in `migrations/` in order — paste each into the SQL editor, or run
   `for f in migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done`.
   `001_init.sql` creates the enums, ten tables, indexes, RLS, and the private `media`
   bucket. `002_job_execution.sql` adds job leases, retries and idempotency keys; the
   worker needs it. `003_stage_execution.sql` adds stage records, lease-guarded
   stage functions and automatic closure of abandoned stages. `004_operational_metrics.sql`
   adds durable metric observations; `005_execution_read_models.sql` adds the dashboard
   read models. `006_delete_jobs.sql` adds guarded queue deletion and
   `007_retry_jobs.sql` adds explicit retries that preserve saved progress.
   `008_delete_job_media.sql` adds durable removal of deleted jobs' media.
   `009_background_rotation.sql` adds persistent per-story background rotation.
   Apply all nine before starting this version.
3. `cp .env.example .env` and fill in `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
   (Project Settings -> API). The service_role key bypasses RLS — server-side only.
4. `pip install -r requirements.txt`
5. `python test_db.py` -> `phase 0 ok`
6. Install FFmpeg/ffprobe on the worker host. For local generation, sign in to
   Claude Code with `claude auth login` or Codex with `codex login` on that host.
   Set `BRAINROT_LLM_PROVIDER=claude-code` (the default) or `codex` in `.env`.
   Local modes use the saved subscription login and require no API key.
   H2/H2b need an active background: `python -m brainrot.cli add-background background.mp4`.
   H1 needs `python -m brainrot.cli setup-face-model`, which downloads pinned,
   checksum-verified OpenCV YuNet weights and uploads them to the private bucket.
   H2b additionally needs approved Reddit API access and the Reddit variables in
   `.env.example`. Platform publishing credentials are configured separately.

Preview a topic without creating a job or publishing:

```sh
python -m brainrot.cli generate-script "Why octopuses can open jars" --provider claude-code
python -m brainrot.cli generate-script "Why octopuses can open jars" --provider codex
```

Workspace's Model selector chooses Claude or Chat GPT for each new topic or
repurpose job. The choice appears in Review and is saved with the job for every
attempt. Each integration uses its configured model; the selector does not pick
individual model versions.

For topic generation, **Brainrot level** snaps between five named steps:
Grounded, Playful (the default), Chaotic, Unhinged and Max brainrot.
It changes the script's tone, slang, pacing,
exaggeration and story developments. Ordinary real-world topics stay factual;
clearly invented premises are developed as fiction. Higher levels increase comic
delivery for factual subjects and can escalate events inside fictional stories.
Review, Queue and Inspect show the saved setting.
Retries reuse an existing saved script; choose a new job to generate a different
intensity. Repurposing keeps the source video's spoken content.

Jobs without a saved selection use the provider in `.env` for topic scripts,
Reddit rewrites and H1 moment selection. Restart the worker after changing that
default. There is no automatic
fallback to another provider or paid API. Subscription limits still apply, and
account-level extra usage settings can incur charges. Local adapters are intended
for your own private worker, running as the signed-in OS user.

The existing API remains available only with `BRAINROT_LLM_PROVIDER=anthropic`
and `ANTHROPIC_API_KEY`. See [local model setup](docs/local-models.md) for login,
Windows executable discovery, timeouts and deployment boundaries.

## Phases

| Phase | Scope | State |
|---|---|---|
| 0 | Schema, buckets, Supabase access layer | done |
| 1 | H2: topic -> script -> TTS -> render | done |
| 2 | H2b: Reddit scan, rewrite, chapters | done |
| 3 | H1: download, transcribe, face-track reframe | done |
| 4 | Publishing scheduler, retention-based chapter pacing | done |
| 5 | YouTube / TikTok / Instagram posting | uploaders built, unauthorized |

Phase 5 uploads but cannot authorize. There is no OAuth consent flow in the code -
registering each developer app and granting consent is a manual, browser-bound
step. `publish.py` reads whatever tokens are in `platform_credentials` and skips
any platform that has no row, so the worker keeps running while apps are pending.

Once an app exists, insert its row:

    db.client().table("platform_credentials").upsert({
        "platform": "youtube",
        "data": {"access_token": "...", "refresh_token": "...",
                 "client_id": "...", "client_secret": "..."},
    }, on_conflict="platform").execute()

A platform with no row is skipped: its publications stay `scheduled` and go out
once the row exists.

Per platform: YouTube wants `access_token` plus `refresh_token`/`client_id`/
`client_secret` (it refreshes itself, since Google tokens last an hour); TikTok
wants `access_token`; Instagram wants `access_token` and `ig_user_id`.

Two platform facts worth knowing before you test: TikTok forces every post from an
unaudited client to private, and YouTube has no API field that declares a Short -
a vertical video under three minutes simply becomes one.

## Running it

    python -m brainrot.worker                         # claim jobs, render, pace chapters
    python -m brainrot.cli add-background clip.mp4    # H2/H2b need at least one
    python -m brainrot.cli scan-reddit                # queue jobs from subreddits
    python -m brainrot.cli tick                       # pacing pass, list what is due
    python -m brainrot.cli publish                    # upload everything that is due
    python test_pipeline.py                           # offline checks, no credentials

Generated stories rotate through active backgrounds in order of least recent
use, starting with `background_clips.rotation_order`. Each story saves its choice,
so all its chapters and retries use the same gameplay. Concurrent workers share
the same rotation in Supabase. Adding or deactivating a clip changes the pool
for new assignments; existing stories keep their assigned background.

### Job lifecycle

    pending --claim--> running --> done
                          |------> failed                 (permanent error, or out of attempts)
                          '------> pending (run_after)    (transient error: retry later)
    running, lease expired --recover--> pending | failed

A claim leases the job to one worker for ten minutes, and the worker renews it
every minute while the pipeline runs. If the worker dies, the lease lapses and the
next worker iteration puts the job back in the queue. Network errors, timeouts,
rate limits and 5xx responses are retried after 30s, 60s, 120s... (capped at 30
minutes) up to `jobs.max_attempts` (3); anything else fails the job, since retrying
a bug repeats the same model work. A retried job resumes: it reuses
the story, transcript and moment selection its earlier attempt saved and only
renders what is missing.

The queue's Delete action opens a confirmation dialog, then removes the job and
its related database rows. Deleting a running job revokes its lease; its current
operation may finish, but it cannot record completion or start another stage.
Active platform uploads must finish before deletion. These checks are atomic with
worker claims. Audio, videos and saved source files are removed from Supabase
Storage as well. Apply `008_delete_job_media.sql` before deploying this behavior.
A durable cleanup queue retries Storage failures and rechecks any in-flight
upload after its old lease expires; the worker also removes late uploads when
their owner has been deleted. Shared background clips stay in the library.
Posts already published on external platforms are not removed. Database network
operations have an eight-second timeout. Queue reads have a 15-second deadline;
Output allows 45 seconds for media-link signing and promptly retries failed reads;
the queue retries failed reads and keeps the last successful update visible.

Failed jobs have a Retry action alongside Inspect and Delete. Retry requeues the
same job, keeping its saved script, completed chapters/clips, and attempt history.
Each explicit retry grants up to three further attempts. Finished jobs and running
jobs cannot be retried, and repeated clicks cannot create a second job.

Publishing is not retried. A failed upload stays `failed`, because an upload that
timed out after the platform accepted it would otherwise post twice. A publication
stuck in `uploading` means the worker died mid-upload: check the platform before
resetting it to `scheduled`.

## Tests

    pip install -r requirements-dev.txt
    pytest                    # unit tests plus SQL tests against a local Postgres
    python test_pipeline.py   # ffmpeg end-to-end checks
    python test_db.py         # real Supabase row/Storage smoke; removes its own objects
    python test_live.py       # real DB worker/API retry smoke; rolls its transaction back

The SQL tests start a throwaway Postgres using `PG_BIN`, or find its binaries
through `pg_ctl` on `PATH` (falling back to `/usr/lib/postgresql/16/bin`). They
support Windows and Unix and skip if Postgres is not installed. They never use
`DATABASE_URL` or your Supabase project.

The two live scripts are explicit operator checks, outside pytest. `test_db.py`
leaves compact metric observations of its temporary job; `test_live.py` requires
`DATABASE_URL` and rolls back its synthetic work, including metric observations.
Neither calls a generation or publishing provider. See the
[operations guide](docs/operations.md) for browser checks and troubleshooting.

### Pipeline registration

`brainrot/pipelines.py` registers `repurpose` (H1), `brainrot` (H2), and `reddit`
(H2b). Each adapter accepts a `PipelineContext` and returns a `PipelineResult`
containing the story or source video id. The worker resolves the job's `kind`
through the registry, without branching on pipeline names. Unknown kinds fail
permanently. Register implementations in `create_registry()` to extend dispatch;
new database job kinds still require a migration of the `job_kind` enum.

### Stage execution

Worker-dispatched pipelines record major operations in `stage_executions`.
Each record includes the job, stage, chapter/clip scope, job attempt, worker,
status, timestamps, database-calculated duration and error. Retries keep earlier
attempts; reused scripts, transcripts and finished renders are not reported as
newly executed work. When an attempt ends, unfinished stages become `abandoned`.

Stages require a live lease. A worker that loses it stops at the next stage
boundary and leaves the job outcome to recovery. Legacy direct pipeline calls
have no leased context and do not create stage records. See
[stage execution details](docs/stage-execution.md).

### Logs, metrics and inspection

The worker emits JSON lifecycle events with job, pipeline, attempt, worker and
stage context. Saved errors and operational responses redact configured secrets;
logs omit prompts and provider payloads. Workspace -> Queue -> Inspect shows
attempts, current stage, duration, stage history and publication states.

`GET /metrics` requires the same `X-API-Key` as the other operational endpoints.
Job, retry, recovery, publication and duration metrics come from durable database
observations shared across worker/API processes, beginning with migration 004.
Queue gauges describe current rows; API latency is per API process and resets on
restart. [Metric names, scrape setup and limitations](docs/operations.md).

### Chapter pacing

Chapter one publishes immediately. Each later chapter waits on the previous one's
best reported retention: at or above 60% it follows after 12h, 40-60% after 24h,
below that 48h, and under 20% the story is dropped rather than given more slots.
If the platforms report nothing within 24h of a chapter going out, pacing falls
back to the slowest cadence instead of stalling the story forever.

The normalized analytics contract and pure pacing policy live in
`brainrot/application/analytics.py`. Platform analytics fetching remains deferred;
without ingested retention, the existing 48h fallback applies.

### Transcription

H1 uses YouTube's own captions when the video has them, which is free and instant.
`faster-whisper` runs only as the fallback, and downloads its model on first use.

## Connection note

The direct host `db.<ref>.supabase.co` only publishes an AAAA record, so it is
unreachable from IPv4-only networks. `DATABASE_URL` therefore points at the session
pooler, which is IPv4:

    postgresql://postgres.<ref>:<password>@aws-0-us-west-2.pooler.supabase.com:5432/postgres

Note the user is `postgres.<ref>`, not `postgres`, and the password must be
percent-encoded. This connection is used for migrations and explicit live SQL checks; the application code
in `brainrot/db.py` goes through the REST API with the service_role key.

## Dashboard

Two processes. The API holds the service_role key; the browser never sees it.

    uvicorn brainrot.api:app --reload --port 8000
    cd web && npm install && npm run dev

Open http://localhost:5173. Home, Docs and FAQ describe the product; Workspace
contains job creation, the job list and finished videos.

Queue includes per-job execution inspection. Requests poll sequentially every 2s,
keep the last successful response on connection failure and stop when the view closes.

`DASHBOARD_API_KEY` is a shared secret sent as the `X-API-Key` header; the API
rejects every request while it is unset. `web/.env` carries the same value as
`VITE_API_KEY`, and that file is gitignored — a Vite `VITE_` variable is baked into
the bundle, so only ever serve this dashboard somewhere private.

The job list polls every 2s rather than using Supabase Realtime. Realtime from the
browser would need `SELECT` policies for `anon` on `jobs`, and the anon key ships in
the JS bundle, so that would make the table readable by anyone with the project URL.
Reading through the API keeps RLS closed.

### Vercel deployment

Vercel hosts the Vite dashboard. Keep its Root Directory at the repository root;
`vercel.json` selects Vite, installs with `npm ci --prefix web`, builds with
`npm run build --prefix web`, and serves `web/dist`. This overrides automatic
FastAPI detection at the Python repository root.

The API and media worker run separately. Configure `VITE_API_URL` and
`VITE_API_KEY` in Vercel before building, and allow the dashboard origin in the
API's `DASHBOARD_ORIGINS`. See [deployment details](docs/deployment.md) and the
[documentation index](docs/index.md).

