"""Course calendars, grouped as school > campus > faculty.

Each school is one module in this folder (see uoft.py, and _template.py to start a new one).
The module has a CALENDARS list. Each calendar is one faculty's course calendar, with:
- id:      the faculty id, like 'uoft-artsci'
- name:    'Faculty of Arts & Science'
- school:  {"id": "uoft", "name": "...", "credit_unit": "FCE"}
- campus:  {"id": "uoft-stg", "school_id": "uoft", "name": "St. George", "calendar": None}
- faculty: {"id": "uoft-artsci", "campus_id": "uoft-stg", "name": "Faculty of Arts & Science"}
- fetch(subjects, cache_dir) -> list of course dicts with these keys:
    code, title, description, prereq_text, exclusions, recommended, breadth,
    year_level, credits, terms_offered, calendar_year, url, campus_id, faculty_id

Ids: a campus id starts with its school id and a dash ('uoft-stg'). The website uses
that to know which school a campus belongs to.

The shared loader (loaders/load_courses.py) does the rest: skill tags, the and/or
prerequisite format, vectors and saving.

To add a school: copy _template.py, fill it in, and add the module to SCHOOLS below.
"""

from loaders.schools import uoft

SCHOOLS = [uoft]

# Keyed by faculty id, like 'uoft-artsci'.
FACULTIES = {cal.id: cal for school in SCHOOLS for cal in school.CALENDARS}
