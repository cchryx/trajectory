"""One module per school. Each one scrapes a course calendar and returns the shared course shape.

Every school module has:
- SCHOOL: {"id": "uoft", "name": "...", "credit_unit": "FCE"}
- fetch_courses(subjects, cache_dir) -> list of course dicts with these keys:
    code, title, description, prereq_text, exclusions, recommended,
    year_level, credits, terms_offered, calendar_year, url

The shared loader (loaders/load_courses.py) does the rest: skill tags, the and/or
prerequisite format, vectors and saving. To add a school, add one module here
and list it in SCHOOLS.
"""

from loaders.schools import uoft

SCHOOLS = {uoft.SCHOOL["id"]: uoft}
