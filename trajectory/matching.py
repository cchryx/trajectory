"""Rank open internships against one resume.

fit = W_MEANING x similarity(resume, posting) + W_SKILLS x (posting skills found in resume / posting skills)

A posting with no skill tags is scored on meaning alone.
Nothing here saves or logs the resume.
"""

import io
import os
from collections import Counter

from pypdf import PdfReader

from trajectory.embed import embed_passages, to_pg
from trajectory.skills import find_skills

W_MEANING = float(os.environ.get("FIT_W_MEANING", "0.6"))
W_SKILLS = 1.0 - W_MEANING
CANDIDATES = 50  # closest postings to score
TOP = 20  # postings returned
COMMON = 8  # most common missing skills returned
COURSES_PER_SKILL = 3


class ResumeError(ValueError):
    """The resume could not be read. The message is safe to show to the user."""


def pdf_text(data):
    """Pull the text out of a PDF, in memory."""
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as err:
        raise ResumeError("We could not open this PDF. Try exporting it again.") from err
    if len(text.strip()) < 50:
        raise ResumeError(
            "We could not find text in this PDF. It may be a scan. "
            "Export it from Word or Google Docs and try again."
        )
    return text


CANDIDATES_SQL = """
select id, company, title, url, locations, terms, category, date_posted, skills,
       description is not null as has_description,
       1 - (embedding <=> %(vec)s::vector) as similarity
from postings
where active and embedding is not null
  and (%(country)s::text is null or %(country)s = any(country))
  and (%(term)s::text is null or %(term)s = any(terms))
  and (%(category)s::text is null or category = %(category)s)
order by embedding <=> %(vec)s::vector
limit %(limit)s
"""

# Courses tagged with one skill, best first: a course whose title names the skill
# ("Introduction to Machine Learning") beats one that mentions it once.
COURSES_FOR_SKILL_SQL = """
select id, code, title, year_level, url
from courses, plainto_tsquery('english', %(skill)s) query
where active and school_id = %(school)s and %(skill)s = any(skills)
  and (%(campus)s::text is null or campus_id = %(campus)s)
order by ts_rank_cd(fts, query) desc, year_level nulls last, code
limit %(limit)s
"""


def score(similarity, posting_skills, resume_skills):
    """Return (fit, matched, missing). Fit is between 0 and 1."""
    posting_skills = posting_skills or []
    matched = [s for s in posting_skills if s in resume_skills]
    missing = [s for s in posting_skills if s not in resume_skills]
    if posting_skills:
        fit = W_MEANING * similarity + W_SKILLS * len(matched) / len(posting_skills)
    else:
        fit = similarity
    return max(0.0, min(1.0, fit)), matched, missing


def match(conn, resume_text, country=None, term=None, category=None, school="uoft", campus=None):
    """Rank postings for one resume. Returns a dict ready to send as JSON."""
    resume_skills = set(find_skills(resume_text))
    vec = embed_passages([resume_text])[0]

    with conn.cursor() as cur:
        cur.execute(
            CANDIDATES_SQL,
            {"vec": to_pg(vec), "country": country, "term": term, "category": category, "limit": CANDIDATES},
        )
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    jobs = []
    for row in rows:
        fit, matched, missing = score(row["similarity"], row["skills"], resume_skills)
        jobs.append(
            {
                **{k: row[k] for k in ("id", "company", "title", "url", "locations", "terms", "category")},
                "date_posted": row["date_posted"].isoformat() if row["date_posted"] else None,
                "has_description": row["has_description"],
                "similarity": round(row["similarity"], 4),
                "fit": round(fit, 4),
                "matched_skills": matched,
                "missing_skills": missing,
            }
        )
    jobs.sort(key=lambda j: j["fit"], reverse=True)
    jobs = jobs[:TOP]

    counts = Counter(s for j in jobs for s in j["missing_skills"])
    common = [{"skill": s, "jobs": n, "courses": []} for s, n in counts.most_common(COMMON)]
    if common and school:
        with conn.cursor() as cur:
            for item in common:
                cur.execute(
                    COURSES_FOR_SKILL_SQL,
                    {"school": school, "campus": campus, "skill": item["skill"], "limit": COURSES_PER_SKILL},
                )
                item["courses"] = [
                    {"id": cid, "code": code, "title": title, "year_level": yl, "url": url}
                    for cid, code, title, yl, url in cur.fetchall()
                ]

    return {"resume_skills": sorted(resume_skills), "jobs": jobs, "common_missing": common}
