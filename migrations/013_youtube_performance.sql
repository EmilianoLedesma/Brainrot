alter table public.publications add column analytics jsonb not null default '{}'::jsonb;
alter table public.publications add column analytics_checked_at timestamptz;
notify pgrst, 'reload schema';
