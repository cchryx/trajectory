"""Fill a local database with sample data, so you can run the app in a few minutes.

- Jobs: the real SimplifyJobs list (one download, about 5 MB).
- Courses: a few saved UofT pages from tests/fixtures (no scraping).
- Timetable: a small saved sample from tests/fixtures/timetable.

Run from the repo root, after `docker compose up -d`:
    python -m loaders.dev_seed

Set EMBEDDER=hash to skip the model download (about 70 MB). Search results will be
less useful, but everything runs.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
CACHE = ROOT / ".cache" / "uoft"

# Saved calendar page -> the cache file the UofT loader reads instead of the website.
PAGES = {
    "uoft-artsci": "uoft_csc_page.html",
    "uoft-eng": "uoft_eng_page.html",
    "uoft-utm": "uoft_utm_page.html",
    "uoft-utsc": "uoft_utsc_page.html",
}


def run(*args):
    print("\n$ python -m", " ".join(args))
    subprocess.run([sys.executable, "-m", *args], cwd=ROOT, check=True)


def main():
    for faculty, name in PAGES.items():
        folder = CACHE / faculty
        folder.mkdir(parents=True, exist_ok=True)
        html = (FIXTURES / name).read_text(encoding="utf-8")
        # Drop the "last page" link, so the loader reads only this one page.
        html = "\n".join(line for line in html.splitlines() if "pager__item--last" not in line)
        (folder / "page-0.html").write_text(html, encoding="utf-8")

    run("loaders.load_postings")
    run("loaders.tag_skills")
    run("loaders.embed_postings")
    run("loaders.load_courses")
    run("loaders.load_timetable", "--division", "ARTSC,APSC", "--fixture", str(FIXTURES / "timetable"))
    print("\nDone. Start the API with: uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
