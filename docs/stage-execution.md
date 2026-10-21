# Stage execution

Apply `migrations/003_stage_execution.sql` after migrations 001 and 002 before
running the worker from this version. It adds `stage_executions`, two stage RPCs
and a trigger that closes unfinished records when a job attempt ends. Existing
jobs and media keep their current schema and behavior.

The registry adapters bind a `PipelineContext` while executing each handler.
Major operations use `brainrot.application.stages.stage()` to record their
start and outcome:

| Pipeline | Stages |
|---|---|
| H2 / H2b | script, chaptering, background, tts, render, upload, schedule |
| H1 | download, transcribe, selection, render, upload, schedule |

TTS includes word timings. `schedule` queues publications; platform uploads
still happen separately through the publisher.

Each record stores `job_id`, `stage`, `scope`, job `attempt`, `worker_id`,
`status`, `started_at`, `completed_at`, `duration_seconds` and `error`.
Chapter scopes are `chapter:1`, `chapter:2`, etc.; H1 uses the clip id.
The unique key is `(job_id, attempt, stage, scope)`. Duration is calculated in
Postgres from the recorded timestamps.

## Outcomes and retries

- `running`: the operation has started and has no outcome yet.
- `done`: the operation and its persisted output completed successfully.
- `failed`: the operation raised an error. The original error still reaches
  the worker's retry policy.
- `abandoned`: the job attempt ended before the stage outcome was saved.

A retry creates new records with the new job attempt. Earlier records remain
available. Operations skipped because their outputs already exist do not create
new stage records. Chaptering still runs because it calculates the deterministic
chapter list for every story attempt; H1 downloads the source again because
workers have no persistent local files.

Stage writes require the matching current attempt, worker and unexpired lease.
The SQL functions lock the job row before writing a stage so recovery cannot
leave a newly inserted stage behind. A lease loss stops execution at a stage
boundary; the worker leaves completion/failure to recovery. This does not cancel
an external call or renderer that is already executing.

The job-state trigger closes unfinished stages in the same transaction as job
retry, failure, completion or lease recovery. An outage while recording a stage
error preserves the original provider error classification; the job-state
transition closes the unfinished stage later.

## Inspection and access

For an operator using the SQL editor:

```sql
select stage, scope, attempt, worker_id, status,
       started_at, completed_at, duration_seconds, error
from stage_executions
where job_id = '<job UUID>'
order by attempt, started_at;
```

RLS is enabled with no browser policies. Stage RPCs are executable by
`service_role` only. Errors remain server-side; stage read endpoints and
dashboard displays are later tasks in the plan.

Direct calls to the legacy pipeline functions have no leased context and do no
tracking I/O. New worker pipelines should bind the execution context and wrap
their major operations, following the adapters in `brainrot/pipelines.py`.
