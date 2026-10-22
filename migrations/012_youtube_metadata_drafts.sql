-- Reusable AI drafts are separate from upload claims and reviewed metadata.
create table public.youtube_metadata_drafts (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid unique references public.story_chapters on delete cascade,
  clip_id uuid unique references public.clips on delete cascade,
  fingerprint text not null,
  metadata jsonb not null,
  created_at timestamptz not null default now(),
  constraint youtube_metadata_one_target check (num_nonnulls(chapter_id,clip_id)=1)
);
alter table public.youtube_metadata_drafts enable row level security;
grant all on public.youtube_metadata_drafts to service_role;
notify pgrst, 'reload schema';
