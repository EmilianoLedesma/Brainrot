-- Persist the exact title, description, tags and visibility chosen before upload.
alter table public.publications add column if not exists metadata jsonb not null default '{}'::jsonb;
notify pgrst, 'reload schema';
