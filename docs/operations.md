# Operations

The API, worker and dashboard share Supabase as the source of truth. PostgreSQL
owns claims, lease guards, retries, stage records and publication claims. New media
lives on persistent local disk by default; rows keep relative paths. Legacy cloud
objects can be cached locally. Media and model caches can travel in a verified
handoff archive; see [moving between computers](moving-between-computers.md).
Redis/RabbitMQ, separate worker pools and horizontal scaling remain deferred.

## Start and inspect

Apply every unapplied migration through 014 before starting this version. Run
`python scripts/bootstrap.py`, install FFmpeg/ffprobe, and configure root `.env`.
H1 bootstraps its detector on first use, or fetch it in advance with
`python -m brainrot.cli setup-face-model`. Add a
background for H2/H2b with `python -m brainrot.cli add-background background.mp4`.
The model command checks a pinned SHA-256 before upload; a failed download cannot
leave a partial local detector cache.

For local development, start the dashboard, API and worker together:

```sh
uv run --locked python -m brainrot.dev
```

The worker polls every five seconds. Chapter pacing and publishing run when idle
and between jobs at least once every five minutes while busy. A single long job
can delay housekeeping until it finishes.

Workspace -> Queue shows status, current stage, attempt, duration and a short
plain-language error message. Queue, Inspect, and forms never render upstream
error strings. Redacted diagnostics remain in API responses (browser developer
tools -> Network); full stored tracebacks remain in worker/database diagnostics.
New topic jobs use five named Brainrot steps, defaulting to Playful; the API keeps
its numeric intensity contract. Its saved
value appears in Review, Queue and Inspect and controls script style for either
local model integration. Legacy jobs without it keep their original prompt.
Inspect shows only the current attempt's stages and publication states. Retry
clears the displayed stages immediately; they stay empty until the next attempt
starts. Earlier attempt records remain available in API responses for diagnostics.
A completed generation job can still have scheduled publications; it does not
imply an upload succeeded.
The view retains its last successful response during a connection failure.
Queue requests have a 15-second deadline. Output allows 45 seconds for media-link
signing on cold connections. Failed reads retry after two seconds; successful
Output reads refresh every 15 minutes, and existing media remains visible on errors.
Database network operations have an eight-second timeout. The worker logs
transient connection failures and resumes its loop instead of exiting.

Repeated `GET /jobs/{uuid}` requests returning HTTP 200 are normal inspector
polling; the job's status and stage history describe pipeline failures.
Narration uses the locked edge-tts version. Refresh dependencies with
`uv sync --locked` and restart the worker when updating. Each narration attempt
has a five-minute deadline; a stalled stream is cancelled and retried using the
saved script under the existing retry policy.

Delete opens a confirmation dialog for any job, including running work. Confirming
revokes its lease and removes its related database rows. The current operation
may finish, but cannot record completion or start a later stage. An active platform
upload blocks deletion with HTTP 409. Related generated media is removed, with
durable cleanup for failed removals and guards against late writes. Shared
backgrounds and existing remote platform posts remain. Requires migrations
`006_delete_jobs.sql` and `008_delete_job_media.sql`.

Inspect, Retry, and Delete are arranged in one row. Retry appears for failed jobs
and requeues the same job using its saved progress. Scripts, finished chapters/clips,
publications, and stage history remain intact; attempt numbers keep increasing.
Each explicit retry permits up to three more attempts. Duplicate requests while
already pending are harmless, and running/completed jobs reject retries. Failed
publication uploads are not retried by this action. Requires `007_retry_jobs.sql`.

Authenticated endpoints:

| Endpoint | Result |
|---|---|
| `GET /jobs?limit=50` | Newest jobs; limit 1–200 |
| `GET /jobs/{uuid}` | Job, stage history and publication states |
| `POST /jobs/{uuid}/retry` | Requeue failed work; 404 if absent, 409 if running/completed/cancelled |
| `DELETE /jobs/{uuid}` | Confirmed deletion; 204 on success, 404 if absent, 409 during an upload |
| `GET /metrics` | Prometheus text format 0.0.4 |

