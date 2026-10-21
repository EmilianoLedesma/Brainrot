# Brainrot --- Reliability, Observability & Extensible Pipeline Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL:
> `superpowers:subagent-driven-development` (or
> `superpowers:executing-plans` when executing this plan).

**Goal:** Evolve the existing Brainrot pipeline system into a reliable,
observable and extensible job-processing platform without introducing a
new content pipeline in this increment.

**Architecture:** Incremental Domain/Application/Infrastructure
separation around the existing FastAPI + worker + Supabase architecture.
Existing H1/H2/H2b pipelines remain functional while job lifecycle,
leases, retries, idempotency, stage execution, metrics and pipeline
registration become explicit infrastructure.

**Tech Stack:** Python, FastAPI, Supabase/PostgreSQL, Supabase Storage,
React/Vite, FFmpeg, existing Brainrot integrations, pytest-compatible
test tooling, Prometheus-compatible metrics.

**Progress (2026-10-21):** Tasks 1–12 are implemented. Task 13's automated,
browser, live database/Storage and synthetic worker checks pass; real provider
pipeline checks remain pending credentials. Task 14's architecture review passes
for the tested boundaries, with H1/H2/H2b live acceptance still open.
PR #1 was merged before further implementation; subsequent changes are on
`feat/stage-execution` with no new PR. See [operations](../../operations.md)
for validation boundaries and the runbook.

**Spec path:**
`docs/superpowers/specs/2026-09-17-brainrot-reliability-observability.md`

**Global Constraints:** - Do not add a new content pipeline. - Do not
introduce Redis/RabbitMQ in this increment. - Do not rewrite the whole
codebase. - Preserve H1, H2 and H2b behavior. - Keep Supabase as the
source of truth. - Keep workers stateless. - Make schema changes
additive. - Follow TDD for behavior changes. - Do not invent schema
names/types before inspecting the current migration and repository
code. - Every task must leave the repository in a runnable state.

------------------------------------------------------------------------

## Task 1: Establish the baseline and current execution contract

**Files:** - Read: `brainrot/worker.py` - Read: `brainrot/pipeline.py` -
Read: `brainrot/db.py` - Read: `brainrot/scheduler.py` - Read:
`brainrot/publish.py` - Read: `brainrot/repurpose.py` - Read:
`brainrot/script.py` - Read: `brainrot/render.py` - Read:
`migrations/001_init.sql` - Read: `test_pipeline.py` - Read:
`test_db.py`

**Interfaces:** - Consumes: current repository behavior. - Produces:
documented baseline for subsequent changes.

### Step 1: Inspect current behavior

Read the worker loop, database helpers, scheduler and pipeline
implementations before changing anything.

Document: - current job states; - how jobs are claimed; - how failures
are represented; - where retries currently happen, if anywhere; - how
publishing records are persisted; - current scheduler cadence
implementation.

### Step 2: Run the existing tests

Run:

``` bash
python test_pipeline.py
python test_db.py
```

Expected: - existing tests pass or any baseline failure is recorded
before implementation starts.

### Step 3: Commit baseline documentation

``` bash
git add .
git commit -m "docs: establish brainrot reliability baseline"
```

------------------------------------------------------------------------

## Task 2: Define the job lifecycle and execution domain contract

**Files:** - Create: `brainrot/domain/jobs.py` - Create:
`brainrot/domain/pipelines.py` - Create: `tests/test_job_state.py` -
Create: `tests/test_pipeline_contract.py`

**Interfaces:** - Consumes: existing job data. - Produces: explicit
state transition and pipeline contracts.

### Step 1: Write failing tests

Test: - allowed transitions; - rejection of invalid transitions; -
terminal states; - pipeline result contract.

Example:

``` python
def test_processing_can_complete():
    state = JobState.PENDING
    state = transition(state, JobState.PROCESSING)
    state = transition(state, JobState.COMPLETED)
    assert state == JobState.COMPLETED
```

### Step 2: Run tests

``` bash
pytest tests/test_job_state.py tests/test_pipeline_contract.py -q
```

Expected: FAIL because the new domain contracts do not exist.

### Step 3: Implement the minimal domain layer

Define explicit states matching the real database model after inspecting
the current migration.

Implement: - state transition function; - `Pipeline`; -
`PipelineContext`; - `PipelineResult`.

Do not put Supabase or FFmpeg calls in this layer.

### Step 4: Run tests

``` bash
pytest tests/test_job_state.py tests/test_pipeline_contract.py -q
```

Expected: PASS.

### Step 5: Commit

``` bash
git add brainrot/domain tests
git commit -m "feat: define job and pipeline domain contracts"
```

