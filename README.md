# Trajectory

Find the internships that fit you. Get the courses that launch you there.

[![Tests](https://github.com/cchryx/trajectory/actions/workflows/tests.yml/badge.svg)](https://github.com/cchryx/trajectory/actions/workflows/tests.yml)
[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Upload your resume. Trajectory ranks open internships by fit and lists the skills you are missing for each one. Then it finds courses at your university that teach those skills, with their prerequisite chains.

Live at [trajectory-web.onrender.com](https://trajectory-web.onrender.com). Open source: add your school, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

| Part | What | Status |
|---|---|---|
| 1 | Job finder: resume upload, fit score, missing skills | Built |
| 2 | Course finder: UofT courses, hybrid search, prerequisite graph | Built |
| 2b | Course planner: plan each year, terms, section times, clash checks | Built |
| 3 | Live on Render | Live |
| 4 | Open source: more schools and job sources | Open for contributions |

## How it works

1. A daily job pulls open internships for every term from the [SimplifyJobs list](https://github.com/SimplifyJobs/Summer2027-Internships) into Supabase.
2. It fetches full descriptions from Greenhouse, Lever and Ashby job boards where they are public.
3. Each posting gets skill tags and a 384-number vector (fastembed, `BAAI/bge-small-en-v1.5`).
4. A monthly job loads every course from every UofT calendar, grouped as school > campus > faculty: St. George (Arts & Science, Engineering), Mississauga (UTM) and Scarborough (UTSC). Each course keeps its breadth requirements. Prerequisites are saved in one shared and/or format, so any school can be added.
5. When you upload a resume, the API turns it into a vector and finds the 50 closest postings.
6. Each one is scored: `fit = 0.6 × meaning match + 0.4 × skill overlap`. The top 20 are returned with missing skills and courses that teach them.
7. Course search mixes keyword search and meaning search, merged with reciprocal rank fusion.
8. A weekly job loads the UofT Timetable Builder: which term each course runs in (Fall, Winter or full year) and each section's times.
9. The planner page checks your plan: prerequisites done in an earlier term, the right term, time clashes, exclusions and credit load. The plan is saved in the page link, not in the database.

Your resume is read in memory and never saved or logged. Only daily counts of searches are stored.

## Repo layout

```
db/          SQL for the database tables (run in order)
trajectory/  Shared Python code: skills, vectors, prerequisites, matching, course search
loaders/     Jobs that fill the database (run daily, weekly and monthly by GitHub Actions)
  schools/   One course scraper per school
api/         FastAPI matching API
web/         Next.js website
evals/       Test sets and the script that measures search quality
tests/       Automated tests
```

## Steps to launch

Do these once, in order.

### 1. Update the database

1. Open Supabase > SQL Editor.
2. Paste and run `db/002_trajectory.sql`. It adds 3 columns the loaders need, the course tables and the indexes.
3. Paste and run `db/003_campuses.sql`. It adds campuses.
4. Paste and run `db/004_faculties.sql`. It adds faculties and breadth requirements.
5. Paste and run `db/005_timetable.sql`. It adds terms and section times for the planner.

All these files are safe to run twice.

### 2. Rename the GitHub repo (optional)

1. On GitHub, open the repo > Settings > General > Repository name. Change it to `trajectory`.
2. GitHub redirects the old address, so nothing breaks.
3. On your computer: `git remote set-url origin https://github.com/cchryx/trajectory.git`

### 3. Fill the database

1. Push the code to GitHub.
2. Open Actions > Daily job refresh > Run workflow. This loads jobs and makes the vectors. The first run downloads the model (about 70 MB).
3. Open Actions > Course refresh > Run workflow. This loads every UofT course from all 4 calendars. It takes about 6 minutes, because it waits 1 second between pages.
4. Open Actions > Timetable refresh > Run workflow. This loads terms and section times. It takes about 7 minutes. It runs again every Monday.

### 4. Deploy on Render

1. In Render: New > Blueprint > pick this repo. Render reads `render.yaml` and creates two services.
2. Fill in the values it asks for:
   - `trajectory-api` > `DATABASE_URL`: your Supabase Session pooler string.
   - `trajectory-web` > `NEXT_PUBLIC_API_URL`: the API address, for example `https://trajectory-api.onrender.com`.
   - `trajectory-api` > `WEB_ORIGIN`: the website address, for example `https://trajectory-web.onrender.com`.
3. After you set `NEXT_PUBLIC_API_URL`, redeploy the website. The address is built into the page.
4. Open the website and try your resume.

The free plan sleeps after 15 minutes without visits. The first search after that takes about a minute.

### 5. Measure quality

1. Write 10 test resumes as `.txt` files (yours, plus friends' with names removed).
2. For each, pick 5 posting ids a recruiter would call a good fit, then add it:
   `python -m evals.run_evals --add-job resumes/jane.txt id1,id2,id3,id4,id5`
3. Check the 30 course questions in `evals/course_questions.json` against the calendar. Fix any course codes that are wrong.
4. Run `python -m evals.run_evals`. Goals: 3 of 5 jobs in the top 10, and hybrid course search beats keyword and vector alone.
5. To tune the fit score, set `FIT_W_MEANING` (default 0.6) and run the evals again.

## Run it on your computer

Contributors: follow [CONTRIBUTING.md](CONTRIBUTING.md). It uses a local Docker database and sample data, with no accounts needed.

The steps below are for the live setup, with Supabase. You need Python 3.12 and Node 22.

```bash
cp .env.example .env              # paste your Supabase connection string
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Loaders (run from the repo root)
python -m loaders.load_postings
python -m loaders.load_descriptions
python -m loaders.tag_skills
python -m loaders.embed_postings
python -m loaders.load_courses                    # all UofT calendars, about 6 minutes
python -m loaders.load_courses --faculty uoft-utm --subjects PHY,CHM   # just part of one

# API on http://localhost:8000
uvicorn api.main:app --reload

# Website on http://localhost:3000 (second terminal)
cd web
cp .env.example .env.local
npm install
npm run dev
```

## Tests

`pytest` runs the parser tests. The API tests also need a test database with pgvector:

```bash
TEST_DATABASE_URL=postgresql://... EMBEDDER=hash pytest
```

`EMBEDDER=hash` uses fake vectors, so tests need no model download. GitHub Actions runs everything on each push (see `.github/workflows/tests.yml`).

## Add a university, campus or faculty

Full steps are in [CONTRIBUTING.md > Add your school](CONTRIBUTING.md#add-your-school).

Courses are grouped as school > campus > faculty. Each faculty has its own calendar.

| Faculty id | Campus | Calendar |
|---|---|---|
| `uoft-artsci` | St. George | Faculty of Arts & Science |
| `uoft-eng` | St. George | Faculty of Applied Science & Engineering |
| `uoft-utm` | Mississauga (UTM) | UTM Academic Calendar |
| `uoft-utsc` | Scarborough (UTSC) | UTSC Academic Calendar |

- Another UofT faculty on the same website system: add one `Calendar(...)` line to `CALENDARS` in `loaders/schools/uoft.py`.
- Another school: copy `loaders/schools/_template.py`, fill it in, add its code format to `trajectory/codes.py`, and add the module to `SCHOOLS` in `loaders/schools/__init__.py`.

Then run `python -m loaders.load_courses --faculty <id>`. No table or search changes are needed.

## When UofT changes their website

UofT can change their calendar or timetable site at any time. The loaders are built to fail safely.

What the timetable loader does:

1. It checks every response has the fields it needs. If a field is missing, it stops with `TimetableChanged`.
2. It compares the course count to the last run. If a division drops below half, it refuses to save.
3. When it stops, the old data stays in the database. The website keeps working.
4. The GitHub Action fails. GitHub emails you.

What to do when you get that email:

1. Open the failed run in Actions and read the error. It names the missing field or the drop.
2. Open the UofT site in your browser. Press F12 > Network and find the new request.
3. Fix the code:
   - Timetable: `loaders/schools/uoft_timetable.py`. The API address, request body and field names are at the top.
   - Calendar: `loaders/schools/uoft.py`. The page addresses and HTML class names are in `CALENDARS` and `parse_page`.
4. Save one real response as a test file in `tests/fixtures/` and run the tests.
5. Run the Action again.

If UofT really did remove many courses, run Timetable refresh with `min_ratio` set to `0`. That turns the drop check off for one run.

If the timetable is down for a long time, the planner still works. It shows prerequisites and uses the last saved terms and times.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/filters` | Terms, role types, schools and campuses for the menus |
| POST | `/match` | Form data: `file` (PDF, up to 2 MB) or `text`, plus optional `country`, `term`, `category`, `school` |
| GET | `/courses/search?q=...&campus=uoft-stg` | Course search. Optional: `faculty`, `breadth`, `year`, `mode`. With no `q`, lists every course that matches the filters |
| GET | `/planner/courses?ids=uoft:CSC148H1,uoft:CSC207H1` | Planner details: prerequisites, exclusions, terms and section times |
| GET | `/courses/{id}` | One course, like `uoft:CSC207H1`, with its prerequisite graph and what it unlocks |

## Contributing

Pull requests are welcome. The most useful ones add a school, a job source or better skill tags. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems as in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). You can use, change and share the code, as long as you keep the license notice.

## Credits

Job data comes from the [SimplifyJobs internship list](https://github.com/SimplifyJobs/Summer2027-Internships). Every result links back to the original posting. Course data comes from the [UofT Arts & Science calendar](https://artsci.calendar.utoronto.ca).
