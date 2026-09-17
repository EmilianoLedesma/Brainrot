-- Phase 0: initial schema for the vertical-video pipeline.
-- Single-user project. Workers connect with the service_role key, which bypasses RLS.
-- RLS is enabled with no policies on every table, so anon/authenticated clients get nothing.

create extension if not exists pgcrypto;

create type job_kind as enum ('repurpose', 'brainrot', 'reddit');
create type job_status as enum ('pending', 'running', 'done', 'failed', 'cancelled');
create type asset_status as enum ('pending', 'rendering', 'ready', 'failed');
create type publication_status as enum ('scheduled', 'uploading', 'published', 'failed');
create type platform as enum ('youtube', 'tiktok', 'instagram');

-- One row per unit of requested work. params holds the kind-specific input
-- (a YouTube URL, a topic, a subreddit filter) so adding a kind needs no migration.
create table jobs (
  id          uuid primary key default gen_random_uuid(),
  kind        job_kind not null,
  status      job_status not null default 'pending',
  params      jsonb not null default '{}'::jsonb,
  error       text,
  created_at  timestamptz not null default now(),
  started_at  timestamptz,
  finished_at timestamptz
);
create index jobs_pending_idx on jobs (status, created_at);

-- H1 only: the downloaded source video and its transcript.
create table source_videos (
  id               uuid primary key default gen_random_uuid(),
  job_id           uuid not null references jobs on delete cascade,
  youtube_url      text not null,
  youtube_id       text,
  title            text,
  duration_seconds numeric(10, 3),
  storage_path     text,
  transcript       jsonb,
  created_at       timestamptz not null default now()
);
create index source_videos_job_idx on source_videos (job_id);

-- H1 only: a candidate moment cut out of a source video.
create table clips (
  id              uuid primary key default gen_random_uuid(),
  job_id          uuid not null references jobs on delete cascade,
  source_video_id uuid not null references source_videos on delete cascade,
  start_seconds   numeric(10, 3) not null,
  end_seconds     numeric(10, 3) not null,
  title           text,
  reason          text,
  score           numeric(4, 3),
  status          asset_status not null default 'pending',
  storage_path    text,
  created_at      timestamptz not null default now(),
  constraint clips_range_valid check (end_seconds > start_seconds)
);
create index clips_job_idx on clips (job_id);

-- H2 and H2b share this table. The reddit_* columns stay null for generated stories.
create table stories (
  id             uuid primary key default gen_random_uuid(),
  job_id         uuid not null references jobs on delete cascade,
  topic          text,
  title          text,
  script         text,
  status         asset_status not null default 'pending',
  reddit_post_id text unique,
  subreddit      text,
  permalink      text,
  upvotes        integer,
  created_at     timestamptz not null default now()
);
create index stories_job_idx on stories (job_id);

-- A story renders as one or more chapters. A short story is simply chapter 1 of 1.
create table story_chapters (
  id            uuid primary key default gen_random_uuid(),
  story_id      uuid not null references stories on delete cascade,
  chapter_index integer not null,
  text          text not null,
  audio_path    text,
  video_path    text,
  status        asset_status not null default 'pending',
  created_at    timestamptz not null default now(),
  unique (story_id, chapter_index),
  constraint story_chapters_index_positive check (chapter_index >= 1)
);

-- Retention samples pulled back from the platforms. Drives pacing of later chapters.
create table chapter_metrics (
  id                 uuid primary key default gen_random_uuid(),
  chapter_id         uuid not null references story_chapters on delete cascade,
  platform           platform not null,
  views              integer,
  likes              integer,
  comments           integer,
  avg_watch_seconds  numeric(8, 3),
  retention_pct      numeric(5, 2),
  captured_at        timestamptz not null default now()
);
create index chapter_metrics_chapter_idx on chapter_metrics (chapter_id, captured_at desc);

-- Library of copyright-free loops used as H2/H2b backgrounds.
create table background_clips (
  id               uuid primary key default gen_random_uuid(),
  label            text not null,
  storage_path     text not null,
  duration_seconds numeric(10, 3),
  tags             text[] not null default '{}',
  active           boolean not null default true,
  created_at       timestamptz not null default now()
);

-- One row per (rendered asset, platform) upload attempt.
create table publications (
  id               uuid primary key default gen_random_uuid(),
  platform         platform not null,
  clip_id          uuid references clips on delete cascade,
  chapter_id       uuid references story_chapters on delete cascade,
  status           publication_status not null default 'scheduled',
  scheduled_at     timestamptz not null default now(),
  published_at     timestamptz,
  platform_post_id text,
  url              text,
  error            text,
  created_at       timestamptz not null default now(),
  -- Exactly one target: a clip (H1) or a chapter (H2/H2b), never both, never neither.
  constraint publications_one_target check ((clip_id is null) <> (chapter_id is null))
);
create index publications_due_idx on publications (status, scheduled_at);
create unique index publications_platform_post_idx
  on publications (platform, platform_post_id)
  where platform_post_id is not null;

-- Which subreddits to scan and the bar a post must clear.
create table reddit_sources_config (
  id            uuid primary key default gen_random_uuid(),
  subreddit     text not null unique,
  min_upvotes   integer not null default 1000,
  min_comments  integer not null default 50,
  max_age_hours integer not null default 168,
  enabled       boolean not null default true,
  created_at    timestamptz not null default now()
);

-- Placeholder for Phase 5. Tokens go in data; no OAuth flow is implemented yet.
create table platform_credentials (
  id         uuid primary key default gen_random_uuid(),
  platform   platform not null unique,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table jobs                  enable row level security;
alter table source_videos         enable row level security;
alter table clips                 enable row level security;
alter table stories               enable row level security;
alter table story_chapters        enable row level security;
alter table chapter_metrics       enable row level security;
alter table background_clips      enable row level security;
alter table publications          enable row level security;
alter table reddit_sources_config enable row level security;
alter table platform_credentials  enable row level security;

-- Private bucket for every generated and downloaded media file.
insert into storage.buckets (id, name, public)
values ('media', 'media', false)
on conflict (id) do nothing;
