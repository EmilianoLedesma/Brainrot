-- Storage objects must be deleted through the Storage API, never by deleting
-- storage.objects rows. Keep a durable cleanup request across the DB/HTTP boundary.
create table media_cleanup (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null, -- deliberately survives deletion of its parent job
  storage_path text not null unique check (length(btrim(storage_path)) > 0),
  retry_at timestamptz not null default clock_timestamp(),
  settle_until timestamptz not null default clock_timestamp()
);
alter table media_cleanup enable row level security;
grant select, insert, update, delete on media_cleanup to service_role;
create index media_cleanup_retry_idx on media_cleanup(retry_at);

create function queue_media_cleanup(p_job uuid, p_paths text[], p_settle_until timestamptz default clock_timestamp())
returns void language sql as $$
  insert into media_cleanup(job_id, storage_path, settle_until)
    select p_job, path, p_settle_until from (
      select distinct unnest(p_paths) as path
    ) paths where path is not null and length(btrim(path)) > 0
  on conflict(storage_path) do update set
    id = gen_random_uuid(), job_id = excluded.job_id, retry_at = clock_timestamp(),
    settle_until = greatest(media_cleanup.settle_until, excluded.settle_until);
$$;

create function pending_media_cleanup(p_job uuid default null, p_limit integer default 500)
returns table(id uuid, storage_path text, is_referenced boolean) language sql stable as $$
  select m.id, m.storage_path,
    exists(select 1 from background_clips b where b.storage_path=m.storage_path)
    or exists(select 1 from source_videos v where v.storage_path=m.storage_path)
    or exists(select 1 from clips c where c.storage_path=m.storage_path)
    or exists(select 1 from story_chapters c where c.audio_path=m.storage_path or c.video_path=m.storage_path)
    as is_referenced
  from media_cleanup m
  where (p_job is null and m.retry_at <= statement_timestamp()) or m.job_id=p_job
  order by m.retry_at, m.id limit greatest(1,least(p_limit,500));
$$;

create function finish_media_cleanup(p_ids uuid[], p_success boolean)
returns void language plpgsql as $$
begin
  if p_success then
    delete from media_cleanup where id=any(p_ids) and settle_until <= clock_timestamp();
    -- Recheck a running upload after its old lease expires. A crashed worker
    -- might finish sending an object after the first Storage deletion succeeds.
    update media_cleanup set retry_at=settle_until where id=any(p_ids);
  else
    update media_cleanup set retry_at=clock_timestamp()+interval '30 seconds' where id=any(p_ids);
  end if;
end;
$$;

create or replace function delete_job(p_job uuid)
returns text language plpgsql as $$
declare
  job_row jobs%rowtype;
  paths text[];
  settle timestamptz := clock_timestamp();
begin
  select * into job_row from jobs where id=p_job for update;
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

  if job_row.status='running' and exists(
    select 1 from stage_executions where job_id=p_job and stage='upload' and status='running'
  ) then
    settle := greatest(clock_timestamp()+interval '2 minutes',
                       coalesce(job_row.lease_expires_at,clock_timestamp())+interval '1 minute');
  end if;

  -- Include deterministic destinations even when an upload has not yet saved
  -- its path to a row (or a previous upload succeeded but its DB update failed).
  select array_agg(distinct path) into paths from (
    select storage_path as path from source_videos where job_id=p_job
    union all select storage_path from clips where job_id=p_job
    union all select 'clips/'||id||'.mp4' from clips where job_id=p_job
    union all select ch.audio_path from story_chapters ch join stories st on st.id=ch.story_id where st.job_id=p_job
    union all select ch.video_path from story_chapters ch join stories st on st.id=ch.story_id where st.job_id=p_job
    union all
      select 'stories/'||st.id||'/'||
        case when ch.chapter_index<10 then '0'||ch.chapter_index::text else ch.chapter_index::text end||ext
      from story_chapters ch join stories st on st.id=ch.story_id
      cross join (values ('.mp3'),('.mp4')) extensions(ext) where st.job_id=p_job
  ) assets where path is not null;
  perform queue_media_cleanup(p_job,coalesce(paths,array[]::text[]),settle);

  if job_row.status='running' then
    update jobs set status='cancelled', lease_owner=null, lease_expires_at=null,
      finished_at=clock_timestamp(), error='Job deleted by user' where id=p_job;
  end if;
  -- Cascades stories, chapters, source videos, clips, publications, metrics,
  -- transcripts, cached selections, and all stage/attempt history atomically.
  delete from jobs where id=p_job;
  return 'deleted';
end;
$$;

revoke execute on function queue_media_cleanup(uuid,text[],timestamptz) from public,anon,authenticated;
revoke execute on function pending_media_cleanup(uuid,integer) from public,anon,authenticated;
revoke execute on function finish_media_cleanup(uuid[],boolean) from public,anon,authenticated;
grant execute on function queue_media_cleanup(uuid,text[],timestamptz) to service_role;
grant execute on function pending_media_cleanup(uuid,integer) to service_role;
grant execute on function finish_media_cleanup(uuid[],boolean) to service_role;
notify pgrst, 'reload schema';
