"""Course details for the planner: prerequisites, exclusions, terms and section times.

The planner page does its own checks with this data (prerequisites met, offered in
that term, time clashes, credit load). The plan itself lives in the page's link,
not in the database.
"""

from trajectory.codes import find_codes

MAX_IDS = 120


def planner_courses(conn, ids):
    """Details for up to MAX_IDS course ids, like 'uoft:CSC207H1'."""
    ids = list(dict.fromkeys(ids))[:MAX_IDS]
    if not ids:
        return {"courses": [], "timetable_year": None}
    with conn.cursor() as cur:
        cur.execute(
            "select id, school_id, code, title, credits, year_level, campus_id, faculty_id, prereq_tree, "
            "exclusions, breadth, url, terms_offered from courses where id = any(%s)",
            (ids,),
        )
        cols = [d.name for d in cur.description]
        courses = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}

        cur.execute(
            "select course_id, academic_year, term, sections from offerings where course_id = any(%s) "
            "order by academic_year desc",
            (ids,),
        )
        for cid, year, term, sections in cur.fetchall():
            course = courses[cid]
            course.setdefault("offerings", {}).setdefault(year, {})[term] = sections

        cur.execute("select max(academic_year) from offerings")
        timetable_year = cur.fetchone()[0]

    out = []
    for cid in ids:
        c = courses.get(cid)
        if c is None:
            continue
        c["credits"] = float(c["credits"]) if c["credits"] is not None else None
        # Course codes named in the exclusions text: you cannot take both.
        c["exclusion_codes"] = sorted(find_codes(c.pop("exclusions"), c.pop("school_id")))
        c.setdefault("offerings", {})
        out.append(c)
    return {"courses": out, "timetable_year": timetable_year}
