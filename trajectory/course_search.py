"""Course search and the prerequisite graph.

Search is hybrid: keyword search (Postgres full text) finds exact words like "CSC 207"
or "linear algebra". Vector search finds meaning, like "robots" matching "autonomous
systems". The two ranked lists are merged with reciprocal rank fusion (RRF): each
course gets 1 / (60 + rank) from each list it appears in.
"""

import re

from trajectory.embed import embed_query, to_pg
from trajectory.prereqs import codes

RRF_K = 60
POOL = 50  # results taken from each list before merging
MODES = ("hybrid", "keyword", "vector")

FILTERS = """
  and (%(campus)s::text is null or campus_id = %(campus)s)
  and (%(faculty)s::text is null or faculty_id = %(faculty)s)
  and (%(breadth)s::text is null or %(breadth)s = any(breadth))
  and (%(year)s::int is null or year_level = %(year)s)
"""

KEYWORD_SQL = f"""
select id from courses, websearch_to_tsquery('english', %(q)s) query
where active and school_id = %(school)s and fts @@ query
{FILTERS}
order by ts_rank_cd(fts, query) desc, code
limit %(limit)s
"""

VECTOR_SQL = f"""
select id from courses
where active and school_id = %(school)s and embedding is not null
{FILTERS}
order by embedding <=> %(vec)s::vector
limit %(limit)s
"""

# A course code in the question: "CSC 263", "csc263", UTSC style "CSCA08", or "CS 135".
CODE_IN_QUERY = re.compile(r"\b([A-Za-z]{2,4})\s?(\d{3}|[A-Za-z]\d{2})", re.IGNORECASE)

CODE_SQL = f"""
select id from courses
where active and school_id = %(school)s and code like any(%(patterns)s)
{FILTERS}
order by code
"""

COURSE_COLS = "id, campus_id, faculty_id, breadth, code, title, description, year_level, credits, url, skills, prereq_text"


def _keyword_query(q):
    """Match any of the words, so plain-language questions still find courses.
    Courses that match more words rank higher."""
    words = re.findall(r"[A-Za-z0-9]+", q)
    return " or ".join(words)


