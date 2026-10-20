"""Measure search quality on fixed test sets.

Course search: top-5 recall for keyword, vector and hybrid search.
  Questions live in evals/course_questions.json. Goal: hybrid beats both.

Job matching: for each test resume, how many of its 5 good-fit postings land in the top 10.
  Cases live in the eval_cases table (kind = 'job'). Goal: 3 of 5 or better.
  Add one:  python -m evals.run_evals --add-job resumes/jane.txt 12345,23456,34567,45678,56789

Run from the repo root:  python -m evals.run_evals
"""

import argparse
import json
import time
from pathlib import Path

from trajectory.course_search import MODES, search_ids
from trajectory.db import connect
from trajectory.matching import match

HERE = Path(__file__).parent


def course_eval(conn, school="uoft", k=5):
    questions = json.loads((HERE / "course_questions.json").read_text())
    with conn.cursor() as cur:
        cur.execute("select id from courses where school_id = %s and active", (school,))
        loaded = {r[0] for r in cur.fetchall()}

    usable = []
    for q in questions:
        expected = [f"{school}:{c}" for c in q["expected"]]
        present = [e for e in expected if e in loaded]
        if present:
            usable.append((q["question"], present))
    print(f"Course search: {len(usable)} of {len(questions)} questions have their courses loaded.")
    if not usable:
        print("  Load courses first: python -m loaders.load_courses")
        return

    for mode in MODES:
        recalls, started = [], time.perf_counter()
        for question, expected in usable:
            top = [cid for cid, _ in search_ids(conn, question, school, mode, k)]
            recalls.append(sum(e in top for e in expected) / len(expected))
        ms = (time.perf_counter() - started) * 1000 / len(usable)
        print(f"  {mode:<8} top-{k} recall {sum(recalls) / len(recalls):.0%}   ({ms:.0f} ms per search)")


def job_eval(conn, k=10):
    with conn.cursor() as cur:
        cur.execute("select id, query, expected from eval_cases where kind = 'job' order by id")
        cases = cur.fetchall()
    print(f"Job matching: {len(cases)} test resumes.")
    if not cases:
        print("  Add some with --add-job (see the top of this file).")
        return
    passed = 0
    for case_id, resume, expected in cases:
        started = time.perf_counter()
        top = [j["id"] for j in match(conn, resume, school=None)["jobs"][:k]]
        hits = sum(e in top for e in expected)
        passed += hits >= 3
        ms = (time.perf_counter() - started) * 1000
        print(f"  case {case_id}: {hits} of {len(expected)} in the top {k} ({ms:.0f} ms)")
    print(f"  {passed} of {len(cases)} cases reach the goal (3 of 5).")


def add_job(conn, resume_path, ids):
    text = Path(resume_path).read_text(encoding="utf-8")
    expected = [i.strip() for i in ids.split(",") if i.strip()]
    conn.execute("insert into eval_cases (kind, query, expected) values ('job', %s, %s)", (text, expected))
    print(f"Added a job case with {len(expected)} expected postings.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--add-job", nargs=2, metavar=("RESUME_TXT", "POSTING_IDS"))
    parser.add_argument("--school", default="uoft")
    args = parser.parse_args()
    with connect() as conn:
        if args.add_job:
            add_job(conn, *args.add_job)
            return
        course_eval(conn, args.school)
        job_eval(conn)


if __name__ == "__main__":
    main()
