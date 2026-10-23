# Pipeline and operations reference

Detailed execution notes moved from the main README. Run commands from the
repository root. For setup and current validation instructions, use the
[development guide](agents/development.md); for incident response, use
[operations](operations.md).

## Operator commands

```sh
uv run --locked python -m brainrot.cli generate-script "Why octopuses can open jars" --provider codex
uv run --locked python -m brainrot.cli add-background clip.mp4
uv run --locked python -m brainrot.cli scan-reddit
uv run --locked python -m brainrot.cli tick
uv run --locked python -m brainrot.cli publish
```

`generate-script` previews writing without creating a job or publishing. `scan-reddit`
queues stories using configured Reddit access. `publish` uploads due publications;
run it deliberately with the correct platform settings.

## Job lifecycle

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

    uv run --locked python -m pytest tests -q
    uv run --locked python test_pipeline.py
    uv run --locked python test_db.py    # explicit live Supabase check
    uv run --locked python test_live.py  # explicit rollback-only live SQL check

The SQL tests start a throwaway Postgres using `PG_BIN`, or find its binaries
through `pg_ctl` on `PATH` (falling back to `/usr/lib/postgresql/16/bin`). They
support Windows and Unix and skip if Postgres is not installed. They never use
`DATABASE_URL` or your Supabase project.

The two live scripts are explicit operator checks, outside pytest. `test_db.py`
leaves compact metric observations of its temporary job; `test_live.py` requires
`DATABASE_URL` and rolls back its synthetic work, including metric observations.
Neither calls a generation or publishing provider. See the
[operations guide](operations.md) for browser checks and troubleshooting.

## Pipeline registration

`brainrot/pipelines.py` registers `repurpose` (H1), `brainrot` (H2), and `reddit`
(H2b). Each adapter accepts a `PipelineContext` and returns a `PipelineResult`
containing the story or source video id. The worker resolves the job's `kind`
through the registry, without branching on pipeline names. Unknown kinds fail
permanently. Register implementations in `create_registry()` to extend dispatch;
new database job kinds still require a migration of the `job_kind` enum.

## Stage execution

Worker-dispatched pipelines record major operations in `stage_executions`.
Each record includes the job, stage, chapter/clip scope, job attempt, worker,
status, timestamps, database-calculated duration and error. Retries keep earlier
attempts; reused scripts, transcripts and finished renders are not reported as
newly executed work. When an attempt ends, unfinished stages become `abandoned`.

Stages require a live lease. A worker that loses it stops at the next stage
boundary and leaves the job outcome to recovery. Legacy direct pipeline calls
have no leased context and do not create stage records. See
[stage execution details](stage-execution.md).

## Logs, metrics and inspection

The worker emits JSON lifecycle events with job, pipeline, attempt, worker and
stage context. Saved errors and operational responses redact configured secrets;
logs omit prompts and provider payloads. Workspace -> Queue -> Inspect shows
attempts, current stage, duration, stage history and publication states.

`GET /metrics` requires the same `X-API-Key` as the other operational endpoints.
Job, retry, recovery, publication and duration metrics come from durable database
observations shared across worker/API processes, beginning with migration 004.
Queue gauges describe current rows; API latency is per API process and resets on
restart. [Metric names, scrape setup and limitations](operations.md).

## Chapter pacing

Chapter one publishes immediately. Each later chapter waits on the previous one's
best reported retention: at or above 60% it follows after 12h, 40-60% after 24h,
below that 48h, and under 20% the story is dropped rather than given more slots.
If the platforms report nothing within 24h of a chapter going out, pacing falls
back to the slowest cadence instead of stalling the story forever.

The normalized analytics contract and pure pacing policy live in
`brainrot/application/analytics.py`. YouTube performance ingestion now feeds
chapter pacing with reported average percentage watched. TikTok and Instagram
analytics remain deferred; without metrics, the existing 48h fallback applies.

## Transcription

H1 uses YouTube's own captions when the video has them, which is free and instant.
`faster-whisper` runs only as the fallback, and downloads its model on first use.
