-- One imported background per relative path, including concurrent API hosts.
create or replace function public.activate_library_background(p_path text, p_label text, p_duration double precision, p_provider text)
returns uuid language plpgsql as $$
declare background_id uuid;
begin
  if p_path not like 'backgrounds/%' or p_path like '%..%' or length(p_path)>512 or p_provider not in ('nasa','pexels') then
    raise exception 'invalid background';
  end if;
  perform pg_advisory_xact_lock(hashtextextended('library:'||p_path,0));
  select id into background_id from public.background_clips where storage_path=p_path order by created_at limit 1;
  if background_id is null then
    insert into public.background_clips(storage_path,label,duration_seconds,tags,active)
    values(p_path,p_label,p_duration,array[p_provider],true) returning id into background_id;
  else
    update public.background_clips set active=true where id=background_id;
  end if;
  return background_id;
end;
$$;
revoke execute on function public.activate_library_background(text,text,double precision,text) from public,anon,authenticated;
grant execute on function public.activate_library_background(text,text,double precision,text) to service_role;
notify pgrst, 'reload schema';
