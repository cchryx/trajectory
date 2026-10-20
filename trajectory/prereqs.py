"""Turn prerequisite text into a shared and/or format that works for any school.

Rules, from how course calendars write them:
- "/" or "or" means options: any one of them is enough.
- "," ";" or "and" means all of them are needed.
- "/" binds tighter than "," so "A/B, C" means (A or B) and C.
- Brackets group: "A/ (B, C)" means A, or both B and C.
- Words that are not course codes ("60% or higher in", "minimum of 73% in") are ignored.

parse() returns a tree:  "CSC148H1"  |  {"and": [...]}  |  {"or": [...]}  |  None
to_groups() flattens the tree into "and" of "or" groups for the prereqs table:
[["CSC148H1", "CSC111H1"], ["MAT223H1"]] means (CSC148H1 or CSC111H1) and MAT223H1.
"""

import re
from functools import cache
from itertools import product

from trajectory.codes import DEFAULT_SCHOOL, normalize, pattern

MAX_GROUPS = 64


@cache
def _token_re(school_id):
    return re.compile(
        rf"(?P<code>{pattern(school_id)})"
        r"|(?P<open>[(\[])|(?P<close>[)\]])"
        r"|(?P<or>/|\bor\b)|(?P<and>[,;]|\band\b)",
        re.IGNORECASE,
    )


def _tokens(text, school_id=DEFAULT_SCHOOL):
    text = (text or "").replace("​", "")
    out = []
    for m in _token_re(school_id).finditer(text):
        kind = m.lastgroup
        if kind == "code":
            out.append(("code", normalize(m.group())))
        else:
            out.append((kind, None))
    return out


def _combine(op, items):
    flat = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, dict) and op in item:
            flat.extend(item[op])
        elif item not in flat:
            flat.append(item)
    if not flat:
        return None
    return flat[0] if len(flat) == 1 else {op: flat}


class _Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def all_of(self):
        items = [self.one_of()]
        while self.peek() == "and":
            self.take()
            items.append(self.one_of())
        return _combine("and", items)

    def one_of(self):
        items = [self.atom()]
        while self.peek() == "or":
            self.take()
            items.append(self.atom())
        return _combine("or", items)

    def atom(self):
        kind = self.peek()
        if kind == "code":
            return self.take()[1]
        if kind == "open":
            self.take()
            inner = self.all_of()
            if self.peek() == "close":
                self.take()
            return inner
        return None  # a separator or the end: nothing here


def parse(text, school_id=DEFAULT_SCHOOL):
    """Parse prerequisite text into a tree. Returns None when it names no courses."""
    p = _Parser(_tokens(text, school_id))
    parts = []
    while p.peek() is not None:
        parts.append(p.all_of())
        if p.peek() is not None:
            p.take()  # skip a stray ")" and keep going
    return _combine("and", parts)


def to_groups(tree):
    """Flatten a tree into a list of "or" groups that are all required."""
    if tree is None:
        return []
    if isinstance(tree, str):
        return [[tree]]
    if "and" in tree:
        groups = [g for child in tree["and"] for g in to_groups(child)]
    else:
        # (a and b) or c  ==  (a or c) and (b or c)
        choices = [to_groups(child) for child in tree["or"]]
        groups = []
        for combo in product(*choices):
            group = []
            for part in combo:
                group.extend(c for c in part if c not in group)
            groups.append(group)
            if len(groups) >= MAX_GROUPS:
                break
    return _simplify(groups)


def _simplify(groups):
    """Drop repeated groups and groups that contain a smaller group (they add nothing)."""
    out = []
    for g in sorted(groups, key=len):
        if not any(set(o) <= set(g) for o in out):
            out.append(g)
    return out


def codes(tree):
    """Every course code in a tree, in order, without repeats."""
    if tree is None:
        return []
    if isinstance(tree, str):
        return [tree]
    seen = []
    for child in next(iter(tree.values())):
        for c in codes(child):
            if c not in seen:
                seen.append(c)
    return seen
