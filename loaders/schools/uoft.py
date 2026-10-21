"""University of Toronto: every campus and faculty calendar.

UofT has one course calendar per faculty or campus:
- St. George: Faculty of Arts & Science, and Faculty of Applied Science & Engineering
- Mississauga (UTM)
- Scarborough (UTSC)

They all run on the same website system, with small differences (handled below).
We read each public course search page. robots.txt allows these pages.
We send at most 1 request per second and cache every page on disk,
so a second run in the same place sends no requests.
"""

import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from trajectory.codes import pattern

SCHOOL = {"id": "uoft", "name": "University of Toronto", "credit_unit": "FCE"}

CAMPUSES = {
    "uoft-stg": {"id": "uoft-stg", "school_id": "uoft", "name": "St. George", "calendar": None},
    "uoft-utm": {"id": "uoft-utm", "school_id": "uoft", "name": "Mississauga (UTM)", "calendar": None},
    "uoft-utsc": {"id": "uoft-utsc", "school_id": "uoft", "name": "Scarborough (UTSC)", "calendar": None},
}

HEADERS = {"User-Agent": "TrajectoryBot/1.0 (student project; course search)"}
DELAY = 1.0  # seconds between requests
TIMEOUT = 30

CODE = pattern("uoft")
HEADING = re.compile(rf"^({CODE})\s*[-•–]\s*(.+)$")

# Field class on the page -> key in the shared course shape.
FIELDS = {
    "prerequisite": "prereq_text",
    "exclusion": "exclusions",
    "recommended": "recommended",
    "recommended-preparation": "recommended",
    "breadth-requirements": "breadth",
    "distribution-requirements": "breadth",
}


@dataclass
class Calendar:
    """One faculty's course calendar."""

    id: str  # faculty id, like 'uoft-artsci'
    name: str  # 'Faculty of Arts & Science'
    campus_id: str
    base: str
    search_path: str = "/search-courses"
    letter_years: bool = False  # UTSC: CSCA08H3, where A = year 1

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
    Calendar("uoft-artsci", "Faculty of Arts & Science", "uoft-stg", "https://artsci.calendar.utoronto.ca"),
    Calendar(
        "uoft-eng", "Faculty of Applied Science & Engineering", "uoft-stg", "https://engineering.calendar.utoronto.ca"
    ),
    Calendar("uoft-utm", "UTM Academic Calendar", "uoft-utm", "https://utm.calendar.utoronto.ca", "/course-search"),
    Calendar(
        "uoft-utsc", "UTSC Academic Calendar", "uoft-utsc", "https://utsc.calendar.utoronto.ca", letter_years=True
    ),
]


def calendar_year(today=None):
    """The calendar runs from fall to summer: Oct 2026 is in '2026-2027'."""
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{start + 1}"


def year_level(code, letter_years=False):
    """CSC148H1 -> 1. UTSC: CSCB07H3 -> 2 (A=1, B=2, C=3, D=4)."""
    ch = code[3]
    if ch.isdigit():
        return int(ch)
    return "ABCD".index(ch) + 1 if letter_years and ch in "ABCD" else None


def field_text(field):
    """Text of one field.

    Skips a bold label at the start ("Prerequisite:"), as on the Engineering calendar.
    Stops at a later bold sub-heading, such as the separate rule for Engineering students
    on the Arts & Science calendar.
    """
    content = field.select_one(".field-content")
    if content is None:
        return ""
    parts = []
    for node in content.children:
        if getattr(node, "name", None) == "strong":
            if not parts and node.get_text(strip=True).endswith(":"):
                continue
            break
        parts.append(node.get_text(" ") if hasattr(node, "get_text") else str(node))
    text = " ".join(parts).replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def split_breadth(text):
    """'Creative and Cultural Representations (1), Society and its Institutions (3)' -> 2 items.
    Names can contain commas ("Thought, Belief and Behaviour (2)"), so split only after ')'."""
    if not text:
        return []
    if re.search(r"\(\d\)", text):
        return [p.strip() for p in re.split(r"(?<=\))\s*,\s*", text) if p.strip()]
    return [text.strip()]


