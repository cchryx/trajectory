"""Loader 1: pull internships from the SimplifyJobs list into Supabase.

- Keeps every visible listing, for any term (summer, fall, winter, spring).
- Inserts new postings and updates changed ones by id.
- Marks postings as closed (active = false) when they are closed or gone from the list.
- Never touches description, skills or embedding. Later loaders fill those.

Run from the repo root:  python -m loaders.load_postings
Needs DATABASE_URL in the environment or in a .env file at the repo root.
"""

from datetime import datetime, timezone

import requests

from trajectory.db import connect

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "dev/.github/scripts/listings.json"
)

UPSERT_SQL = """
insert into postings (id, company, title, url, locations, country, terms, category, active, date_posted, updated_at)
values (%(id)s, %(company)s, %(title)s, %(url)s, %(locations)s, %(country)s, %(terms)s, %(category)s, %(active)s, %(date_posted)s, now())
on conflict (id) do update set
  company     = excluded.company,
  title       = excluded.title,
  url         = excluded.url,
  locations   = excluded.locations,
  country     = excluded.country,
  terms       = excluded.terms,
  category    = excluded.category,
  active      = excluded.active,
  date_posted = excluded.date_posted,
  updated_at  = now()
where (postings.company, postings.title, postings.url, postings.locations, postings.country,
       postings.terms, postings.category, postings.active, postings.date_posted)
   is distinct from
      (excluded.company, excluded.title, excluded.url, excluded.locations, excluded.country,
       excluded.terms, excluded.category, excluded.active, excluded.date_posted)
"""


def fetch_listings():
    res = requests.get(LISTINGS_URL, timeout=60)
    res.raise_for_status()
    return res.json()


CA_WORDS = ("Canada", "Toronto", "Vancouver", "Montreal", "Montréal", "Waterloo",
            "Ottawa", "Calgary", "Edmonton", "Kitchener", "Mississauga", "Markham")
CA_PROVINCES = {"ON", "BC", "QC", "AB", "MB", "NS", "SK", "NB", "NL", "PE"}
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE",
    "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
    "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}
US_NAMES = {
    "USA", "United States", "Remote in USA", "Remote in US", "NYC", "SF", "LA",
    "South SF", "Alabama", "Arizona", "California", "Colorado", "Florida", "Georgia",
    "Illinois", "Iowa", "Massachusetts", "Michigan", "Minnesota", "New Jersey",
    "New York", "North Carolina", "Ohio", "Oregon", "Pennsylvania", "Texas",
    "Utah", "Virginia", "Washington",
}


def countries(locations):
    found = set()
    for loc in locations:
        loc = loc.strip()
        last = loc.rsplit(", ", 1)[-1]  # "Austin, TX" -> "TX"
        if last in CA_PROVINCES or any(w in loc for w in CA_WORDS):
            found.add("CA")
        elif last in US_STATES or loc in US_NAMES or last in US_NAMES:
            found.add("US")
    return sorted(found) or ["other"]


def to_row(item):
    posted = item.get("date_posted")
    return {
        "id": str(item["id"]),
        "company": (item.get("company_name") or "").strip(),
        "title": (item.get("title") or "").strip(),
        "url": item.get("url") or "",
        "locations": item.get("locations") or [],
        "country": countries(item.get("locations") or []),
        "terms": item.get("terms") or [],
        "category": item.get("category"),
        "active": bool(item.get("active")),
        "date_posted": datetime.fromtimestamp(posted, tz=timezone.utc) if posted else None,
    }


def keep(item):
    return (
        item.get("is_visible", True)
        and item.get("id")
        and item.get("company_name")
        and item.get("title")
        and item.get("url")
    )


def main():
    items = fetch_listings()
    rows = [to_row(x) for x in items if keep(x)]
    open_ids = [r["id"] for r in rows if r["active"]]
    print(f"Fetched {len(items)} listings. Kept {len(rows)}, {len(open_ids)} open.")

    with connect() as conn, conn.cursor() as cur:
        cur.execute("select id from postings")
        before = {r[0] for r in cur.fetchall()}

        # One batched round trip instead of one per row.
        cur.executemany(UPSERT_SQL, rows)
        added = sum(1 for r in rows if r["id"] not in before)
        updated = cur.rowcount - added

        # Postings that were open before but are no longer open in the list.
        cur.execute(
            "update postings set active = false, updated_at = now() "
            "where active and not (id = any(%s))",
            (open_ids,),
        )
        closed = cur.rowcount

        cur.execute("select count(*) from postings where active")
        open_total = cur.fetchone()[0]

    print(f"Added {added}, updated {updated}, closed {closed}. Open postings now: {open_total}.")


if __name__ == "__main__":
    main()
