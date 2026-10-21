-- Lock the job before checking its state so claim_job cannot race deletion.
-- Publication rows are locked too: a scheduled upload cannot be taken while
-- its parent job is being deleted. Media objects and external posts are retained.
create function delete_job(p_job uuid)
returns text language plpgsql as $$
declare
  job_state job_status;
begin
  select status into job_state from jobs where id=p_job for update;
  if not found then return 'missing'; end if;

  perform p.id from publications p
    left join clips c on c.id=p.clip_id
    left join story_chapters ch on ch.id=p.chapter_id
    left join stories st on st.id=ch.story_id
    where c.job_id=p_job or st.job_id=p_job
    order by p.id for update of p;
  if exists (
    select 1 from publications p
    left join clips c on c.id=p.clip_id
    left join story_chapters ch on ch.id=p.chapter_id
    left join stories st on st.id=ch.story_id
    where (c.job_id=p_job or st.job_id=p_job) and p.status='uploading'
  ) then return 'uploading'; end if;

  -- Revoke the lease and close running stages before cascading the records.
  -- Any in-flight operation may finish, but its outcome and later stages are fenced.
  if job_state='running' then
    update jobs set status='cancelled', lease_owner=null, lease_expires_at=null,
      finished_at=clock_timestamp(), error='Job deleted by user'
      where id=p_job;
  end if;
  delete from jobs where id=p_job;
  return 'deleted';
end;
$$;
revoke execute on function delete_job(uuid) from public,anon,authenticated;
grant execute on function delete_job(uuid) to service_role;
