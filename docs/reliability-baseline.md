# Reliability baseline

Task 1 of `docs/superpowers/plans/2026-09-17-brainrot-reliability-observability.md`.
This is how the system behaves at commit `39f6aa7`, before any reliability
work. Later tasks change it; this file records the starting point so those
changes can be checked against it.

## Test baseline

| Check | Result |
|---|---|
| `python test_pipeline.py` | 7/7 pass (offline, needs ffmpeg) |
| `python test_db.py` | not run: needs a real Supabase project in `.env` |
| `cd web && npm run build` | builds |
| pytest | not a dependency; `test_pipeline.py` is a script, not a suite |

## Job states

`job_status` enum in `migrations/001_init.sql`:

    pending -> running -> done
                       -> failed
    cancelled            (in the enum, but nothing sets it)

Compared with the spec's lifecycle:

| Spec | Database today | Note |
|---|---|---|
| `pending` | `pending` | same |
| `processing` | `running` | rename in the domain layer only; the enum stays |
| `completed` | `done` | same as above |
| `failed` | `failed` | same |
| `retry_wait` | none | needs `ALTER TYPE ... ADD VALUE`, or `pending` plus a not-before time |
| none | `cancelled` | not in the spec; keep it as a terminal state |

The column is `jobs.kind` (`repurpose`, `brainrot`, `reddit`), not `pipeline`.

## How jobs are claimed

`worker.claim()` makes two REST calls: it selects the oldest `pending` row, then
runs `update ... set status='running' where id=? and status='pending'`. This
compare-and-set guarantees one winner, but it has no lease:

- A worker that dies mid-job leaves the row `running` forever, and nothing
  recovers it.
- There is no worker id, attempt count, or heartbeat.

`db.py` only reaches Postgres through PostgREST with the service_role key, so
an atomic claim with `FOR UPDATE SKIP LOCKED` has to be a SQL function called
with `client().rpc(...)`.

## How failures are represented

`worker.run()` catches any exception and writes `status='failed'` with a
5-frame traceback in `jobs.error`. There is no classification into transient
and permanent errors, and there are no retries. One traceback string is the
only diagnostic.

Partial output survives a failure. If chapter 2 of 3 fails to render, the
`stories` row stays `pending`, chapter 1 is `ready`, and chapter 2 stays
`rendering`. H1 behaves the same way with `source_videos` and `clips`.

## Retries: where they happen today

Only inside libraries: the Anthropic SDK retries 429 and 5xx twice, and
yt-dlp retries its own downloads. Nothing in brainrot retries.

**The pipelines cannot be re-run safely in their current form.** This blocks
Task 4, so it matters for Task 3:

- **H2b**: `pipeline.produce` inserts a `stories` row with `reddit_post_id`,
  and that column is `unique`. A second attempt at the same job fails on the
  constraint, so the retry fails permanently.
- **H2**: a second attempt inserts a second `stories` row and duplicate
  chapters, then `scheduler.plan_story` queues chapter 1 for publication again.
- **H1**: a second attempt inserts a second `source_videos` row and new
  `clips`, and `plan_clip` queues each clip again.

Pipelines need get-or-create keyed on `job_id` (or on stage) before any retry
policy is switched on.

## How publishing is persisted

There is one `publications` row per (target, platform), with
`scheduled -> uploading -> published | failed`. `unique (platform,
platform_post_id)` stops the same returned post id from being recorded twice.
It does not stop the same video from being uploaded twice.

- `publish_one` sets `uploading` without checking that the row is still
  `scheduled`. The worker loop and `python -m brainrot.cli publish` can both
  pick up the same due row and post the video twice.
- A crash between "platform accepted" and "row updated" leaves the row in
  `uploading` forever. The current code never re-queues it, so this is safe,
  but it needs recovery by hand.
- `MissingCredentials` is raised inside `publish_one`'s `try`, so the row is
  marked `failed`, not skipped. The README says skipped. When credentials are
  added later, those rows never go out unless someone resets them by hand.
- Instagram polls with `time.sleep(60)` up to five times inside the worker
  loop, which blocks every other job for up to five minutes.

## Scheduler cadence

`scheduler.tick()` runs when `worker.run_once()` finds no job. A long backlog
of jobs therefore delays both pacing and publishing. The pacing table matches
the spec:

    retention >= 60%  -> +12h
    40% <= r < 60%    -> +24h
    20% <= r < 40%    -> +48h
    r < 20%           -> stop the story
    no data 24h after chapter N went out -> +48h

These are measured from the earliest `published_at` across platforms for the
previous chapter. Chapter 1 is queued on all three platforms as soon as it
renders. H1 clips are queued immediately.

**Nothing writes `chapter_metrics`.** No platform analytics are fetched, so
every story falls through to the 24h-silence branch and paces at 48h. The
retention policy is implemented but never fed data. Task 10 extracts the
policy, but real analytics ingestion is outside this increment unless it is
added explicitly.

## Things the original goal asked for that are not built

- H1 retention edits: zoom on key moments and reactive emoji overlays.
- Redis/Celery: replaced by a Supabase-polling worker. The spec defers a queue.
- The SKILL.md-per-capability layout: the project is a conventional Python
  package instead.
- H1 face model setup: `repurpose.py` downloads
  `models/face_detection_yunet_2023mar.onnx` from Storage, but no command or
  README step uploads it. A fresh project fails its first H1 job.

## Stale docs found during the review

- `README.md` says the pipeline modules "arrive with their phase", says
  FastAPI and a queue "arrive when...", and says "Until the Phase 1-3
  pipelines exist, a created job stays `pending`". All three are out of date.
- The `brainrot/api.py` module docstring says workers are "not built yet".
- The README says platforms without credentials are skipped. They are marked
  `failed` instead (see above).

## Test infrastructure available

PostgreSQL 16 binaries are installed in the dev container
(`/usr/lib/postgresql/16/bin`). Tasks 3 and 6 can therefore test their SQL
(claim RPC, leases, unique keys) against a real throwaway Postgres instead of
mocking PostgREST. That needs a small stub for the `storage` schema that
`001_init.sql` touches.
