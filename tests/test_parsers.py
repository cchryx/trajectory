from pathlib import Path

from loaders.schools.uoft import CALENDARS, calendar_year, last_page, parse_page, split_breadth
from trajectory.prereqs import codes, parse, to_groups
from trajectory.skills import find_skills
from trajectory.terms import realistic_terms

FIXTURE = Path(__file__).parent / "fixtures" / "uoft_csc_page.html"


# Skills ------------------------------------------------------------------


def test_skills_in_a_list():
    assert find_skills("Experience with Python, Go, and Rust.") == ["Go", "Python", "Rust"]


def test_skills_ignore_normal_words():
    assert find_skills("You will react to feedback and excel at teamwork. Go above and beyond.") == []


def test_skills_in_course_descriptions():
    assert find_skills("Rotational motion and angular momentum of rigid bodies.", course=True) == []
    assert find_skills("Build web apps with Angular and React.") == ["Angular", "React"]
    assert find_skills("Titrate the solution in a flask. Airflow and solidity of materials.", course=True) == []
    assert find_skills("Types, lambda calculus and type inference.", course=True) == []
    assert find_skills("Readings from Kafka and Borges.", course=True) == []
    assert find_skills("Stream events with Kafka.") == ["Kafka"]


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
    assert c207["url"] == "https://artsci.calendar.utoronto.ca/course/CSC207H1"
    assert c207["campus_id"] == "uoft-stg" and c207["faculty_id"] == "uoft-artsci"
    assert courses["CSC148H1"]["breadth"] == ["The Physical and Mathematical Universes (5)"]
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


# Other UofT calendars ----------------------------------------------------------

CAL = {c.id: c for c in CALENDARS}


def test_engineering_page():
    [c] = parse_page((FIXTURE.parent / "uoft_eng_page.html").read_text(), CAL["uoft-eng"])
    assert c["code"] == "ECE314H1" and c["faculty_id"] == "uoft-eng" and c["campus_id"] == "uoft-stg"
    assert c["credits"] == 0.5 and c["year_level"] == 3
    assert c["prereq_text"].startswith("ECE212H1 and")  # the bold "Prerequisite:" label is skipped
    assert to_groups(parse(c["prereq_text"])) == [["ECE212H1"], ["ECE221H1"], ["ECE231H1"]]
    assert "DC/DC converters" in c["description"]


def test_utm_page():
    [c] = parse_page((FIXTURE.parent / "uoft_utm_page.html").read_text(), CAL["uoft-utm"])
    assert c["code"] == "ANT338H5" and c["title"] == "Laboratory Methods in Biological Anthropology"
    assert c["campus_id"] == "uoft-utm" and c["breadth"] == ["Science"]
    assert parse(c["prereq_text"]) == {"and": [{"or": ["ANT202H5", "ANT203H5"]}, "ANT220H5"]}


def test_utsc_page():
    [c] = parse_page((FIXTURE.parent / "uoft_utsc_page.html").read_text(), CAL["uoft-utsc"])
    assert c["code"] == "CSCB07H3" and c["year_level"] == 2  # B = second year
    assert c["campus_id"] == "uoft-utsc" and c["breadth"] == ["Quantitative Reasoning"]
    assert codes(parse(c["prereq_text"])) == ["CSCA48H3"]


def test_breadth_names_with_commas():
    text = "Thought, Belief and Behaviour (2), Society and its Institutions (3)"
    assert split_breadth(text) == ["Thought, Belief and Behaviour (2)", "Society and its Institutions (3)"]
    assert split_breadth("Arts, Literature and Language") == ["Arts, Literature and Language"]


# Terms ---------------------------------------------------------------------------


def test_realistic_terms():
    from datetime import date

    terms = ["N/A", "Spring 2016", "Summer 2026", "Fall 2026", "Winter 2027", "Summer 2027", "Fall 2029", "Fall 2026"]
    assert realistic_terms(terms, date(2026, 10, 20)) == ["Fall 2026", "Winter 2027", "Summer 2027"]