All require `X-API-Key: <DASHBOARD_API_KEY>`. Response fields are allowlisted;
errors are redacted, summarized and bounded. Job input rejects extra fields,
blank topics and unsupported video URLs. The browser does not receive lease
tokens, raw database rows or service-role credentials. The existing shared
dashboard key is bundled in Vite, so serve the dashboard privately.

## Claims, retries and recovery

Jobs move `pending -> running -> done` or `failed`. Waiting retries stay
`pending` with a future `run_after`. A claim increments `attempts`, records an
owner and establishes a ten-minute lease. The worker renews every minute.
Completion, failure, renewal and stage mutations require the current owner and
an unexpired lease. Recovery closes unfinished stages as `abandoned`.

Network/transport errors, timeouts, rate limits, HTTP 408/425 and 5xx responses
retry with `min(30s * 2^(attempt-1), 30min)` backoff. The default maximum is
three total attempts, so normally there are two waiting intervals: 30s and 60s.
Unrecognized errors, missing required assets and model refusals fail immediately.
Local CLI login, quota/exit and invalid-output errors are terminal setup/result
errors; local CLI timeouts follow the bounded retry policy.
An expired lease returns the job to pending, or fails it if attempts are exhausted.

Retries reuse the saved story, transcript, selected moments and finished outputs.
Unique constraints prevent duplicate job-derived stories/videos and duplicate
target/platform publications. Work performed before its result was saved can
still repeat after a crash, including a provider call. This is not an exactly-once
guarantee for an external service.

For a job that appears stuck:

1. Check its status, stage and error in Inspect.
2. Check worker logs for the job ID and the latest lease renewal failures.
3. Restore database connectivity and restart the supervised worker if needed.
4. Let the ten-minute lease expire and recovery run; do not clear a live lease.
5. For a terminal failure, resolve the cause before creating replacement work.
   There is no dashboard retry/reset action in this increment.

Lease loss stops a worker at the next guarded stage boundary. A provider call
already in progress can finish before that boundary; publication claims provide
an additional gate for uploads.

## Publishing reconciliation

Only a caller that atomically changes `scheduled -> uploading` may upload.
Worker housekeeping and the CLI can run concurrently without taking the same
publication. Missing platform credentials leave it scheduled.

Publishing does not retry automatically. If the platform accepts a video and
the response is lost, the publication can be `failed`; a worker crash can leave
it `uploading`. Check the destination account before any manual reset. Record
the confirmed remote ID/result when accepted, or reset to scheduled only after
confirming the upload did not occur. Never bulk reset ambiguous uploads.

## Logs and metrics

Worker and publication boundary events use the standard-library JSON logger.
Events include timestamp, event name and the available job/pipeline/stage/scope/
attempt/worker context. Configured credentials, bearer tokens, credential
assignments and URL passwords are redacted from saved errors. Application events
omit prompts, content bodies and provider payloads; third-party library output
is outside this logger.

