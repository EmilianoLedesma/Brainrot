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
    brainrot/application/  retry policy, pipeline registry and stage tracking
    brainrot/pipelines.py  H1/H2/H2b adapters and default pipeline registration
    brainrot/script.py     Claude: topic -> story, Reddit post -> retold story
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
    test_pipeline.py       offline self-checks for captions, chaptering, reframing
    docs/                  reliability baseline, spec and plan

## Setup

1. Create a Supabase project.
2. Apply every file in `migrations/` in order — paste each into the SQL editor, or run
   `for f in migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done`.
   `001_init.sql` creates the enums, ten tables, indexes, RLS, and the private `media`
   bucket. `002_job_execution.sql` adds job leases, retries and idempotency keys; the
   worker needs it. `003_stage_execution.sql` adds stage records, lease-guarded
   stage functions and automatic closure of abandoned stages. Apply both before
   running a worker from this version.
3. `cp .env.example .env` and fill in `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
   (Project Settings -> API). The service_role key bypasses RLS — server-side only.
4. `pip install -r requirements.txt`
5. `python test_db.py` -> `phase 0 ok`

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
a bug only pays for the same Claude call again. A retried job resumes: it reuses
the story, transcript and moment selection its earlier attempt saved and only
renders what is missing.

Publishing is not retried. A failed upload stays `failed`, because an upload that
timed out after the platform accepted it would otherwise post twice. A publication
stuck in `uploading` means the worker died mid-upload: check the platform before
resetting it to `scheduled`.

## Tests

    pip install -r requirements-dev.txt
    pytest                    # unit tests plus SQL tests against a local Postgres
    python test_pipeline.py   # ffmpeg end-to-end checks

The SQL tests start a throwaway Postgres using `PG_BIN`, or find its binaries
through `pg_ctl` on `PATH` (falling back to `/usr/lib/postgresql/16/bin`). They
support Windows and Unix and skip if Postgres is not installed. They never use
`DATABASE_URL` or your Supabase project.

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

### Chapter pacing

Chapter one publishes immediately. Each later chapter waits on the previous one's
best reported retention: at or above 60% it follows after 12h, 40-60% after 24h,
below that 48h, and under 20% the story is dropped rather than given more slots.
If the platforms report nothing within 24h of a chapter going out, pacing falls
back to the slowest cadence instead of stalling the story forever.

### Transcription

H1 uses YouTube's own captions when the video has them, which is free and instant.
`faster-whisper` runs only as the fallback, and downloads its model on first use.

## Connection note

The direct host `db.<ref>.supabase.co` only publishes an AAAA record, so it is
unreachable from IPv4-only networks. `DATABASE_URL` therefore points at the session
pooler, which is IPv4:

    postgresql://postgres.<ref>:<password>@aws-0-us-west-2.pooler.supabase.com:5432/postgres

Note the user is `postgres.<ref>`, not `postgres`, and the password must be
percent-encoded. This connection is used only for migrations; the application code
in `brainrot/db.py` goes through the REST API with the service_role key.

## Dashboard

Two processes. The API holds the service_role key; the browser never sees it.

    uvicorn brainrot.api:app --reload --port 8000
    cd web && npm install && npm run dev

Open http://localhost:5173. Home, Docs and FAQ describe the product; Workspace
contains job creation, the job list and finished videos.

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

