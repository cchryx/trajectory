"""Which internship terms to offer in the filter menu.

The job list has some odd values ("N/A", "Spring 2016"). We keep only real terms
like "Fall 2026" that have not ended yet and start within the next two years.
"""

import re
from datetime import date

TERM = re.compile(r"^(Winter|Spring|Summer|Fall) (\d{4})$")
SEASONS = ["Winter", "Spring", "Summer", "Fall"]
LAST_MONTH = {"Winter": 4, "Spring": 6, "Summer": 8, "Fall": 12}  # month the term ends
YEARS_AHEAD = 2


def realistic_terms(terms, today=None):
    """Keep current and upcoming terms, sorted by date: Fall 2026, Winter 2027, ..."""
    today = today or date.today()
    keep = []
    for term in set(terms):
        m = TERM.match(term or "")
        if not m:
            continue
        season, year = m.group(1), int(m.group(2))
        ended = (year, LAST_MONTH[season]) < (today.year, today.month)
        too_far = year > today.year + YEARS_AHEAD
        if not ended and not too_far:
            keep.append((year, SEASONS.index(season), term))
    return [t for _, _, t in sorted(keep)]
