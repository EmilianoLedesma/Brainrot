# brainrot

Generates and auto-publishes short vertical video (YouTube Shorts, Reels, TikTok)
from three sources:

- **H1 — repurposing**: a YouTube link becomes 9:16 clips with face tracking and captions.
- **H2 — brainrot**: a topic becomes an LLM-written story narrated over a looping background.
- **H2b — Reddit narrator**: filtered subreddit posts, rewritten and chaptered, through the H2 pipeline.

All persistent state lives in Supabase: rows in Postgres, media in the `media`
Storage bucket. Nothing on the local disk is expected to survive a job.

## Layout

    brainrot/db.py         Supabase client, job helpers, media upload
    brainrot/api.py        FastAPI: job creation plus read-only views for the dashboard
    brainrot/worker.py     claims pending jobs and runs the matching pipeline
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
    migrations/            SQL applied by hand in the Supabase SQL editor
    test_db.py             Supabase round-trip check (needs credentials)
    test_pipeline.py       offline self-checks for captions, chaptering, reframing

Pipeline modules (`story.py`, `render.py`, `reddit.py`, `repurpose.py`) arrive with
their phase. FastAPI and a job queue arrive when something other than a local CLI
needs to trigger a run.

## Setup

1. Create a Supabase project.
2. Apply `migrations/001_init.sql` — paste it into the SQL editor, or run
   `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/001_init.sql`. It creates the
   enums, ten tables, indexes, RLS, and the private `media` bucket.
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

Open http://localhost:5173. Three tabs: create a job, watch the job list, play
finished videos.

`DASHBOARD_API_KEY` is a shared secret sent as the `X-API-Key` header; the API
rejects every request while it is unset. `web/.env` carries the same value as
`VITE_API_KEY`, and that file is gitignored — a Vite `VITE_` variable is baked into
the bundle, so only ever serve this dashboard somewhere private.

The job list polls every 2s rather than using Supabase Realtime. Realtime from the
browser would need `SELECT` policies for `anon` on `jobs`, and the anon key ships in
the JS bundle, so that would make the table readable by anyone with the project URL.
Reading through the API keeps RLS closed.

Until the Phase 1-3 pipelines exist, a created job stays `pending` (nothing consumes
it) and the gallery stays empty (nothing renders into `clips` or `story_chapters`).