def rrf(*ranked_lists, k=RRF_K):
    """Merge ranked lists of ids. Returns [(id, score)] best first."""
    scores = {}
    for ids in ranked_lists:
        for rank, cid in enumerate(ids, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def _filters(school, campus=None, faculty=None, breadth=None, year=None):
    return {"school": school, "campus": campus, "faculty": faculty, "breadth": breadth, "year": year}


def search_ids(conn, q, school="uoft", mode="hybrid", limit=10, campus=None, faculty=None, breadth=None, year=None):
    """Ranked course ids for a question. Used by the API and the evals."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    f = _filters(school, campus, faculty, breadth, year)
    keyword, vector = [], []
    with conn.cursor() as cur:
        if mode in ("hybrid", "keyword"):
            cur.execute(KEYWORD_SQL, {**f, "q": _keyword_query(q), "limit": POOL})
            keyword = [r[0] for r in cur.fetchall()]
        if mode in ("hybrid", "vector"):
            cur.execute(VECTOR_SQL, {**f, "vec": to_pg(embed_query(q)), "limit": POOL})
            vector = [r[0] for r in cur.fetchall()]
        # A course code in the question, like "CSC 263", goes straight to the top.
        patterns = [f"{a.upper()}{b.upper()}%" for a, b in CODE_IN_QUERY.findall(q)]
        exact = []
        if patterns:
            cur.execute(CODE_SQL, {**f, "patterns": patterns})
            exact = [r[0] for r in cur.fetchall()]
    lists = [lst for lst in (keyword, vector) if lst]
    merged = rrf(*lists)
    top = [(cid, 1.0) for cid in exact]
    return (top + [(cid, s) for cid, s in merged if cid not in exact])[:limit]


def _rows(cur):
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


BROWSE_SQL = f"""
select id from courses
where active and school_id = %(school)s
{FILTERS}
order by year_level nulls last, code
limit %(limit)s
"""


def search(conn, q, school="uoft", mode="hybrid", limit=10, campus=None, faculty=None, breadth=None, year=None):
    """Search with a question. With no question, list the courses that match the filters
    (for example, every course that counts for one breadth requirement)."""
    if q and q.strip():
        ranked = search_ids(conn, q, school, mode, limit, campus, faculty, breadth, year)
    else:
        with conn.cursor() as cur:
            cur.execute(BROWSE_SQL, {**_filters(school, campus, faculty, breadth, year), "limit": limit})
            ranked = [(r[0], 0.0) for r in cur.fetchall()]
    return _load(conn, ranked)


def _load(conn, ranked):
    if not ranked:
        return []
    with conn.cursor() as cur:
        cur.execute(f"select {COURSE_COLS} from courses where id = any(%s)", ([cid for cid, _ in ranked],))
        by_id = {r["id"]: r for r in _rows(cur)}
    out = []
    for cid, s in ranked:
        row = by_id[cid]
        row["credits"] = float(row["credits"]) if row["credits"] is not None else None
        row["score"] = round(s, 5)
        out.append(row)
    return out


def course_detail(conn, course_id, depth=3):
    """One course, what it needs (as a graph, up to `depth` steps back) and what it unlocks."""
    with conn.cursor() as cur:
        cur.execute(
            f"select {COURSE_COLS}, school_id, exclusions, recommended, prereq_tree, calendar_year "
            "from courses where id = %s",
            (course_id,),
        )
        rows = _rows(cur)
        if not rows:
            return None
        course = rows[0]
        course["credits"] = float(course["credits"]) if course["credits"] is not None else None
        cur.execute(
            "select s.name, c.name, f.name from schools s left join campuses c on c.id = %s "
            "left join faculties f on f.id = %s where s.id = %s",
            (course["campus_id"], course["faculty_id"], course["school_id"]),
        )
        found = cur.fetchone()
        course["school_name"], course["campus_name"], course["faculty_name"] = found if found else (None,) * 3

        # Walk back through prerequisites, one level at a time.
        edges, seen, frontier = [], {course_id}, [course_id]
        for level in range(1, depth + 1):
            if not frontier:
                break
            cur.execute(
                "select course_id, requires, option_group from prereqs where course_id = any(%s)",
                (frontier,),
            )
            nxt = []
            for cid, req, group in cur.fetchall():
                edges.append({"from": req, "to": cid, "group": group, "level": level})
                if req not in seen:
                    seen.add(req)
                    nxt.append(req)
            frontier = nxt

        # Courses this one unlocks (one step forward).
        cur.execute(
            "select distinct p.course_id, c.code, c.title from prereqs p join courses c on c.id = p.course_id "
            "where p.requires = %s and c.active order by c.code",
            (course_id,),
        )
        unlocks = [{"id": i, "code": c, "title": t} for i, c, t in cur.fetchall()]

        cur.execute("select id, code, title, year_level from courses where id = any(%s)", (list(seen),))
        known = {i: {"id": i, "code": c, "title": t, "year_level": y, "loaded": True} for i, c, t, y in cur.fetchall()}

    edges = _group_by_requirement(conn, edges)
    nodes = [
        known.get(n) or {"id": n, "code": n.split(":", 1)[-1], "title": None, "year_level": None, "loaded": False}
        for n in seen
    ]
    course["graph"] = {"nodes": nodes, "edges": edges}
    course["unlocks"] = unlocks
    return course


def _group_by_requirement(conn, edges):
    """Colour edges by which requirement of the target course they belong to.

    The prereqs table stores flat "or" groups, which can repeat a course. For the graph,
    each edge gets the index of the top-level requirement in the course's prereq_tree,
    and repeated edges are dropped.
    """
    targets = list({e["to"] for e in edges})
    if not targets:
        return edges
    with conn.cursor() as cur:
        cur.execute("select id, prereq_tree from courses where id = any(%s)", (targets,))
        trees = dict(cur.fetchall())

    def requirement_of(target, source):
        tree = trees.get(target)
        if not tree:
            return 0
        items = tree["and"] if isinstance(tree, dict) and "and" in tree else [tree]
        code = source.split(":", 1)[-1]
        return next((i for i, item in enumerate(items) if code in codes(item)), 0)

    out, seen = [], set()
    for e in edges:
        key = (e["from"], e["to"])
        if key in seen:
            continue
        seen.add(key)
        out.append({**e, "group": requirement_of(e["to"], e["from"])})
    return out

