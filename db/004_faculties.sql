-- Trajectory: faculties and breadth requirements. Run after 003_campuses.sql.
-- Safe to run more than once.
--
-- School > campus > faculty. Each faculty has its own course calendar.
-- UofT: St. George has Arts & Science and Engineering. UTM and UTSC have one each.

create table if not exists faculties (
  id         text primary key,      -- 'uoft-artsci'
  campus_id  text not null references campuses(id),
  name       text not null          -- 'Faculty of Arts & Science'
);

alter table courses add column if not exists faculty_id text references faculties(id);
alter table courses add column if not exists breadth    text[];   -- breadth or distribution requirements it counts for

create index if not exists courses_faculty_idx on courses (faculty_id) where active;
create index if not exists courses_breadth_idx on courses using gin (breadth);

alter table faculties enable row level security;
