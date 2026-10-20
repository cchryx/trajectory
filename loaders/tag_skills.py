"""Loader 3: tag each open posting with the skills its title and description mention.

Also saves the skill list into the skills table.
Re-tags every open posting each run, so changes to skills.py apply to old postings too.
"""

from collections import Counter

from trajectory.db import connect
from trajectory.skills import SKILLS, find_skills

SAVE_SKILL_SQL = """
insert into skills (name, aliases, kind)
values (%s, %s, %s)
on conflict (name) do update set aliases = excluded.aliases, kind = excluded.kind
"""

SAVE_TAGS_SQL = """
update postings set skills = %(skills)s
where id = %(id)s and skills is distinct from %(skills)s
"""


def main():
    with connect() as conn, conn.cursor() as cur:
        # 1. Save the skill list.
        cur.executemany(SAVE_SKILL_SQL, [(n, a, k) for n, k, a in SKILLS])

        # 2. Find skills in every open posting.
        cur.execute("select id, title, description from postings where active")
        rows = []
        counts = Counter()
        tagged = 0
        for posting_id, title, description in cur.fetchall():
            found = find_skills(f"{title}\n{description or ''}")
            rows.append({"id": posting_id, "skills": found})
            counts.update(found)
            tagged += bool(found)

        # 3. Save the tags. Rows that did not change are skipped by the SQL.
        cur.executemany(SAVE_TAGS_SQL, rows)

    print(f"Saved {len(SKILLS)} skills. Tagged {tagged} of {len(rows)} open postings.")
    print("Top 15 skills:")
    for name, n in counts.most_common(15):
        print(f"  {name:<20} {n}")


if __name__ == "__main__":
    main()