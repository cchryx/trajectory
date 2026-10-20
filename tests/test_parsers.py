from pathlib import Path

from loaders.schools.uoft import calendar_year, last_page, parse_page
from trajectory.prereqs import codes, parse, to_groups
from trajectory.skills import find_skills

FIXTURE = Path(__file__).parent / "fixtures" / "uoft_csc_page.html"


# Skills ------------------------------------------------------------------


def test_skills_in_a_list():
    assert find_skills("Experience with Python, Go, and Rust.") == ["Go", "Python", "Rust"]


def test_skills_ignore_normal_words():
    assert find_skills("You will react to feedback and excel at teamwork. Go above and beyond.") == []


# Prerequisites -------------------------------------------------------------


def test_options_and_required():
    tree = parse("CSC236H1/ CSC240H1; STA237H1/ STA247H1")
    assert tree == {"and": [{"or": ["CSC236H1", "CSC240H1"]}, {"or": ["STA237H1", "STA247H1"]}]}
    assert to_groups(tree) == [["CSC236H1", "CSC240H1"], ["STA237H1", "STA247H1"]]


def test_words_are_ignored():
    tree = parse("60% or higher in CSC148H1/ 60% or higher in CSC111H1")
    assert tree == {"or": ["CSC148H1", "CSC111H1"]}


def test_brackets_inside_options():
    # MAT137Y1, or both MAT135H1 and MAT136H1
    tree = parse("MAT137Y1/ (MAT135H1, MAT136H1)")
    assert tree == {"or": ["MAT137Y1", {"and": ["MAT135H1", "MAT136H1"]}]}
    assert to_groups(tree) == [["MAT137Y1", "MAT135H1"], ["MAT137Y1", "MAT136H1"]]


def test_no_courses():
    assert parse("Permission of the instructor.") is None
    assert to_groups(None) == []


def test_codes_from_other_campuses():
    assert codes(parse("CSC148H1/ CSC148H5/ CSCA48H3")) == ["CSC148H1", "CSC148H5", "CSCA48H3"]


def test_stray_bracket_does_not_break():
    assert parse("CSC108H1) , CSC148H1") == {"and": ["CSC108H1", "CSC148H1"]}


# UofT calendar page ---------------------------------------------------------


def test_uoft_page():
    courses = {c["code"]: c for c in parse_page(FIXTURE.read_text(), year="2026-2027")}
    assert "CSC148H1" in courses and "CSC311H1" in courses

    c207 = courses["CSC207H1"]
    assert c207["title"] == "Software Design"
    assert c207["year_level"] == 2 and c207["credits"] == 0.5
    assert c207["url"] == "https://artsci.calendar.utoronto.ca/course/csc207h1"
    assert "version control" in c207["description"]
    assert "Java" in find_skills(c207["description"])


def test_uoft_engineering_rule_is_dropped():
    courses = {c["code"]: c for c in parse_page(FIXTURE.read_text())}
    text = courses["CSC263H1"]["prereq_text"]
    assert "STA257H1" in text and "APS105H1" not in text
    assert to_groups(parse(text)) == [
        ["CSC236H1", "CSC240H1", "CSC236H5", "CSCB36H3"],
        ["STA237H1", "STA247H1", "STA255H1", "STA257H1"],
    ]


def test_uoft_csc311_has_four_requirements():
    courses = {c["code"]: c for c in parse_page(FIXTURE.read_text())}
    tree = parse(courses["CSC311H1"]["prereq_text"])
    assert len(tree["and"]) == 4
    assert "MAT136H1" in codes(tree)
    assert courses["CSC311H1"]["recommended"].startswith("( MAT235H1")


def test_uoft_pager_and_year():
    assert last_page(FIXTURE.read_text()) == 2
    from datetime import date

    assert calendar_year(date(2026, 10, 20)) == "2026-2027"
    assert calendar_year(date(2027, 3, 1)) == "2026-2027"
