-- Independent local media folders must not consume one shared queue concurrently.
create table public.local_media_host (
  singleton boolean primary key default true check(singleton),
  host_key text not null,
  expires_at timestamptz not null
);
alter table public.local_media_host enable row level security;
grant all on public.local_media_host to service_role;

create function public.acquire_local_media_host(p_host text) returns boolean language plpgsql as $$
declare current_host public.local_media_host;
begin
  if p_host is null or length(p_host) <> 64 then raise exception 'invalid host'; end if;
  insert into public.local_media_host(singleton,host_key,expires_at)
  values(true,p_host,now()+interval '2 minutes') on conflict do nothing;
  select * into current_host from public.local_media_host where singleton for update;
  if current_host.host_key <> p_host then
    if current_host.expires_at > now() or
       exists(select 1 from public.jobs where status='running' and lease_expires_at>now()) or
       exists(select 1 from public.publications where status='uploading') then
      return false;
    end if;
  end if;
  update public.local_media_host set host_key=p_host,expires_at=now()+interval '2 minutes' where singleton;
  return true;
end;
$$;

create function public.claim_job_on_local_host(p_worker text,p_host text,p_lease_seconds integer default 600)
returns setof public.jobs language plpgsql as $$
declare current_host public.local_media_host;
begin
  select * into current_host from public.local_media_host where singleton for update;
  if current_host.host_key is distinct from p_host or current_host.expires_at<=now() then return; end if;
  return query select * from public.claim_job(p_worker,p_lease_seconds);
end;
$$;

revoke execute on function public.acquire_local_media_host(text) from public,anon,authenticated;
revoke execute on function public.claim_job_on_local_host(text,text,integer) from public,anon,authenticated;
grant execute on function public.acquire_local_media_host(text) to service_role;
grant execute on function public.claim_job_on_local_host(text,text,integer) to service_role;
notify pgrst, 'reload schema';
