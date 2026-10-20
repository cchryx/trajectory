-- Trajectory: split courses by campus. Run after 002_trajectory.sql.
-- Safe to run more than once.

create table if not exists campuses (
  id         text primary key,      -- 'uoft-stg'
  school_id  text not null references schools(id),
  name       text not null,         -- 'St. George'
  calendar   text                   -- 'Faculty of Arts & Science'
);

alter table courses add column if not exists campus_id text references campuses(id);
create index if not exists courses_campus_idx on courses (campus_id) where active;

alter table campuses enable row level security;
