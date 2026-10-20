"""Loader 6: load which term each course runs in, and its section times, for the planner.

Run from the repo root:
    python -m loaders.load_timetable                 # all UofT divisions, about 7 minutes
    python -m loaders.load_timetable --division ERIN

Safety checks, so a change on UofT's side never wipes good data:
1. Every response is checked for the fields we use (see uoft_timetable.py).
2. If a division returns far fewer courses than last time (under half, by default),
   nothing is saved for it.
3. A division that fails does not stop the others, but the run ends with an error,
   so the GitHub Action fails and GitHub emails you.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from loaders.schools.uoft_timetable import DIVISIONS, Client, TimetableChanged, academic_year, fetch_division, parse_course
from trajectory.db import connect

SAVE_SQL = """
insert into offerings (course_id, academic_year, term, sections, updated_at)
values (%s, %s, %s, %s, now())
on conflict (course_id, academic_year, term) do update set sections = excluded.sections, updated_at = now()
"""


def last_count(cur, division, year):
    cur.execute(
        "select courses from timetable_runs where source = %s and academic_year = %s order by ran_at desc limit 1",
        (division, year),
    )
    row = cur.fetchone()
    return row[0] if row else None


def save_division(conn, division, year, raw_courses, min_ratio):
    """Check and save one division. Returns a short summary line."""
    faculty = DIVISIONS[division]
    offerings = defaultdict(list)  # (code, term) -> sections
    for course in raw_courses:
        code, term, sections = parse_course(course)
        if term not in ("F", "S", "Y"):
            continue  # summer or special sessions: not planned yet
        offerings[(code, term)].extend(sections)
    if not offerings:
        raise TimetableChanged(f"{division}: no courses found. UofT may have changed the timetable API.")

    with conn.cursor() as cur:
        before = last_count(cur, division, year)
        if before and len(offerings) < before * min_ratio:
            raise TimetableChanged(
                f"{division}: only {len(offerings)} courses, down from {before} last time. "
                "Nothing saved. Check the timetable site, then run again with --min-ratio 0 if this is real."
            )

        cur.execute("select id from courses where school_id = 'uoft'")
        known = {r[0] for r in cur.fetchall()}
        rows = [
            (f"uoft:{code}", year, term, json.dumps(sections))
            for (code, term), sections in offerings.items()
            if f"uoft:{code}" in known
        ]
        cur.executemany(SAVE_SQL, rows)

        # Offerings this division no longer lists for this year are removed.
        kept = [f"{r[0]}|{r[2]}" for r in rows]
        cur.execute(
            "delete from offerings o using courses c where c.id = o.course_id and c.faculty_id = %s "
            "and o.academic_year = %s and not (o.course_id || '|' || o.term = any(%s))",
            (faculty, year, kept),
        )
        removed = cur.rowcount

        # Keep the course's own list of terms up to date: 'F', 'S', 'Y'.
        cur.execute(
            "update courses c set terms_offered = t.terms from ("
            "  select course_id, array_agg(distinct term order by term) terms from offerings"
            "  where academic_year = %s group by course_id) t "
            "where c.id = t.course_id and c.faculty_id = %s",
            (year, faculty),
        )
        cur.execute(
            "insert into timetable_runs (source, academic_year, courses) values (%s, %s, %s)",
            (division, year, len(offerings)),
        )
    conn.commit()
    skipped = len(offerings) - len(rows)
    return f"  {division}: saved {len(rows)} offerings, removed {removed}, skipped {skipped} not in our course list."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--division", default="all", help="division codes, comma-separated: " + ", ".join(DIVISIONS))
    parser.add_argument("--min-ratio", type=float, default=0.5, help="stop if a division drops below this share of last run")
    parser.add_argument("--fixture", help="read <DIVISION>.json files from this folder instead of the API (tests)")
    args = parser.parse_args()

    divisions = list(DIVISIONS) if args.division == "all" else [d.strip().upper() for d in args.division.split(",")]
    client = None if args.fixture else Client()
    sessions = None if args.fixture else client.sessions()

    failed = []
    with connect() as conn:
        for division in divisions:
            try:
                if args.fixture:
                    data = json.loads((Path(args.fixture) / f"{division}.json").read_text(encoding="utf-8"))
                    div_sessions, courses = data["sessions"], data["courses"]
                else:
                    div_sessions = sessions
                    print(f"Fetching {division} for sessions {', '.join(sessions)}...")
                    courses, total = fetch_division(client, division, sessions)
                    if total and len(courses) < total * 0.9:
                        raise TimetableChanged(f"{division}: got {len(courses)} of {total} courses.")
                year = academic_year(div_sessions[0])
                print(save_division(conn, division, year, courses, args.min_ratio))
            except (TimetableChanged, OSError, ValueError) as err:
                conn.rollback()
                print(f"  {division} FAILED: {err}", file=sys.stderr)
                failed.append(division)

    if failed:
        sys.exit(f"Timetable load failed for {', '.join(failed)}. Old data was kept.")
    print("Done.")


if __name__ == "__main__":
    main()
