"""Loader 5: load course calendars, then tag, link and embed the courses.

Courses are grouped as school > campus > faculty. Each faculty has its own calendar
module (see loaders/schools/). This file is shared by every school: it saves courses,
tags skills, turns prerequisites into the shared and/or format, builds the prereqs
table and embeds descriptions.

Run from the repo root:
    python -m loaders.load_courses                                   # every UofT calendar, every course
    python -m loaders.load_courses --faculty uoft-utm                # one calendar
    python -m loaders.load_courses --faculty uoft-artsci --subjects CSC,PHY,CHM
"""

import argparse
import hashlib
import json

from loaders.schools import FACULTIES
from trajectory.db import connect
from trajectory.embed import embed_passages, to_pg
from trajectory.prereqs import parse, to_groups
from trajectory.skills import find_skills

SAVE_SCHOOL_SQL = """
insert into schools (id, name, credit_unit) values (%(id)s, %(name)s, %(credit_unit)s)
on conflict (id) do update set name = excluded.name, credit_unit = excluded.credit_unit
"""

SAVE_CAMPUS_SQL = """
insert into campuses (id, school_id, name, calendar) values (%(id)s, %(school_id)s, %(name)s, %(calendar)s)
on conflict (id) do update set name = excluded.name, calendar = excluded.calendar
"""

SAVE_FACULTY_SQL = """
insert into faculties (id, campus_id, name) values (%(id)s, %(campus_id)s, %(name)s)
on conflict (id) do update set campus_id = excluded.campus_id, name = excluded.name
"""

SAVE_COURSE_SQL = """
insert into courses (id, school_id, campus_id, faculty_id, code, title, description, year_level, credits,
                     terms_offered, calendar_year, url, prereq_text, prereq_tree, exclusions, recommended,
                     breadth, skills, active, updated_at)
values (%(id)s, %(school_id)s, %(campus_id)s, %(faculty_id)s, %(code)s, %(title)s, %(description)s,
        %(year_level)s, %(credits)s, %(terms_offered)s, %(calendar_year)s, %(url)s, %(prereq_text)s,
        %(prereq_tree)s, %(exclusions)s, %(recommended)s, %(breadth)s, %(skills)s, true, now())
on conflict (id) do update set
  campus_id = excluded.campus_id, faculty_id = excluded.faculty_id, title = excluded.title,
  description = excluded.description, year_level = excluded.year_level, credits = excluded.credits,
  terms_offered = excluded.terms_offered, calendar_year = excluded.calendar_year, url = excluded.url,
  prereq_text = excluded.prereq_text, prereq_tree = excluded.prereq_tree, exclusions = excluded.exclusions,
  recommended = excluded.recommended, breadth = excluded.breadth, skills = excluded.skills,
  active = true, updated_at = now()
"""

SAVE_EMBED_SQL = "update courses set embedding = %(vec)s::vector, embed_hash = %(hash)s where id = %(id)s"


def course_text(course):
    """The text a course is searched by."""
    return f"{course['code']} {course['title']}.\n{course['description']}"


def to_row(school_id, course):
    tree = parse(course["prereq_text"])
    return {
        **course,
        "id": f"{school_id}:{course['code']}",
        "school_id": school_id,
        "prereq_tree": json.dumps(tree) if tree else None,
        "skills": find_skills(f"{course['title']}\n{course['description']}"),
        "groups": to_groups(tree),
    }


def load_calendar(conn, cal, subjects, cache):
    school_id = cal.school["id"]
    label = f"{cal.school['name']}, {cal.campus['name']}: {cal.name}"
    print(f"Fetching {label} ({', '.join(subjects) if subjects else 'all subjects'})...")
    rows = [to_row(school_id, c) for c in cal.fetch(subjects, cache)]

    with conn.cursor() as cur:
        cur.execute(SAVE_SCHOOL_SQL, cal.school)
        cur.execute(SAVE_CAMPUS_SQL, cal.campus)
        cur.execute(SAVE_FACULTY_SQL, cal.faculty)
        cur.executemany(SAVE_COURSE_SQL, rows)

        # Courses that left this calendar are kept but hidden.
        ids = [r["id"] for r in rows]
        if subjects:
            cur.execute(
                "update courses set active = false where faculty_id = %s and active "
                "and left(code, 3) = any(%s) and not (id = any(%s))",
                (cal.id, subjects, ids),
            )
        else:
            cur.execute(
                "update courses set active = false where faculty_id = %s and active and not (id = any(%s))",
                (cal.id, ids),
            )
        hidden = cur.rowcount

        # Rebuild the prerequisite links for the courses we just loaded.
        cur.execute("delete from prereqs where course_id = any(%s)", (ids,))
        links = [
            (r["id"], f"{school_id}:{code}", group_no)
            for r in rows
            for group_no, group in enumerate(r["groups"])
            for code in group
        ]
        cur.executemany("insert into prereqs (course_id, requires, option_group) values (%s, %s, %s)", links)
        conn.commit()

        # Embed only courses whose text changed.
        cur.execute("select id, embed_hash from courses where id = any(%s)", (ids,))
        old = dict(cur.fetchall())
        todo = []
        for r in rows:
            text = course_text(r)
            h = hashlib.md5(text.encode()).hexdigest()
            if old.get(r["id"]) != h:
                todo.append((r["id"], text, h))
        for start in range(0, len(todo), 128):
            batch = todo[start : start + 128]
            vectors = embed_passages([t for _, t, _ in batch])
            cur.executemany(
                SAVE_EMBED_SQL,
                [{"id": cid, "vec": to_pg(v), "hash": h} for (cid, _, h), v in zip(batch, vectors)],
            )
            conn.commit()

    print(
        f"  Saved {len(rows)} courses ({hidden} hidden). "
        f"{sum(bool(r['groups']) for r in rows)} have prerequisites ({len(links)} links), "
        f"{sum(bool(r['breadth']) for r in rows)} count for breadth, "
        f"{sum(bool(r['skills']) for r in rows)} have skill tags. Embedded {len(todo)}."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--faculty", default="all", help="faculty ids, comma-separated, or 'all': " + ", ".join(FACULTIES))
    parser.add_argument("--subjects", default="all", help="subject codes like CSC,PHY,CHM, or 'all'")
    parser.add_argument("--cache", default=".cache")
    args = parser.parse_args()

    if args.faculty == "all":
        calendars = list(FACULTIES.values())
    else:
        unknown = [f for f in args.faculty.split(",") if f.strip() not in FACULTIES]
        if unknown:
            parser.error(f"unknown faculty: {', '.join(unknown)}. Choose from: {', '.join(FACULTIES)}")
        calendars = [FACULTIES[f.strip()] for f in args.faculty.split(",")]
    subjects = None if args.subjects == "all" else [s.strip().upper() for s in args.subjects.split(",") if s.strip()]

    with connect() as conn:
        for cal in calendars:
            load_calendar(conn, cal, subjects, args.cache)
    print("Done.")


if __name__ == "__main__":
    main()
