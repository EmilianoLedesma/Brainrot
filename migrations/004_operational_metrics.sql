-- Durable observations shared by API and worker processes. Counters begin here;
-- old attempts cannot be reconstructed reliably and are not backfilled.
create table operational_events (
  id bigint generated always as identity primary key,
  event text not null check (event in
    ('processed','completed','failed','retried','recovered','job_duration',
     'stage_duration','publication_published','publication_failed')),
  pipeline job_kind,
  stage text not null default '',
  platform platform,
  duration_seconds double precision check (duration_seconds >= 0),
  observed_at timestamptz not null default clock_timestamp()
);
create index operational_events_groups_idx on operational_events(event,pipeline,stage,platform);
alter table operational_events enable row level security;
grant select, insert on operational_events to service_role;
grant usage on sequence operational_events_id_seq to service_role;

create function record_job_metrics() returns trigger language plpgsql as $$
begin
  if new.status = 'running' and old.status <> 'running' then
    insert into operational_events(event,pipeline) values ('processed',new.kind);
  elsif old.status = 'running' and new.status <> 'running' then
    insert into operational_events(event,pipeline,duration_seconds)
      values ('job_duration',new.kind,greatest(0,extract(epoch from (clock_timestamp()-old.started_at))));
    if new.status = 'done' then
      insert into operational_events(event,pipeline) values ('completed',new.kind);
    elsif new.status = 'failed' then
      insert into operational_events(event,pipeline) values ('failed',new.kind);
    elsif new.status = 'pending' and new.error_kind is distinct from 'lease_expired' then
      insert into operational_events(event,pipeline) values ('retried',new.kind);
    end if;
    if new.error_kind = 'lease_expired' then
      insert into operational_events(event,pipeline) values ('recovered',new.kind);
    end if;
  end if;
  return new;
end;
$$;
create trigger jobs_record_metrics after update of status on jobs
for each row when (old.status is distinct from new.status) execute function record_job_metrics();

create function record_stage_metrics() returns trigger language plpgsql as $$
begin
  insert into operational_events(event,pipeline,stage,duration_seconds)
    select 'stage_duration',kind,
      case when new.stage in ('script','chaptering','background','tts','render','upload',
                              'schedule','download','transcribe','selection')
           then new.stage else 'other' end,
      new.duration_seconds from jobs where id = new.job_id;
  return new;
end;
$$;
create trigger stages_record_metrics after update of status on stage_executions
for each row when (old.status = 'running' and new.status <> 'running')
execute function record_stage_metrics();

create function record_publication_metrics() returns trigger language plpgsql as $$
begin
  insert into operational_events(event,platform)
    values (case when new.status = 'published' then 'publication_published' else 'publication_failed' end,
            new.platform);
  return new;
end;
$$;
create trigger publications_record_metrics after update of status on publications
for each row when (old.status = 'uploading' and new.status in ('published','failed'))
execute function record_publication_metrics();

create function operational_metrics() returns jsonb language sql stable as $$
  with counters as (
    select event,pipeline,platform,count(*) as value
      from operational_events where duration_seconds is null group by event,pipeline,platform
  ), histograms as (
    select event,pipeline,stage,count(*) as count,coalesce(sum(duration_seconds),0) as sum,
      jsonb_build_array(
        count(*) filter(where duration_seconds <= 0.1),
        count(*) filter(where duration_seconds <= 1),
        count(*) filter(where duration_seconds <= 5),
        count(*) filter(where duration_seconds <= 30),
        count(*) filter(where duration_seconds <= 60),
        count(*) filter(where duration_seconds <= 300),
        count(*) filter(where duration_seconds <= 1800),
        count(*)) as buckets
    from operational_events where duration_seconds is not null group by event,pipeline,stage
  ), states as (
    select kind as pipeline,status as state,count(*) as value from jobs group by kind,status
  ), ready as (
    select kind as pipeline,count(*) as value from jobs
      where status = 'pending' and run_after <= now() group by kind
  )
  select jsonb_build_object(
    'counters',coalesce((select jsonb_agg(to_jsonb(c)) from counters c),'[]'::jsonb),
    'histograms',coalesce((select jsonb_agg(to_jsonb(h)) from histograms h),'[]'::jsonb),
    'states',coalesce((select jsonb_agg(to_jsonb(s)) from states s),'[]'::jsonb),
    'ready',coalesce((select jsonb_agg(to_jsonb(r)) from ready r),'[]'::jsonb));
$$;

revoke execute on function record_job_metrics() from public,anon,authenticated;
revoke execute on function record_stage_metrics() from public,anon,authenticated;
revoke execute on function record_publication_metrics() from public,anon,authenticated;
revoke execute on function operational_metrics() from public,anon,authenticated;
grant execute on function operational_metrics() to service_role;