------------------------------------------------------------------------

## Task 3: Add persistent execution metadata, leases and idempotency

**Files:** - Create: new additive migration under `migrations/` -
Modify: `brainrot/db.py` - Create: `tests/test_job_execution.py`

**Interfaces:** - Consumes: current jobs schema. - Produces: persistent
execution metadata and atomic claim semantics.

### Step 1: Inspect the existing migration

Before writing SQL, identify: - jobs table; - primary key; - current
status column; - timestamps; - foreign keys; - publication tables; -
existing unique constraints.

Do not duplicate existing columns.

### Step 2: Write failing tests

Cover: - successful claim; - second worker cannot claim the same live
lease; - lease expiry allows recovery; - attempt counter increments; -
idempotency key uniqueness.

### Step 3: Run tests

``` bash
pytest tests/test_job_execution.py -q
```

Expected: FAIL.

### Step 4: Write the additive migration

Add only the metadata actually required by the inspected schema.

Conceptually support: - attempt count; - worker/lease owner; - lease
expiration; - started/completed timestamps; - retry timestamp; - error
metadata; - idempotency key.

Prefer database-enforced uniqueness and atomic updates where possible.

### Step 5: Implement database helpers

Add repository-level operations for: - claim; - renew lease; -
complete; - fail; - schedule retry; - recover abandoned job; - check/set
idempotency.

### Step 6: Run tests

``` bash
pytest tests/test_job_execution.py -q
```

Expected: PASS.

### Step 7: Commit

``` bash
git add migrations brainrot/db.py tests
git commit -m "feat: add job leases retries and idempotency"
```

------------------------------------------------------------------------

## Task 4: Implement retry and abandoned-job recovery policy

**Files:** - Create: `brainrot/application/retry.py` - Modify:
`brainrot/worker.py` - Create: `tests/test_retry_policy.py` - Create:
`tests/test_recovery.py`

**Interfaces:** - Consumes: domain job state + repository. - Produces:
retry scheduling and recovery behavior.

### Step 1: Write failing tests

Cover: - transient error schedules retry; - permanent error ends in
failed; - exponential backoff is bounded; - maximum attempts end in
failed; - expired lease is recoverable; - active lease is not
recoverable.

### Step 2: Run tests

``` bash
pytest tests/test_retry_policy.py tests/test_recovery.py -q
```

Expected: FAIL.

### Step 3: Implement policy

Use a deterministic backoff function, for example:

``` text
delay = min(base * 2^(attempt-1), max_delay)
```

Keep classification separate from the worker loop.

### Step 4: Integrate recovery

The worker must: 1. recover expired jobs; 2. claim available work; 3.
renew leases during long operations; 4. persist retry/failure state.

### Step 5: Run tests

``` bash
pytest tests/test_retry_policy.py tests/test_recovery.py -q
```

Expected: PASS.

### Step 6: Commit

``` bash
git add brainrot tests
git commit -m "feat: add retry and abandoned job recovery"
```

------------------------------------------------------------------------

## Task 5: Make H1, H2 and H2b execute through a pipeline registry

**Status (2026-10-21):** Implemented in `brainrot/application/registry.py` and
`brainrot/pipelines.py`, with worker integration and registry regression tests.
The adapters preserve the existing entry points and database job-kind names.
Stage execution and subsequent infrastructure tasks are also implemented.

**Files:** - Modify: `brainrot/pipeline.py` - Modify:
`brainrot/repurpose.py` - Modify: `brainrot/script.py` - Modify:
`brainrot/reddit.py` - Modify: `brainrot/worker.py` - Create:
`tests/test_pipeline_registry.py`

**Interfaces:** - Consumes: existing pipeline functions. - Produces:
registry-based pipeline resolution.

### Step 1: Write failing tests

Verify: - H1 resolves by name; - H2 resolves by name; - H2b resolves by
name; - unknown pipeline names fail clearly; - worker core does not
branch on individual pipeline names.

### Step 2: Run tests

``` bash
pytest tests/test_pipeline_registry.py -q
```

Expected: FAIL.

### Step 3: Implement registry

Create a registry mapping stable pipeline names to implementations.

The worker should call:

``` python
pipeline = registry.get(job.pipeline)
result = pipeline.execute(context)
```

Do not move all existing logic at once. Wrap existing implementations
first.

### Step 4: Run tests

``` bash
pytest tests/test_pipeline_registry.py -q
```

Expected: PASS.

### Step 5: Run existing pipeline tests

``` bash
python test_pipeline.py
```

Expected: PASS.

### Step 6: Commit

