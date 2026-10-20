"""Trajectory API.

Run from the repo root:  uvicorn api.main:app --reload

Privacy: resumes are read in memory, used for one search and dropped.
They are never written to disk, saved in the database or logged.
"""

import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import ConnectionPool

from trajectory import embed
from trajectory.course_search import MODES, course_detail, search
from trajectory.db import database_url
from trajectory.matching import ResumeError, match, pdf_text
from trajectory.terms import realistic_terms

MAX_UPLOAD = 2 * 1024 * 1024  # 2 MB
MAX_TEXT = 20_000  # characters of pasted resume text
RATE_LIMIT = int(os.environ.get("MATCH_RATE_LIMIT", "10"))  # matches per minute per visitor

pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(app):
    global pool
    pool = ConnectionPool(database_url(), min_size=1, max_size=4, open=True)
    embed.warm()  # load the model now, so the first student does not wait
    yield
    pool.close()


app = FastAPI(title="Trajectory API", lifespan=lifespan)

origins = [o.strip() for o in os.environ.get("WEB_ORIGIN", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])


# Small in-memory rate limit. Good enough for one server.
_hits: dict[str, deque] = defaultdict(deque)


def _check_rate(request: Request):
    forwarded = request.headers.get("x-forwarded-for", "")
    who = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    q = _hits[who]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Too many searches. Wait a minute and try again.")
    q.append(now)


def _count(event):
    """Count one use. Counts only, nothing about the person. Never fails a request."""
    try:
        with pool.connection() as conn:
            conn.execute(
                "insert into usage_daily (event, count) values (%s, 1) "
                "on conflict (day, event) do update set count = usage_daily.count + 1",
                (event,),
            )
    except Exception:
        pass


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/filters")
def filters():
    """Values for the filter menus on the site."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("select distinct unnest(terms) from postings where active order by 1")
        terms = realistic_terms(r[0] for r in cur.fetchall())
        cur.execute("select distinct category from postings where active and category is not null order by 1")
        categories = [r[0] for r in cur.fetchall()]
        cur.execute("select count(*), count(description) from postings where active")
        total, described = cur.fetchone()
        cur.execute(
            "select s.id, s.name, c.id, c.name, f.id, f.name, count(co.id) "
            "from schools s join campuses c on c.school_id = s.id "
            "join faculties f on f.campus_id = c.id "
            "left join courses co on co.faculty_id = f.id and co.active "
            "group by s.id, s.name, c.id, c.name, f.id, f.name order by s.name, c.id, f.name"
        )
        schools: dict[str, dict] = {}
        campuses: dict[str, dict] = {}
        for sid, sname, cid, cname, fid, fname, n in cur.fetchall():
            school = schools.setdefault(sid, {"id": sid, "name": sname, "campuses": []})
            if cid not in campuses:
                campuses[cid] = {"id": cid, "name": cname, "courses": 0, "faculties": [], "breadth": []}
                school["campuses"].append(campuses[cid])
            campuses[cid]["faculties"].append({"id": fid, "name": fname, "courses": n})
            campuses[cid]["courses"] += n
        cur.execute(
            "select campus_id, b, count(*) from courses, unnest(breadth) b "
            "where active group by campus_id, b order by campus_id, b"
        )
        for cid, name, n in cur.fetchall():
            if cid in campuses:
                campuses[cid]["breadth"].append({"name": name, "courses": n})
        schools = list(schools.values())
    return {
        "countries": [{"id": "CA", "name": "Canada"}, {"id": "US", "name": "United States"}, {"id": "other", "name": "Other"}],
        "terms": terms,
        "categories": categories,
        "schools": schools,
        "open_postings": total,
        "with_description": described,
    }


@app.post("/match")
def match_resume(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    country: str | None = Form(None),
    term: str | None = Form(None),
    category: str | None = Form(None),
    school: str = Form("uoft"),
    campus: str | None = Form(None),
):
    """Rank open internships for one resume. Send a PDF as `file`, or plain text as `text`."""
    _check_rate(request)
    started = time.perf_counter()

    if file is not None:
        data = file.file.read(MAX_UPLOAD + 1)
        file.file.close()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "The PDF is bigger than 2 MB.")
        if not data.startswith(b"%PDF"):
            raise HTTPException(415, "Upload a PDF file.")
        try:
            resume = pdf_text(data)
        except ResumeError as err:
            raise HTTPException(422, str(err)) from None
        finally:
            del data
    elif text and text.strip():
        resume = text[:MAX_TEXT]
    else:
        raise HTTPException(400, "Send a resume PDF or paste the text.")

    with pool.connection() as conn:
        result = match(conn, resume, country=country or None, term=term or None,
                       category=category or None, school=school or None, campus=campus or None)
    del resume
    _count("match")
    result["took_ms"] = round((time.perf_counter() - started) * 1000)
    return result


@app.get("/courses/search")
def course_search(
    q: str = Query("", max_length=300),
    school: str = "uoft",
    campus: str | None = None,
    faculty: str | None = None,
    breadth: str | None = None,
    year: int | None = Query(None, ge=1, le=4),
    mode: str = Query("hybrid", pattern="^(" + "|".join(MODES) + ")$"),
    limit: int = Query(10, ge=1, le=100),
):
    with pool.connection() as conn:
        if len(q.strip()) < 2 and not (breadth or faculty or year):
            raise HTTPException(422, "Type at least 2 letters, or pick a filter.")
        results = search(conn, q, school=school, mode=mode, limit=limit, campus=campus or None,
                         faculty=faculty or None, breadth=breadth or None, year=year)
    _count("course_search")
    return {"query": q, "mode": mode, "results": results}


@app.get("/courses/{course_id}")
def course(course_id: str):
    """One course with its prerequisite graph. The id looks like 'uoft:CSC207H1'."""
    with pool.connection() as conn:
        found = course_detail(conn, course_id)
    if found is None:
        raise HTTPException(404, "Course not found.")
    return found
