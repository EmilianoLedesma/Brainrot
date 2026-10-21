-- A background is chosen once per story. A global, monotonic use order makes
-- the active pool cycle fairly across workers and survives process restarts.
alter table background_clips
  add column rotation_order integer not null default 0 check (rotation_order >= 0),
  add column last_used_order bigint;
create sequence background_rotation_sequence;
grant usage on sequence background_rotation_sequence to service_role;
grant select, update on background_clips, stories to service_role;
create index background_clips_rotation_idx on background_clips
  (last_used_order nulls first, rotation_order, created_at, id) where active;

alter table stories add column background_clip_id uuid references background_clips(id);

-- Preserve the previous choice when upgrading a library that had one active
-- background, for stories whose chapters already began rendering.
update stories set background_clip_id=(select id from background_clips where active limit 1)
where (select count(*) from background_clips where active)=1
  and exists(select 1 from story_chapters where story_id=stories.id);

create function assign_story_background(p_story uuid)
returns text language plpgsql as $$
declare
  saved_background uuid;
  selected_background background_clips%rowtype;
begin
  -- Serialize retries of one story before touching the shared rotation.
  select background_clip_id into saved_background from stories where id=p_story for update;
  if not found then return null; end if;
  if saved_background is not null then
    return (select storage_path from background_clips where id=saved_background);
  end if;

  -- Without this lock, concurrent workers could select the same least-used row.
  perform pg_advisory_xact_lock(518247393);
  select * into selected_background from background_clips where active
    order by last_used_order nulls first, rotation_order, created_at, id limit 1 for update;
  if not found then return null; end if;
  update background_clips set last_used_order=nextval('background_rotation_sequence')
    where id=selected_background.id;
  update stories set background_clip_id=selected_background.id where id=p_story;
  return selected_background.storage_path;
end;
$$;
revoke execute on function assign_story_background(uuid) from public,anon,authenticated;
grant execute on function assign_story_background(uuid) to service_role;
notify pgrst, 'reload schema';