``` bash
git add brainrot tests
git commit -m "refactor: register content pipelines explicitly"
```

------------------------------------------------------------------------

## Task 6: Add stage execution tracking

**Status (2026-10-21):** Implemented with migration 003, scoped stage tracking
for H1/H2/H2b, lease guards, abandoned-stage cleanup and regression tests.
Structured logging and subsequent infrastructure tasks are also implemented.

**Files:** - Create: additive migration under `migrations/` - Create:
`brainrot/application/stages.py` - Modify: pipeline execution paths -
Create: `tests/test_stage_execution.py`

**Interfaces:** - Consumes: job execution. - Produces: per-stage
execution records.

### Step 1: Write failing tests

Cover: - stage starts; - stage completes; - stage failure stores
error; - duration can be calculated; - retrying a stage creates an
identifiable attempt.

### Step 2: Run tests

``` bash
pytest tests/test_stage_execution.py -q
```

Expected: FAIL.

### Step 3: Add persistence

Create an additive stage-execution table only after checking the current
schema for a compatible existing table.

Store: - job reference; - stage; - status; - attempt; - started_at; -
completed_at; - duration; - error.

### Step 4: Implement stage context manager/service

Allow pipeline code to wrap major operations without duplicating
persistence logic.

### Step 5: Run tests

``` bash
pytest tests/test_stage_execution.py -q
```

Expected: PASS.

### Step 6: Commit

``` bash
git add migrations brainrot tests
git commit -m "feat: track pipeline stage executions"
```

------------------------------------------------------------------------

## Task 7: Add structured logging

**Status (2026-10-21):** Implemented with JSON execution events, context binding,
secret redaction and logging regression coverage.

**Files:** - Create: `brainrot/observability/logging.py` - Modify:
`brainrot/worker.py` - Modify: relevant pipeline execution boundaries -
Create: `tests/test_logging.py`

**Interfaces:** - Consumes: job/stage execution context. - Produces:
structured operational logs.

### Step 1: Write failing tests

Verify that log records can contain: - job_id; - pipeline; - stage; -
attempt; - worker_id; - event.

Verify secrets are not emitted.

### Step 2: Run tests

``` bash
pytest tests/test_logging.py -q
```

Expected: FAIL.

### Step 3: Implement structured logger

Prefer standard-library logging with structured fields rather than
introducing a logging dependency without need.

### Step 4: Instrument execution boundaries

At minimum: - claim; - start; - stage start/end; - retry; - recovery; -
completion; - failure; - publication result.

### Step 5: Run tests

``` bash
pytest tests/test_logging.py -q
```

Expected: PASS.

### Step 6: Commit

``` bash
git add brainrot tests
git commit -m "feat: add structured execution logging"
```

------------------------------------------------------------------------

## Task 8: Add metrics instrumentation

**Status (2026-10-21):** Implemented with migration 004's durable observations,
authenticated Prometheus output, bounded labels and per-process API latency.

**Files:** - Create: `brainrot/observability/metrics.py` - Modify:
`brainrot/api.py` - Modify: `brainrot/worker.py` - Create:
`tests/test_metrics.py`

**Interfaces:** - Consumes: execution events. - Produces:
Prometheus-compatible operational metrics.

### Step 1: Write failing tests

Cover counters/gauges/histograms for: - jobs processed; - jobs
completed; - jobs failed; - retries; - recovered jobs; - queue depth; -
job duration; - stage duration; - API latency.

### Step 2: Run tests

``` bash
pytest tests/test_metrics.py -q
```

Expected: FAIL.

### Step 3: Implement instrumentation

Keep metric creation centralized.

Avoid high-cardinality labels such as arbitrary URLs, full error strings
or content text.

### Step 4: Expose metrics

Add an API endpoint such as `/metrics` only if consistent with the
existing authentication/deployment model. If the deployment expects an
unauthenticated Prometheus scrape, document the security boundary
explicitly.

### Step 5: Run tests

``` bash
pytest tests/test_metrics.py -q
```

Expected: PASS.

### Step 6: Commit

``` bash
git add brainrot tests
git commit -m "feat: instrument brainrot operational metrics"
```

------------------------------------------------------------------------

## Task 9: Add operational execution details to the dashboard

**Status (2026-10-21):** Implemented with migration 005's read models,
authenticated inspection endpoints and the EN/ES execution inspector.
Desktop/mobile browser checks cover polling and connection failures.

**Files:** - Modify: `brainrot/api.py` - Modify: `web/src/api.js` -
Modify: relevant pages under `web/src/pages/` - Modify:
`web/src/App.jsx` - Modify: `web/src/style.css` - Create: frontend/API
tests where the existing project test setup supports them.

