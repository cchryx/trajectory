"""One module per school. Each one scrapes a course calendar and returns the shared course shape.

Every school module has:
- SCHOOL: {"id": "uoft", "name": "...", "credit_unit": "FCE"}
- CAMPUS: {"id": "uoft-stg", "school_id": "uoft", "name": "St. George", "calendar": "..."}
- fetch_courses(subjects, cache_dir) -> list of course dicts with these keys:
    code, title, description, prereq_text, exclusions, recommended,
    year_level, credits, terms_offered, calendar_year, url, campus_id

A school with several campuses gets one module per campus calendar,
for example uoft (St. George), later utm and utsc. They share the same SCHOOL.

The shared loader (loaders/load_courses.py) does the rest: skill tags, the and/or
prerequisite format, vectors and saving. To add a school, add one module here
and list it in CAMPUSES.
"""

from loaders.schools import uoft

# Keyed by campus id. Run one with: python -m loaders.load_courses --campus uoft-stg
CAMPUSES = {uoft.CAMPUS["id"]: uoft}
