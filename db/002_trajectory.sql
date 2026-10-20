-- Trajectory: everything after 001_jobs.sql.
-- Safe to run more than once. Run it in the Supabase SQL editor.

-- Part 1: job columns the loaders already use ---------------------------

alter table postings add column if not exists country                text[];       -- 'US', 'CA', 'other'
alter table postings add column if not exists description_source     text;         -- 'greenhouse', 'lever', 'ashby'
alter table postings add column if not exists description_checked_at timestamptz;
alter table postings add column if not exists embed_hash             text;         -- md5 of the text that was embedded

create index if not exists postings_active_idx on postings (active);
create index if not exists postings_embedding_idx
  on postings using hnsw (embedding vector_cosine_ops);

-- Part 2: course tables (any school) -----------------------------------

create table if not exists schools (
  id          text primary key,   -- 'uoft', later 'waterloo'
  name        text not null,
  credit_unit text                -- 'FCE' at UofT, 'units' elsewhere
);

create table if not exists courses (
  id            text primary key, -- 'uoft:CSC207H1'
  school_id     text not null references schools(id),
  code          text not null,
  title         text not null,
  description   text,
  year_level    int,              -- 1 to 4, from the course number
  credits       numeric,          -- 0.5 or 1.0 at UofT
  terms_offered text[],           -- 'fall', 'winter', 'summer' (null when the calendar does not say)
  calendar_year text,             -- '2026-2027'
  url           text,             -- the official course page
  prereq_text   text,             -- the calendar's own words, shown to students
  prereq_tree   jsonb,            -- the same rule in the shared and/or format
  exclusions    text,
  recommended   text,
  skills        text[],
  embedding     vector(384),
  embed_hash    text,
  active        boolean default true,
  updated_at    timestamptz default now(),
  -- Keyword search. "CSC207H1" is also stored as "CSC 207 H1" so "CSC 207" finds it.
  fts tsvector generated always as (
    setweight(to_tsvector('english', code || ' ' || regexp_replace(code, '^([A-Z]+)([0-9]+)(.*)$', '\1 \2 \3')), 'A') ||
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B')
  ) stored
);

create table if not exists prereqs (
  course_id    text references courses(id) on delete cascade,
  requires     text,              -- a course id, same school (it may not be loaded)
  option_group int                -- same group = any one of them (OR)
);

create index if not exists courses_school_idx   on courses (school_id) where active;
create index if not exists courses_fts_idx      on courses using gin (fts);
create index if not exists courses_skills_idx   on courses using gin (skills);
create index if not exists courses_embedding_idx on courses using hnsw (embedding vector_cosine_ops);
create index if not exists prereqs_course_idx   on prereqs (course_id);
create index if not exists prereqs_requires_idx on prereqs (requires);

-- Usage: counts only. No resume text, no IP addresses.
create table if not exists usage_daily (
  day   date not null default current_date,
  event text not null,            -- 'match', 'course_search'
  count int  not null default 0,
  primary key (day, event)
);

-- Block Supabase's public API. The loaders and API connect directly.
alter table schools     enable row level security;
alter table courses     enable row level security;
alter table prereqs     enable row level security;
alter table usage_daily enable row level security;