**Interfaces:** - Consumes: job/stage execution API. - Produces:
operational job inspection UI.

### Step 1: Define the read model

Expose only the data the dashboard needs: - job status; - pipeline; -
attempt; - timestamps; - current stage; - duration; - error summary; -
publication state.

Do not expose secrets or raw provider credentials.

### Step 2: Implement API endpoint

Use the existing authentication mechanism.

### Step 3: Implement dashboard view

Preserve the existing BRAINROT visual language: - cream paper; - thick
black rules; - hard offset shadows; - sticker-sheet treatment; - no
glow.

### Step 4: Verify manually

Start backend and frontend:

``` bash
uvicorn brainrot.api:app --reload --port 8000
cd web
npm run dev
```

Verify: - running jobs are visible; - completed jobs remain visible; -
failures expose useful diagnostics; - stage information is
understandable.

### Step 5: Commit

``` bash
git add brainrot web
git commit -m "feat: add operational job execution dashboard"
```

------------------------------------------------------------------------

## Task 10: Separate analytics ingestion from scheduling policy

**Status (2026-10-21):** Implemented with a normalized Performance contract,
pure pacing decisions and boundary tests. Provider analytics fetching is deferred.

**Files:** - Create: `brainrot/application/analytics.py` - Modify:
`brainrot/scheduler.py` - Create: `tests/test_analytics_policy.py`

**Interfaces:** - Consumes: normalized platform performance. - Produces:
scheduling decisions.

### Step 1: Write failing tests

Cover the existing retention policy exactly:

``` text
>= 60%  -> 12h
40–60%  -> 24h
< 40%   -> 48h
< 20%   -> drop
no data within 24h -> slow cadence
```

Test boundary values explicitly.

### Step 2: Run tests

``` bash
pytest tests/test_analytics_policy.py -q
```

Expected: FAIL.

### Step 3: Extract policy

Move decision logic into a pure application-level policy.

The scheduler must not know whether metrics came from YouTube, TikTok or
Instagram.

### Step 4: Add normalized analytics contract

Define a platform-neutral representation for: - views; - retention; -
engagement; - measurement timestamp; - platform; - content identifier.

Do not implement new provider APIs in this task unless existing adapters
already expose the necessary data.

### Step 5: Run tests

``` bash
pytest tests/test_analytics_policy.py -q
```

Expected: PASS.

### Step 6: Commit

``` bash
git add brainrot tests
git commit -m "refactor: separate analytics from scheduling policy"
```

------------------------------------------------------------------------

## Task 11: Add integration tests for the complete job lifecycle

**Status (2026-10-21):** Implemented against local PostgreSQL for completion,
retry, recovery, stages, API, metrics and publication claiming. An ambiguous
accepted upload is never automatically uploaded again.

**Files:** - Create: `tests/integration/test_job_lifecycle.py` - Create:
`tests/integration/test_publish_idempotency.py` - Modify: test fixtures
as required.

**Interfaces:** - Consumes: worker, database and pipeline contracts. -
Produces: regression coverage for the complete lifecycle.

### Step 1: Write integration tests

Cover:

``` text
pending
 -> processing
 -> stage execution
 -> completed
```

and:

``` text
pending
 -> processing
 -> transient failure
 -> retry_wait
 -> processing
 -> completed
```

and:

``` text
processing
 -> worker disappears
 -> lease expires
 -> recovery
 -> processing
```

### Step 2: Test duplicate publication

Simulate a timeout after an external publish succeeds but before local
success is persisted.

The retry must detect the idempotency record and avoid publishing the
same content twice.

### Step 3: Run tests

``` bash
pytest tests/integration -q
```

Expected: PASS.

### Step 4: Commit

``` bash
git add tests
git commit -m "test: cover end to end job lifecycle"
```

------------------------------------------------------------------------

## Task 12: Harden security and failure boundaries

**Status (2026-10-21):** Implemented with authenticated operations, strict
input validation, bounded allowlisted output and credential-redaction coverage.

**Files:** - Modify: `brainrot/api.py` - Modify: `brainrot/publish.py` -
Modify: `brainrot/observability/logging.py` - Create:
`tests/test_security_boundaries.py`

**Interfaces:** - Consumes: current API/publishing/auth behavior. -
Produces: explicit security regression coverage.

### Step 1: Write failing tests

Verify: - service-role key is never returned by API responses; -
platform credentials are not logged; - arbitrary idempotency keys cannot
bypass ownership/auth boundaries; - operational endpoints follow the
intended authentication policy.

