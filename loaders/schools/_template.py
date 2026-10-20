"""TEMPLATE: copy this file to start a new school, like loaders/schools/uwaterloo.py.

Steps:
1. Copy this file and rename it to your school id.
2. Fill in SCHOOL, CAMPUSES and CALENDARS.
3. Write fetch_courses() so it returns every course in the shared shape (see below).
4. Add your code format to trajectory/codes.py, like "uwaterloo": r"...".
5. Add the module to SCHOOLS in loaders/schools/__init__.py.
6. Save one real page or API response in tests/fixtures/ and add a parser test.
7. Run: python -m loaders.load_courses --faculty <your faculty id> --subjects CS

Be polite to the school's website:
- Check robots.txt and the site's terms first. Prefer an official API or open data.
- Wait at least 1 second between requests (DELAY).
- Cache every response on disk, so a second run sends no requests.
- Send a clear User-Agent.
"""

from dataclasses import dataclass

SCHOOL = {
    "id": "example",  # short, lowercase, no spaces: "uwaterloo"
    "name": "Example University",
    "credit_unit": "credit",  # what the school calls a credit: "FCE", "unit", "credit"
}

# A campus id starts with the school id and a dash.
CAMPUSES = {
    "example-main": {"id": "example-main", "school_id": "example", "name": "Main campus", "calendar": None},
}

HEADERS = {"User-Agent": "TrajectoryBot/1.0 (open source student project; course search)"}
DELAY = 1.0  # seconds between requests


@dataclass
class Calendar:
    """One faculty's course calendar. If the school has one calendar, make one faculty for it."""

    id: str  # faculty id: "example-eng"
    name: str  # "Faculty of Engineering"
    campus_id: str

    @property
    def school(self):
        return SCHOOL

    @property
    def campus(self):
        return CAMPUSES[self.campus_id]

    @property
    def faculty(self):
        return {"id": self.id, "campus_id": self.campus_id, "name": self.name}

    def fetch(self, subjects, cache_dir):
        return fetch_courses(self, subjects, cache_dir)


CALENDARS = [
    Calendar("example-main", "Undergraduate calendar", "example-main"),
]


def fetch_courses(cal, subjects, cache_dir):
    """Return every course as a dict in the shared shape.

    subjects is None for all subjects, or a list like ["CS", "MATH"].
    cache_dir is a folder path (a string). Save raw responses under
    Path(cache_dir) / SCHOOL["id"] / cal.id.
    """
    example = {
        "code": "CS135",  # no spaces, capitals. "CS 135" becomes "CS135"
        "title": "Designing Functional Programs",
        "description": "Plain text description.",
        # Prerequisite text in the shared format: "/" or "or" = any one, "," ";" or "and" = all.
        # Rewrite school wording first. Example: "One of A, B" -> "A/B".
        "prereq_text": "CS115/CS135",
        "exclusions": "",  # text that names courses you can't take with this one
        "recommended": "",
        "breadth": [],  # breadth or distribution groups, as a list of names
        "year_level": 1,  # 1 to 4, or None
        "credits": 0.5,  # in the school's credit_unit, or None
        "terms_offered": ["F", "S"],  # F = fall, S = winter, Y = full year; [] if unknown
        "calendar_year": "2026-2027",
        "url": "https://example.edu/courses/CS135",
        "campus_id": cal.campus_id,
        "faculty_id": cal.id,
    }
    raise NotImplementedError(f"Fill in fetch_courses for {cal.id}. A course looks like: {example}")
