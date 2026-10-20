"""University of Toronto, Faculty of Arts & Science calendar.

Reads the public course search at artsci.calendar.utoronto.ca, one subject at a time.
robots.txt allows /search-courses. We send at most 1 request per second and cache
every page on disk, so a second run in the same place sends no requests.
"""

import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

SCHOOL = {"id": "uoft", "name": "University of Toronto (Arts & Science)", "credit_unit": "FCE"}

BASE = "https://artsci.calendar.utoronto.ca"
SEARCH = BASE + "/search-courses"
HEADERS = {"User-Agent": "TrajectoryBot/1.0 (student project; course search)"}
DELAY = 1.0  # seconds between requests
TIMEOUT = 30

HEADING = re.compile(r"^([A-Z]{3}\d{3}[HY]\d)\s*-\s*(.+)$")
FIELDS = {
    "prerequisite": "prereq_text",
    "exclusion": "exclusions",
    "recommended": "recommended",
}


def calendar_year(today=None):
    """The calendar runs from fall to summer: Oct 2026 is in '2026-2027'."""
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{start + 1}"


def field_text(field):
    """Text of one field. Stops at a bold sub-heading such as the rule for Engineering students."""
    content = field.select_one(".field-content")
    if content is None:
        return ""
    parts = []
    for node in content.children:
        if getattr(node, "name", None) == "strong":
            break
        parts.append(node.get_text(" ") if hasattr(node, "get_text") else str(node))
    text = " ".join(parts).replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_page(html, year=None):
    """Return the courses on one search results page."""
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

        body = row.select_one(".views-field-body .field-content")
        description = re.sub(r"\s+", " ", body.get_text(" ")).strip() if body else ""

        course = {
            "code": code,
            "title": title,
            "description": description,
            "prereq_text": "",
            "exclusions": "",
            "recommended": "",
            "year_level": int(code[3]),
            "credits": 1.0 if code[6] == "Y" else 0.5,
            "terms_offered": None,  # the calendar does not list terms
            "calendar_year": year or calendar_year(),
            "url": f"{BASE}/course/{code.lower()}",
        }
        for field in row.select(".views-field"):
            for cls in field.get("class", []):
                name = cls.removeprefix("views-field-field-")
                if name != cls and name in FIELDS:
                    course[FIELDS[name]] = field_text(field)
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
    """Polite fetcher: checks robots.txt, waits between requests and caches pages."""

    def __init__(self, cache_dir):
        self.cache = Path(cache_dir) / "uoft"
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
        url = requests.Request("GET", SEARCH, params=params).prepare().url
        if self.robots is None:
            self.robots = RobotFileParser(BASE + "/robots.txt")
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


def fetch_courses(subjects, cache_dir):
    """All courses for the given subject codes, like ["CSC", "MAT", "STA"]."""
    fetcher = Fetcher(cache_dir)
    found = {}
    for subject in subjects:
        first = fetcher.get({"course_keyword": subject, "page": 0})
        pages = [first] + [
            fetcher.get({"course_keyword": subject, "page": p}) for p in range(1, last_page(first) + 1)
        ]
        for html in pages:
            for course in parse_page(html):
                # The keyword search also finds other subjects that mention this one.
                if course["code"].startswith(subject):
                    found[course["code"]] = course
        print(f"  {subject}: {sum(c.startswith(subject) for c in found)} courses from {len(pages)} pages")
    return list(found.values())