### Step 2: Run tests

``` bash
pytest tests/test_security_boundaries.py -q
```

Expected: FAIL where behavior is missing.

### Step 3: Implement minimal fixes

Do not broaden authentication architecture unnecessarily.

### Step 4: Run tests

``` bash
pytest tests/test_security_boundaries.py -q
```

Expected: PASS.

### Step 5: Commit

``` bash
git add brainrot tests
git commit -m "fix: harden operational security boundaries"
```

------------------------------------------------------------------------

## Task 13: Full regression and operational validation

**Status (2026-10-21):** 187 pytest tests pass with local PostgreSQL; offline
FFmpeg checks, production Vite build and desktop/mobile browser checks pass.
Live Supabase row/Storage checks and rollback-only worker retry/stage/log/API/
metrics checks pass. H1's official model is provisioned and loads in OpenCV.
README, deployment and operations documentation are updated.
Real H1/H2/H2b runs await `ANTHROPIC_API_KEY` and approved Reddit credentials
for H2b. No existing user job was consumed and no real publishing was attempted.

**Files:** - Modify: `README.md` - Create: operational
documentation/runbook if useful.

**Interfaces:** - Consumes: all previous implementation work. -
Produces: validated release candidate.

### Step 1: Run Python tests

``` bash
pytest -q
```

Expected: PASS.

Also run the existing commands:

``` bash
python test_pipeline.py
python test_db.py
```

### Step 2: Run frontend checks

``` bash
cd web
npm install
npm run build
```

Expected: successful production build.

### Step 3: Validate the worker lifecycle manually

Run:

``` bash
python -m brainrot.worker
```

Create or process representative jobs and verify: - claim; - stage
tracking; - retry; - completion; - recovery; - metrics; - dashboard
state.

### Step 4: Update README

Document: - job lifecycle; - retry policy; - lease/recovery behavior; -
idempotency; - metrics endpoint; - operational troubleshooting; -
current limitations; - deferred Redis/RabbitMQ architecture.

### Step 5: Commit

``` bash
git add README.md docs
git commit -m "docs: document brainrot reliability architecture"
```

------------------------------------------------------------------------

## Task 14: Final architecture review

**Status (2026-10-21):** Reviewed worker/domain/registry/stage ownership,
publication claims, read models, security, metrics and migration boundaries.
Automated criteria pass; real provider compatibility remains unverified until
credentials are configured. Additive migration precautions and operational
rollback are documented in [operations](../../operations.md).

**Files:** - Review all changed files.

### Step 1: Verify acceptance criteria

Confirm:

-   [x] only one worker can own a live job lease;
-   [x] abandoned jobs recover;
-   [x] retries use bounded backoff;
-   [x] permanent failures become terminal;
-   [x] retries reuse persisted outputs and publication claims prevent duplicate uploads;
-   [x] stages are traceable;
-   [x] structured logs include execution context;
-   [x] metrics are available;
-   [x] dashboard exposes execution state;
-   [ ] H1 works end to end with real providers (offline coverage and model loading pass);
-   [ ] H2 works end to end with real providers (offline coverage passes);
-   [ ] H2b works end to end with real providers (offline coverage passes);
-   [x] scheduler behavior remains correct;
-   [x] new pipelines can be registered without modifying worker core;
-   [x] configured secrets are redacted from application logs and operational API responses;
-   [x] existing tests remain green.

### Step 2: Run final test suite

``` bash
pytest -q
cd web && npm run build
```

### Step 3: Review migration safety

Confirm all schema changes are additive and that rollback/recovery
procedures are documented where practical.

### Step 4: Final commit

``` bash
git add .
git commit -m "feat: complete brainrot reliability and observability increment"
```

------------------------------------------------------------------------

## Execution order summary

``` text
1. Baseline
   ↓
2. Domain contracts
   ↓
3. Persistence + leases + idempotency
   ↓
4. Retry + recovery
   ↓
5. Pipeline registry
   ↓
6. Stage execution
   ↓
7. Structured logging
   ↓
8. Metrics
   ↓
9. Dashboard
   ↓
10. Analytics + scheduling policy
   ↓
11. Integration tests
   ↓
12. Security hardening
   ↓
13. Regression + docs
   ↓
14. Final architecture review
```

## Deferred after this increment

Only after this increment is stable:

-   Redis/RabbitMQ;
-   multiple worker pools;
-   workload-specific queues;
-   horizontal scaling;
-   platform-specific optimization;
-   A/B testing;
-   thumbnail generation;
-   multi-language pipelines;
-   deeper analytics/ML optimization;
-   complete OAuth onboarding.
