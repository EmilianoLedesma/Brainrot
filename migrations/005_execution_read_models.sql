-- Server-only read models; the browser continues to use the API key gate.
create function list_job_executions(p_limit integer default 50)
returns setof jsonb language sql stable as $$
  select to_jsonb(j) || jsonb_build_object(
    'current_stage', case when j.status = 'running' then (
      select jsonb_build_object('stage',s.stage,'scope',s.scope,'started_at',s.started_at)
      from stage_executions s where s.job_id=j.id and s.attempt=j.attempts and s.status='running'
      order by s.started_at desc limit 1) end,
    'duration_seconds', case when j.started_at is not null then
      greatest(0,extract(epoch from (
        case when j.status='running' then now() else coalesce(j.finished_at,
          (select max(completed_at) from stage_executions s where s.job_id=j.id and s.attempt=j.attempts))
        end - j.started_at))) end)
  from jobs j order by created_at desc,id limit greatest(1,least(p_limit,200));
$$;

create function job_execution(p_job uuid)
returns jsonb language sql stable as $$
  select jsonb_build_object(
    'job',to_jsonb(j),
    'stages',coalesce((select jsonb_agg(to_jsonb(s) order by s.attempt,s.started_at,s.id)
      from stage_executions s where s.job_id=j.id),'[]'::jsonb),
    'publications',coalesce((select jsonb_agg(to_jsonb(p) order by p.scheduled_at,p.platform) from (
      select p.id,p.platform,p.status,p.scheduled_at,p.published_at,p.error
      from publications p left join clips c on c.id=p.clip_id
      left join story_chapters ch on ch.id=p.chapter_id left join stories st on st.id=ch.story_id
      where c.job_id=j.id or st.job_id=j.id
    ) p),'[]'::jsonb))
  from jobs j where j.id=p_job;
$$;
revoke execute on function list_job_executions(integer) from public,anon,authenticated;
revoke execute on function job_execution(uuid) from public,anon,authenticated;
grant execute on function list_job_executions(integer) to service_role;
grant execute on function job_execution(uuid) to service_role;
