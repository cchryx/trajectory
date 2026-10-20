"""Loader 4: turn every open posting into a 384-number vector.

Only embeds postings whose text changed since last time (checked with an md5 hash),
so a daily run is fast. Run it after tag_skills, because the skills are part of the text.

Run from the repo root:  python -m loaders.embed_postings
"""

import hashlib

from trajectory.db import connect
from trajectory.embed import embed_passages, to_pg

BATCH = 128

TODO_SQL = """
select id, title, company, description, skills, embed_hash
from postings
where active
"""

SAVE_SQL = """
update postings set embedding = %(vec)s::vector, embed_hash = %(hash)s
where id = %(id)s
"""


def posting_text(title, company, description, skills):
    """The text a posting is judged on. Postings with no description still have a title and skills."""
    parts = [f"{title} at {company}."]
    if skills:
        parts.append("Skills: " + ", ".join(skills) + ".")
    if description:
        parts.append(description)
    return "\n".join(parts)


def main():
    with connect() as conn, conn.cursor() as cur:
        cur.execute(TODO_SQL)
        todo = []
        for posting_id, title, company, description, skills, old_hash in cur.fetchall():
            text = posting_text(title, company, description, skills)
            new_hash = hashlib.md5(text.encode()).hexdigest()
            if new_hash != old_hash:
                todo.append((posting_id, text, new_hash))
        print(f"{len(todo)} postings need a new vector.")

        for start in range(0, len(todo), BATCH):
            batch = todo[start : start + BATCH]
            vectors = embed_passages([text for _, text, _ in batch])
            cur.executemany(
                SAVE_SQL,
                [{"id": pid, "vec": to_pg(vec), "hash": h} for (pid, _, h), vec in zip(batch, vectors)],
            )
            conn.commit()
            print(f"  embedded {min(start + BATCH, len(todo))} of {len(todo)}")

    print("Done.")


if __name__ == "__main__":
    main()
