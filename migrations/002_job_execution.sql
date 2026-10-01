-- Job execution metadata: leases, attempts, retry scheduling, idempotency.
-- Additive only; apply after 001_init.sql.
--
-- A job waiting to retry is `pending` with run_after in the future, so the
-- job_status enum does not change. Every state change a worker makes goes
-- through the functions below, which check that the worker still holds the
-- lease. Workers call them with the service_role key via PostgREST rpc.

alter table jobs
  add column attempts         integer not null default 0,
  add column max_attempts     integer not null default 3,
  add column run_after        timestamptz not null default now(),
  add column lease_owner      text,
  add column lease_expires_at timestamptz,
  add column error_kind       text,
  add column idempotency_key  text,
  add constraint jobs_attempts_nonnegative check (attempts >= 0),
  add constraint jobs_max_attempts_positive check (max_attempts >= 1),
  add constraint jobs_error_kind_valid
    check (error_kind in ('transient', 'permanent', 'lease_expired'));

-- Non-partial unique indexes throughout, so PostgREST upserts can name them in
-- on_conflict. NULLs never collide, so rows without a key are unconstrained.
create unique index jobs_idempotency_key_idx on jobs (idempotency_key);
create index jobs_claimable_idx on jobs (run_after, created_at) where status = 'pending';
create index jobs_lease_idx on jobs (lease_expires_at) where status = 'running';

-- One story (H2/H2b) or one source video (H1) per job, so a retried job finds
-- the work its earlier attempt already did instead of starting over.
create unique index stories_job_unique_idx on stories (job_id);
create unique index source_videos_job_unique_idx on source_videos (job_id);

-- One publication per target per platform, so re-planning cannot double-post.
create unique index publications_chapter_platform_idx on publications (chapter_id, platform);
create unique index publications_clip_platform_idx on publications (clip_id, platform);


-- Take the oldest claimable job and lease it to p_worker. SKIP LOCKED means two
-- workers claiming at once each get a different job (or nothing), never the same one.
create function claim_job(p_worker text, p_lease_seconds integer default 600)
returns setof jobs
language sql
as $$
  update jobs
     set status           = 'running',
         attempts         = attempts + 1,
         lease_owner      = p_worker,
         lease_expires_at = now() + make_interval(secs => p_lease_seconds),
         started_at       = now(),
         finished_at      = null
   where id = (
         select id
           from jobs
          where status = 'pending'
            and run_after <= now()
          order by run_after, created_at
          limit 1
          for update skip locked)
  returning *;
$$;

-- Extend a lease. False means the worker no longer owns the job and should stop.
create function renew_lease(p_job uuid, p_worker text, p_lease_seconds integer default 600)
returns boolean
language sql
as $$
  with renewed as (
    update jobs
       set lease_expires_at = now() + make_interval(secs => p_lease_seconds)
     where id = p_job and status = 'running' and lease_owner = p_worker
    returning 1)
  select exists (select 1 from renewed);
$$;

-- Mark the job done. False means the lease was lost and the outcome is not recorded.
create function complete_job(p_job uuid, p_worker text)
returns boolean
language sql
as $$
  with completed as (
    update jobs
       set status           = 'done',
           finished_at      = now(),
           error            = null,
           error_kind       = null,
           lease_owner      = null,
           lease_expires_at = null
     where id = p_job and status = 'running' and lease_owner = p_worker
    returning 1)
  select exists (select 1 from completed);
$$;

-- Record a failed attempt. With p_retry_at the job goes back to pending until
-- then; without it the job is failed for good. Whether to retry is decided by
-- the worker's retry policy, not here. Returns the new status, or null if the
-- lease was lost.
create function fail_job(
  p_job        uuid,
  p_worker     text,
  p_error      text,
  p_error_kind text,
  p_retry_at   timestamptz default null)
returns job_status
language sql
as $$
  update jobs
     set status           = case when p_retry_at is null then 'failed'::job_status
                                 else 'pending'::job_status end,
         run_after        = coalesce(p_retry_at, run_after),
         finished_at      = case when p_retry_at is null then now() end,
         error            = left(p_error, 4000),
         error_kind       = p_error_kind,
         lease_owner      = null,
         lease_expires_at = null
   where id = p_job and status = 'running' and lease_owner = p_worker
  returning status;
$$;

-- Return jobs whose worker stopped renewing to the queue, or fail them if they
-- have used every attempt. A running row with no lease at all was left by the
-- worker that predates this migration, and counts as abandoned too.
create function recover_expired_jobs()
returns table (id uuid, status job_status)
language sql
as $$
  update jobs j
     set status           = case when j.attempts >= j.max_attempts then 'failed'::job_status
                                 else 'pending'::job_status end,
         finished_at      = case when j.attempts >= j.max_attempts then now() end,
         run_after        = now(),
         error            = 'lease expired: worker ' || coalesce(j.lease_owner, 'unknown')
                            || ' stopped renewing',
         error_kind       = 'lease_expired',
         lease_owner      = null,
         lease_expires_at = null
   where j.status = 'running'
     and (j.lease_expires_at is null or j.lease_expires_at < now())
  returning j.id, j.status;
$$;

-- Supabase grants EXECUTE on new public functions to anon and authenticated.
-- These are for workers only.
revoke execute on function claim_job(text, integer)                         from public, anon, authenticated;
revoke execute on function renew_lease(uuid, text, integer)                 from public, anon, authenticated;
revoke execute on function complete_job(uuid, text)                         from public, anon, authenticated;
revoke execute on function fail_job(uuid, text, text, text, timestamptz)    from public, anon, authenticated;
revoke execute on function recover_expired_jobs()                           from public, anon, authenticated;
grant  execute on function claim_job(text, integer)                         to service_role;
grant  execute on function renew_lease(uuid, text, integer)                 to service_role;
grant  execute on function complete_job(uuid, text)                         to service_role;
grant  execute on function fail_job(uuid, text, text, text, timestamptz)    to service_role;
grant  execute on function recover_expired_jobs()                           to service_role;
