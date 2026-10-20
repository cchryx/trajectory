"""University of Toronto timetable: which term each course runs in, and its section times.

Source: the public Timetable Builder at ttb.utoronto.ca. Its page reads from
https://api.easi.utoronto.ca/ttb, and so do we. We send at most 1 request per second.

UofT can change this API at any time. Everything that depends on its exact shape
is in this file, and every response is checked. If the shape changes, we raise
TimetableChanged instead of saving bad data, and the GitHub Action fails so you get
an email. See "When UofT changes their website" in the README.
"""

import time

import requests

API = "https://api.easi.utoronto.ca/ttb"
HEADERS = {
    "User-Agent": "TrajectoryBot/1.0 (student project; course planner)",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
DELAY = 1.0  # seconds between requests
TIMEOUT = 30
PAGE_SIZE = 20  # the API always returns 20 per page
MAX_PAGES = 400  # safety stop

# Timetable division code -> our faculty id.
DIVISIONS = {
    "ARTSC": "uoft-artsci",
    "APSC": "uoft-eng",
    "ERIN": "uoft-utm",
    "SCAR": "uoft-utsc",
}


class TimetableChanged(RuntimeError):
    """The timetable API answered in a shape we do not understand."""


def _need(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        raise TimetableChanged(f"missing '{key}' in {where}. UofT may have changed the timetable API.")
    return obj[key]


def academic_year(session_code):
    """'20269' (Sept 2026) and '20271' (Jan 2027) -> '2026-2027'."""
    year, month = int(session_code[:4]), int(session_code[4:])
    start = year if month >= 9 else year - 1
    return f"{start}-{start + 1}"


def parse_course(course):
    """One timetable course -> (code, term, sections). Term is 'F', 'S' or 'Y'."""
    code = _need(course, "code", "a course")
    term = _need(course, "sectionCode", code)
    sections = []
    for sec in _need(course, "sections", code) or []:
        if sec.get("cancelInd") == "Y":
            continue
        times = []
        for m in sec.get("meetingTimes") or []:
            start, end = _need(m, "start", code), _need(m, "end", code)
            times.append(
                {
                    "day": _need(start, "day", code),  # 1 = Monday ... 5 = Friday
                    "start": _need(start, "millisofday", code) // 60000,  # minutes after midnight
                    "end": _need(end, "millisofday", code) // 60000,
                }
            )
        sections.append({"name": sec.get("name"), "type": sec.get("teachMethod"), "times": times})
    return code, term, sections


class Client:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last = 0.0

    def _wait(self):
        wait = DELAY - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()

    def sessions(self):
        """Session codes for the current Fall-Winter, like ['20269', '20271', '20269-20271']."""
        self._wait()
        res = self.session.get(f"{API}/current-session", timeout=TIMEOUT)
        res.raise_for_status()
        payload = _need(res.json(), "payload", "current-session")
        codes = [p.get("value") for p in payload if not p.get("header")]
        if not codes or not all(isinstance(c, str) and c[:4].isdigit() for c in codes):
            raise TimetableChanged(f"unexpected session list: {codes}")
        return codes

    def page(self, division, sessions, page):
        body = {
            "courseCodeAndTitleProps": {
                "courseCode": "", "courseTitle": "", "courseSectionCode": "", "searchCourseDescription": True,
            },
            "departmentProps": [], "campuses": [], "sessions": sessions, "requirementProps": [],
            "instructor": "", "courseLevels": [], "deliveryModes": [], "dayPreferences": [],
            "timePreferences": [], "divisions": [division], "creditWeights": [],
            "availableSpace": False, "waitListable": False,
            "page": page, "pageSize": PAGE_SIZE, "direction": "asc",
        }
        self._wait()
        res = self.session.post(f"{API}/getPageableCourses", json=body, timeout=TIMEOUT)
        res.raise_for_status()
        pageable = _need(_need(res.json(), "payload", "getPageableCourses"), "pageableCourse", "payload")
        return _need(pageable, "courses", "pageableCourse"), _need(pageable, "total", "pageableCourse")


def fetch_division(client, division, sessions):
    """Every course listing in one division for the given sessions."""
    first, total = client.page(division, sessions, 1)
    pages = min(MAX_PAGES, -(-total // PAGE_SIZE))
    courses = list(first)
    for p in range(2, pages + 1):
        batch, _ = client.page(division, sessions, p)
        courses.extend(batch)
    return courses, total
