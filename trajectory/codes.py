"""Course code formats, one per school.

Every school writes course codes its own way:
- UofT: CSC148H1, CSCA48H3, MAT137Y1
- Waterloo would be: CS 135, MATH 137, STAT 230

The prerequisite parser and the planner use these patterns to find codes in text.
Codes are saved without spaces and in capitals, so "CS 135" is saved as "CS135".

To add a school, add one line to PATTERNS with its school id.
"""

import re

PATTERNS = {
    "uoft": r"[A-Z]{3}[A-Z0-9]\d{2}[HY]\d",
}
DEFAULT_SCHOOL = "uoft"


def pattern(school_id=DEFAULT_SCHOOL):
    """The code pattern for a school, as a regex string."""
    try:
        return PATTERNS[school_id]
    except KeyError:
        raise KeyError(f"No course code pattern for school '{school_id}'. Add one to trajectory/codes.py.") from None


def normalize(code):
    """'cs 135' -> 'CS135'."""
    return re.sub(r"\s+", "", code).upper()


def find_codes(text, school_id=DEFAULT_SCHOOL):
    """Every course code in some text, normalized, in order, without repeats."""
    found = re.findall(pattern(school_id), (text or "").replace("​", ""), re.IGNORECASE)
    return list(dict.fromkeys(normalize(c) for c in found))
