import json
import os
from pathlib import Path

import pytest

from loaders.schools.uoft_timetable import TimetableChanged, academic_year, parse_course

FIXTURES = Path(__file__).parent / "fixtures" / "timetable"
ARTSC = json.loads((FIXTURES / "ARTSC.json").read_text())


def by_code(code, term):
    return next(c for c in ARTSC["courses"] if c["code"] == code and c["sectionCode"] == term)


def test_parse_course_times_and_cancelled_sections():
    code, term, sections = parse_course(by_code("CSC207H1", "F"))
    assert (code, term) == ("CSC207H1", "F")
    assert [s["name"] for s in sections] == ["LEC0101", "LEC0201"]  # LEC9999 is cancelled
    assert sections[0]["times"] == [{"day": 1, "start": 600, "end": 720}]  # Monday 10:00 to 12:00


def test_academic_year():
    assert academic_year("20269") == "2026-2027"
    assert academic_year("20271") == "2026-2027"


def test_changed_api_is_caught():
    broken = dict(by_code("CSC207H1", "F"))
    del broken["sections"]
    with pytest.raises(TimetableChanged):
        parse_course(broken)


DB = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(not DB, reason="set TEST_DATABASE_URL to run database tests")
def test_big_drop_is_refused():
    import psycopg

    from loaders.load_timetable import save_division

    with psycopg.connect(DB) as conn:
        conn.execute("delete from timetable_runs where source = 'TEST'")
        conn.execute("insert into timetable_runs (source, academic_year, courses) values ('ARTSC', '1999-2000', 100)")
        conn.commit()
        with pytest.raises(TimetableChanged, match="down from 100"):
            save_division(conn, "ARTSC", "1999-2000", ARTSC["courses"], min_ratio=0.5)
        conn.rollback()
        conn.execute("delete from timetable_runs where academic_year = '1999-2000'")
        conn.commit()
