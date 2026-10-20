-- Trajectory: timetable data for the course planner. Run after 004_faculties.sql.
-- Safe to run more than once.
--
-- One row per course, academic year and term. A course offered in Fall and again in
-- Winter has two rows. Sections hold the meeting times used to find clashes.

create table if not exists offerings (
  course_id     text not null references courses(id) on delete cascade,
  academic_year text not null,          -- '2026-2027'
  term          text not null,          -- 'F' = Fall, 'S' = Winter, 'Y' = full year
  sections      jsonb not null,         -- [{"name": "LEC0101", "type": "LEC", "times": [{"day": 1, "start": 600, "end": 660}]}]
  updated_at    timestamptz default now(),
  primary key (course_id, academic_year, term)
);

create index if not exists offerings_year_idx on offerings (academic_year);

-- Each loader run is logged, so a sudden drop in courses can be spotted.
create table if not exists timetable_runs (
  id          serial primary key,
  source      text not null,            -- 'ARTSC', 'APSC', 'ERIN', 'SCAR'
  academic_year text not null,
  courses     int not null,
  ran_at      timestamptz default now()
);

alter table offerings      enable row level security;
alter table timetable_runs enable row level security;
