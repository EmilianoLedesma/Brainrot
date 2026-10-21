-- Per-stage records for each leased job attempt. Apply after 002_job_execution.sql.
-- A scope distinguishes repeated work such as rendering separate chapters/clips.
create table stage_executions (
  id               uuid primary key default gen_random_uuid(),
  job_id           uuid not null references jobs on delete cascade,
  stage            text not null check (length(btrim(stage)) > 0),
  scope            text not null default '',
  attempt          integer not null check (attempt > 0),
  worker_id        text not null,
  status           text not null default 'running'
                   check (status in ('running', 'done', 'failed', 'abandoned')),
  started_at       timestamptz not null default clock_timestamp(),
  completed_at     timestamptz,
  duration_seconds numeric generated always as
                   (extract(epoch from (completed_at - started_at))) stored,
  error            text,
  unique (job_id, attempt, stage, scope),
  check ((status = 'running') = (completed_at is null)),
  check (completed_at is null or completed_at >= started_at)
);
create index stage_executions_job_idx on stage_executions (job_id, attempt, started_at);
alter table stage_executions enable row level security;
grant select, insert, update, delete on stage_executions to service_role;

-- Lock the job before inserting so a concurrent recovery cannot miss the new
-- stage. An expired or superseded lease returns NULL without starting work.
create function start_stage(
  p_job uuid, p_worker text, p_attempt integer, p_stage text, p_scope text default '')
returns uuid
language sql
as $$
  with owned_job as (
    select id from jobs
     where id = p_job and status = 'running' and lease_owner = p_worker
       and attempts = p_attempt and lease_expires_at > clock_timestamp()
     for update
  )
  insert into stage_executions (job_id, worker_id, attempt, stage, scope)
    select id, p_worker, p_attempt, p_stage, p_scope from owned_job
  returning id;
$$;

create function finish_stage(p_execution uuid, p_worker text, p_status text, p_error text default null)
returns boolean
language sql
as $$
  with owned_job as (
    select j.id from jobs j join stage_executions s on s.job_id = j.id
     where s.id = p_execution and s.worker_id = p_worker
       and j.status = 'running' and j.lease_owner = p_worker
       and j.attempts = s.attempt and j.lease_expires_at > clock_timestamp()
     for update of j
  ), finished as (
    update stage_executions s
       set status = p_status,
           completed_at = greatest(clock_timestamp(), s.started_at),
           error = case when p_status = 'failed' then left(p_error, 4000) end
      from owned_job j
     where s.id = p_execution and s.job_id = j.id and s.status = 'running'
       and p_status in ('done', 'failed')
    returning 1
  )
  select exists (select 1 from finished);
$$;

-- Recovery, failure and completion all leave the running job state through the
-- existing RPCs. Close any unfinished stages in that same transaction, even if
-- a worker crashed or could not persist its stage outcome.
create function abandon_job_stages()
returns trigger
language plpgsql
as $$
begin
  update stage_executions
     set status = 'abandoned',
         completed_at = greatest(clock_timestamp(), started_at),
         error = left(coalesce(new.error, 'job attempt ended before stage outcome was recorded'), 4000)
   where job_id = old.id and attempt = old.attempts
     and worker_id = old.lease_owner and status = 'running';
  return new;
end;
$$;

create trigger jobs_abandon_stages
after update of status, lease_owner on jobs
for each row
when (old.status = 'running' and
      (new.status <> 'running' or new.lease_owner is distinct from old.lease_owner))
execute function abandon_job_stages();

revoke execute on function start_stage(uuid, text, integer, text, text) from public, anon, authenticated;
revoke execute on function finish_stage(uuid, text, text, text) from public, anon, authenticated;
revoke execute on function abandon_job_stages() from public, anon, authenticated;
grant execute on function start_stage(uuid, text, integer, text, text) to service_role;
grant execute on function finish_stage(uuid, text, text, text) to service_role;
