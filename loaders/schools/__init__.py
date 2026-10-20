"""Course calendars, grouped as school > campus > faculty.

Each faculty calendar is one object with:
- school:  {"id": "uoft", "name": "...", "credit_unit": "FCE"}
- campus:  {"id": "uoft-stg", "school_id": "uoft", "name": "St. George", "calendar": None}
- faculty: {"id": "uoft-artsci", "campus_id": "uoft-stg", "name": "Faculty of Arts & Science"}
- fetch(subjects, cache_dir) -> list of course dicts with these keys:
    code, title, description, prereq_text, exclusions, recommended, breadth,
    year_level, credits, terms_offered, calendar_year, url, campus_id, faculty_id

The shared loader (loaders/load_courses.py) does the rest: skill tags, the and/or
prerequisite format, vectors and saving. To add a school, write a module like uoft.py
and add its calendars to FACULTIES.
"""

from loaders.schools import uoft

# Keyed by faculty id, like 'uoft-artsci'.
FACULTIES = {cal.id: cal for cal in uoft.CALENDARS}
