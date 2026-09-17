# brainrot

Generates and auto-publishes short vertical video (YouTube Shorts, Reels, TikTok)
from three sources:

- **H1 — repurposing**: a YouTube link becomes 9:16 clips with face tracking and captions.
- **H2 — brainrot**: a topic becomes an LLM-written story narrated over a looping background.
- **H2b — Reddit narrator**: filtered subreddit posts, rewritten and chaptered, through the H2 pipeline.

All persistent state lives in Supabase: rows in Postgres, media in the `media`
Storage bucket. Nothing on the local disk is expected to survive a job.

## Layout

    brainrot/db.py        Supabase client, job helpers, media upload
    migrations/           SQL applied by hand in the Supabase SQL editor
    test_db.py            Phase 0 smoke check

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
| 1 | H2: topic -> script -> TTS -> render | next |
| 2 | H2b: Reddit scan, rewrite, chapters | |
| 3 | H1: download, transcribe, face-track reframe | |
| 4 | Publishing scheduler, retention-based chapter pacing | |
| 5 | YouTube / TikTok / Instagram posting | |

Platform OAuth is deliberately not implemented: the developer apps are registered
by hand first, in Phase 5.

## Connection note

The direct host `db.<ref>.supabase.co` only publishes an AAAA record, so it is
unreachable from IPv4-only networks. `DATABASE_URL` therefore points at the session
pooler, which is IPv4:

    postgresql://postgres.<ref>:<password>@aws-0-us-west-2.pooler.supabase.com:5432/postgres

Note the user is `postgres.<ref>`, not `postgres`, and the password must be
percent-encoded. This connection is used only for migrations; the application code
in `brainrot/db.py` goes through the REST API with the service_role key.