def parse_page(html, cal=None, year=None):
    """Return the courses on one search results page."""
    cal = cal or CALENDARS[0]
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for row in soup.select(".view-content > .views-row"):
        heading = row.find("h3")
        if heading is None:
            continue
        match = HEADING.match(heading.get_text(" ", strip=True))
        if not match:
            continue
        code, title = match.group(1), match.group(2).strip()

        body = row.select_one(".views-field-body .field-content, .views-field-field-desc .field-content")
        description = re.sub(r"\s+", " ", body.get_text(" ")).strip() if body else ""

        credits = 1.0 if code[6] == "Y" else 0.5
        credit_field = row.select_one(".views-field-field-credit")
        if credit_field:
            m = re.search(r"(\d+(?:\.\d+)?)", credit_field.get_text(" "))
            if m:
                credits = float(m.group(1))

        course = {
            "code": code,
            "title": title,
            "description": description,
            "prereq_text": "",
            "exclusions": "",
            "recommended": "",
            "breadth": [],
            "year_level": year_level(code, cal.letter_years),
            "credits": credits,
            "terms_offered": None,  # the calendars do not list terms
            "calendar_year": year or calendar_year(),
            "url": f"{cal.base}/course/{code}",
            "campus_id": cal.campus_id,
            "faculty_id": cal.id,
        }
        for field in row.select(".views-field"):
            for cls in field.get("class", []):
                name = cls.removeprefix("views-field-field-")
                if name != cls and name in FIELDS:
                    text = field_text(field)
                    key = FIELDS[name]
                    course[key] = split_breadth(text) if key == "breadth" else text
        out.append(course)
    return out


def last_page(html):
    """Number of the last results page (0 when there is only one)."""
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one(".pager__item--last a")
    if not link:
        return 0
    page = parse_qs(urlparse(link.get("href", "")).query).get("page", ["0"])[0]
    return int(page) if page.isdigit() else 0


class Fetcher:
    """Polite fetcher for one calendar: checks robots.txt, waits between requests, caches pages."""

    def __init__(self, cal, cache_dir):
        self.cal = cal
        self.cache = Path(cache_dir) / "uoft" / cal.id
        self.cache.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last = 0.0
        self.robots = None  # read on the first real request; cached pages need none

    def get(self, params):
        key = "_".join(f"{k}-{v}" for k, v in sorted(params.items())) + ".html"
        path = self.cache / key
        if path.exists():
            return path.read_text(encoding="utf-8")
        url = requests.Request("GET", self.cal.base + self.cal.search_path, params=params).prepare().url
        if self.robots is None:
            self.robots = RobotFileParser(self.cal.base + "/robots.txt")
            self.robots.read()
        if not self.robots.can_fetch(HEADERS["User-Agent"], url):
            raise RuntimeError(f"robots.txt does not allow {url}")
        wait = DELAY - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        res = self.session.get(url, timeout=TIMEOUT)
        self.last = time.monotonic()
        res.raise_for_status()
        path.write_text(res.text, encoding="utf-8")
        return res.text

    def all_pages(self, params):
        first = self.get({**params, "page": 0})
        return [first] + [self.get({**params, "page": p}) for p in range(1, last_page(first) + 1)]


def fetch_courses(cal, subjects, cache_dir):
    """Courses from one calendar. subjects=None loads every course.
    Otherwise only codes that start with a subject, like ["CSC", "PHY"] (UTSC CSCA08H3 counts as CSC)."""
    fetcher = Fetcher(cal, cache_dir)
    found = {}
    if not subjects:
        pages = fetcher.all_pages({})
        for html in pages:
            for course in parse_page(html, cal):
                found[course["code"]] = course
        print(f"  {cal.name}: {len(found)} courses from {len(pages)} pages")
        return list(found.values())
    for subject in subjects:
        pages = fetcher.all_pages({"course_keyword": subject})
        for html in pages:
            for course in parse_page(html, cal):
                # The keyword search also finds courses that only mention the subject.
                if course["code"].startswith(subject):
                    found[course["code"]] = course
        print(f"  {cal.name} {subject}: {sum(c.startswith(subject) for c in found)} courses")
    return list(found.values())
