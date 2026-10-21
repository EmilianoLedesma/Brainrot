-- Explicit retries reuse the same job and all saved assets/stage history.
-- Serialize with worker claims, deletion, and other retry requests.
create function retry_job(p_job uuid)
returns text language plpgsql as $$
declare
  job_state job_status;
begin
  select status into job_state from jobs where id=p_job for update;
  if not found then return 'missing'; end if;
  if job_state='pending' then return 'already_pending'; end if;
  if job_state<>'failed' then return 'not_failed'; end if;

  update jobs set status='pending', run_after=clock_timestamp(),
    started_at=null, finished_at=null, error=null, error_kind=null,
    lease_owner=null, lease_expires_at=null,
    max_attempts=greatest(max_attempts,attempts+3)
    where id=p_job;
  return 'queued';
end;
$$;
revoke execute on function retry_job(uuid) from public,anon,authenticated;
grant execute on function retry_job(uuid) to service_role;