Configure a Prometheus scrape header `X-API-Key` using its [`http_headers`
configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#http_config)
or a private proxy that adds the header. Keep the key in a protected
secret file. Scrape the API host, with the same access boundary as other operations.

| Metric | Meaning |
|---|---|
| `brainrot_jobs_processed_total` | Attempts entering running, by pipeline |
| `brainrot_jobs_completed_total` / `brainrot_jobs_failed_total` | Terminal outcomes |
| `brainrot_jobs_retried_total` / `brainrot_jobs_recovered_total` | Retry scheduling / expired lease recovery |
| `brainrot_publications_published_total` / `brainrot_publications_failed_total` | Observed upload outcomes, by platform |
| `brainrot_queue_depth` | Current row counts by pipeline and state, including terminal states |
| `brainrot_queue_ready` | Pending jobs whose run_after has arrived |
| `brainrot_job_duration_seconds` | Finished attempt durations, including failed/abandoned attempts |
| `brainrot_stage_duration_seconds` | Finished stage durations, including failed/abandoned stages |
| `brainrot_api_duration_seconds` | Request latency by route template, method and status |

Job/stage/publication observations are inserted by database triggers and survive
API/worker restarts. They begin at migration 004; earlier work is not backfilled.
The journal excludes job IDs, content and URLs, and retains observations when a
job is deleted. API latency is local to each API process and resets on restart.
Scrape individual API instances if aggregating latency across multiple processes.

The journal currently grows without compaction, and scrapes aggregate it in SQL.
Monitor its size and scrape latency; introduce rollups/retention before sustained
large volumes. Do not delete observations casually: their removal resets durable
counter history. Stage labels are bounded to known names plus `other`, and request
labels use route templates rather than user-provided URLs.

## Migrations and rollback

Take a database backup and check existing duplicate derived rows before applying
migration 002's uniqueness constraints. Stop old workers before upgrading. The
migrations add schema and guards without dropping application data; migration
002 also returns legacy running jobs without leases to pending.

Apply each file once, in order, with SQL-editor error reporting or
`psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/<file>.sql`. Use a transaction
where supported. Reload the REST schema cache after applying RPC changes:

```sql
notify pgrst, 'reload schema';
```

There are no automatic down migrations. Prefer a forward correction. If reverting
application code, stop workers and deploy a compatible revision while retaining
the additive tables/columns. Do not drop tables, lease functions or triggers under
running workers. Reverting to the pre-lease worker removes the ownership guarantee
and is not a safe operational rollback.

## Validation and current limits

```sh
pip install -r requirements-dev.txt
python -m pytest -q
python test_pipeline.py
python test_db.py
python test_live.py
npm ci --prefix web
npm run build --prefix web
```

Pytest SQL tests use a throwaway local Postgres via `PG_BIN` or `pg_ctl` on PATH;
they do not connect to Supabase. Ensure SQL tests actually run rather than skip
when validating a release. The offline pipeline script exercises real FFmpeg.

`test_db.py` uses Supabase REST/Storage, deletes its own delayed diagnostic job
and file, and leaves compact metric observations. `test_live.py` uses
`DATABASE_URL` with a transaction-local synthetic pipeline to test worker retry,
stage history, JSON logs, metrics and authenticated API responses, then rolls back.
Run it while other workers are idle; it verifies that pre-existing job counts and
metric observation counts remain unchanged. Neither live script calls Claude,
Reddit, YouTube download or publishing APIs.

For browser validation, start `npm run dev --prefix web -- --host 127.0.0.1 --port 5189`,
then run `python tests/browser/check_workspace.py --url http://127.0.0.1:5189`.
It uses synthetic API responses and checks desktop/mobile, English/Spanish,
polling and retained data after a connection failure. It uses installed Edge on
Windows; elsewhere install Playwright Chromium with `python -m playwright install chromium`.

As of 2026-10-21, live migrations, Storage, lease/stage/metrics/read-model smoke
checks and OpenCV detector loading pass. Generation now supports the local
Claude Code and Codex CLIs using their subscription sign-ins; an Anthropic API
key is needed only when explicitly selecting the `anthropic` provider.
See [local models](local-models.md) for setup and provider validation.
Real H1/H2/H2b full-pipeline acceptance remains separate from successful script
generation. H2b still requires approved Reddit credentials; typing an H2 topic
requires no Reddit access.

YouTube now has OAuth onboarding, reviewed uploads, optional automatic publishing,
and bounded performance ingestion. See [integrations](integrations.md) for setup,
current validation limits, and migration 013. TikTok/Instagram authorization and
analytics remain separate. Without metrics the scheduler waits 24h, then uses the
previous publication plus 48h. Redis/RabbitMQ and scaling remain outside this increment.
