"""Loader 5: load one school's courses, then tag, link and embed them.

The school module scrapes its calendar (see loaders/schools/). This file is shared by
every school: it saves courses, tags skills, turns prerequisites into the shared and/or
format, builds the prereqs table and embeds descriptions.

Run from the repo root:
    python -m loaders.load_courses                      # UofT: CSC, MAT, STA
    python -m loaders.load_courses --subjects CSC,MAT,STA,ECO
"""

import argparse
import hashlib
import json

from loaders.schools import SCHOOLS
from trajectory.db import connect
from trajectory.embed import embed_passages, to_pg
from trajectory.prereqs import parse, to_groups
from trajectory.skills import find_skills

SAVE_SCHOOL_SQL = """
insert into schools (id, name, credit_unit) values (%(id)s, %(name)s, %(credit_unit)s)
on conflict (id) do update set name = excluded.name, credit_unit = excluded.credit_unit
"""

SAVE_COURSE_SQL = """
insert into courses (id, school_id, code, title, description, year_level, credits, terms_offered,
                     calendar_year, url, prereq_text, prereq_tree, exclusions, recommended, skills,
                     active, updated_at)
values (%(id)s, %(school_id)s, %(code)s, %(title)s, %(description)s, %(year_level)s, %(credits)s,
        %(terms_offered)s, %(calendar_year)s, %(url)s, %(prereq_text)s, %(prereq_tree)s,
        %(exclusions)s, %(recommended)s, %(skills)s, true, now())
on conflict (id) do update set
  title = excluded.title, description = excluded.description, year_level = excluded.year_level,
  credits = excluded.credits, terms_offered = excluded.terms_offered,
  calendar_year = excluded.calendar_year, url = excluded.url, prereq_text = excluded.prereq_text,
  prereq_tree = excluded.prereq_tree, exclusions = excluded.exclusions,
  recommended = excluded.recommended, skills = excluded.skills, active = true, updated_at = now()
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--school", default="uoft", choices=sorted(SCHOOLS))
    parser.add_argument("--subjects", default="CSC,MAT,STA")
    parser.add_argument("--cache", default=".cache")
    args = parser.parse_args()

    school = SCHOOLS[args.school]
    school_id = school.SCHOOL["id"]
    subjects = [s.strip().upper() for s in args.subjects.split(",") if s.strip()]

    print(f"Fetching {school_id} courses for {', '.join(subjects)}...")
    courses = school.fetch_courses(subjects, args.cache)
    rows = [to_row(school_id, c) for c in courses]
    print(f"Fetched {len(rows)} courses.")

    with connect() as conn, conn.cursor() as cur:
        cur.execute(SAVE_SCHOOL_SQL, school.SCHOOL)
        cur.executemany(SAVE_COURSE_SQL, rows)

        # Courses in these subjects that left the calendar are kept but hidden.
        ids = [r["id"] for r in rows]
        cur.execute(
            "update courses set active = false where school_id = %s and active "
            "and left(code, 3) = any(%s) and not (id = any(%s))",
            (school_id, subjects, ids),
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
        cur.executemany(
            "insert into prereqs (course_id, requires, option_group) values (%s, %s, %s)", links
        )

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

    tagged = sum(bool(r["skills"]) for r in rows)
    with_prereqs = sum(bool(r["groups"]) for r in rows)
    print(
        f"Saved {len(rows)} courses ({hidden} hidden). {with_prereqs} have prerequisites, "
        f"{len(links)} links. {tagged} have skill tags. Embedded {len(todo)}."
    )


if __name__ == "__main__":
    main()
