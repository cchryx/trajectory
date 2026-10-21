"""Checks every school module follows the shared rules. No network needed."""

import re

import pytest

from loaders.schools import FACULTIES, SCHOOLS
from loaders.schools import _template as template
from trajectory.codes import PATTERNS, find_codes
from trajectory.prereqs import parse

CALENDARS = [*FACULTIES.values(), *template.CALENDARS]


@pytest.mark.parametrize("cal", CALENDARS, ids=lambda c: c.id)
def test_calendar_shape(cal):
    school, campus, faculty = cal.school, cal.campus, cal.faculty
    assert re.fullmatch(r"[a-z0-9]+", school["id"]), "school id: lowercase letters and numbers"
    assert campus["school_id"] == school["id"]
    assert campus["id"].startswith(school["id"] + "-"), "campus id must start with the school id and a dash"
    assert faculty["campus_id"] == campus["id"]
    assert faculty["id"] == cal.id
    assert callable(cal.fetch)


def test_faculty_ids_are_unique():
    ids = [cal.id for school in SCHOOLS for cal in school.CALENDARS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("school", SCHOOLS, ids=lambda s: s.SCHOOL["id"])
def test_school_has_code_pattern(school):
    assert school.SCHOOL["id"] in PATTERNS, "add your course code format to trajectory/codes.py"


def test_find_codes_uoft():
    assert find_codes("CSC207H1, csc148h5 and MAT137Y1", "uoft") == ["CSC207H1", "CSC148H5", "MAT137Y1"]


def test_parse_with_other_school(monkeypatch):
    # A Waterloo style format, to show the parser works with any code pattern.
    monkeypatch.setitem(PATTERNS, "demo", r"\b(?!or\b|and\b)[A-Z]{2,5} ?\d{3}[A-Z]?\b")
    tree = parse("(CS 136 or CS 146) and MATH 135", "demo")
    assert tree == {"and": [{"or": ["CS136", "CS146"]}, "MATH135"]}
