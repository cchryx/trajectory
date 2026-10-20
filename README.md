# Trajectory

Find the internships that fit you. Get the courses that launch you there.

Upload your resume. Trajectory ranks open internships by fit and lists the skills you are missing for each one. Then it finds courses at your university that teach those skills, with their prerequisite chains.

## Status

| Part | What | Status |
|---|---|---|
| 1 | Job finder: resume upload, fit score, missing skills | Built |
| 2 | Course finder: UofT courses, hybrid search, prerequisite graph | Built |
| 3 | Live on Render | To do (steps below) |

## How it works

1. A daily job pulls open internships for every term from the [SimplifyJobs list](https://github.com/SimplifyJobs/Summer2027-Internships) into Supabase.
2. It fetches full descriptions from Greenhouse, Lever and Ashby job boards where they are public.
3. Each posting gets skill tags and a 384-number vector (fastembed, `BAAI/bge-small-en-v1.5`).
4. A monthly job loads courses by school and campus. It starts with University of Toronto, St. George campus (Arts & Science: CSC, MAT, STA). Prerequisites are saved in one shared and/or format, so any school can be added.
5. When you upload a resume, the API turns it into a vector and finds the 50 closest postings.
6. Each one is scored: `fit = 0.6 × meaning match + 0.4 × skill overlap`. The top 20 are returned with missing skills and courses that teach them.
7. Course search mixes keyword search and meaning search, merged with reciprocal rank fusion.

Your resume is read in memory and never saved or logged. Only daily counts of searches are stored.

## Repo layout

```
db/          SQL for the database tables (run in order)
trajectory/  Shared Python code: skills, vectors, prerequisites, matching, course search
loaders/     Jobs that fill the database (run daily and monthly by GitHub Actions)
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
3. Paste and run `db/003_campuses.sql`. It adds campuses, so courses are grouped by school and campus.

Both files are safe to run twice.

### 2. Rename the GitHub repo (optional)

1. On GitHub, open the repo > Settings > General > Repository name. Change it to `trajectory`.
2. GitHub redirects the old address, so nothing breaks.
3. On your computer: `git remote set-url origin https://github.com/cchryx/trajectory.git`

### 3. Fill the database

1. Push the code to GitHub.
2. Open Actions > Daily job refresh > Run workflow. This loads jobs and makes the vectors. The first run downloads the model (about 70 MB).
3. Open Actions > Course refresh > Run workflow. This loads UofT CSC, MAT and STA courses. It takes a few minutes, because it waits 1 second between pages.

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

You need Python 3.12 and Node 22.

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
python -m loaders.load_courses --subjects CSC,MAT,STA

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

## Add a university or campus

Courses are grouped by school, then campus. Each campus calendar gets its own module.

1. Add a module in `loaders/schools/`, like `utm.py` (UofT Mississauga) or `waterloo.py`, with `SCHOOL`, `CAMPUS` and `fetch_courses()`. It must return the shared course shape (see `loaders/schools/__init__.py`). Campuses of one school share the same `SCHOOL`.
2. List it in `CAMPUSES` in `loaders/schools/__init__.py`.
3. Run `python -m loaders.load_courses --campus uoft-utm --subjects CSC,MAT`.

No table or search changes are needed.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/filters` | Terms, role types, schools and campuses for the menus |
| POST | `/match` | Form data: `file` (PDF, up to 2 MB) or `text`, plus optional `country`, `term`, `category`, `school` |
| GET | `/courses/search?q=...&campus=uoft-stg` | Course search. Optional `mode`: `hybrid`, `keyword` or `vector` |
| GET | `/courses/{id}` | One course, like `uoft:CSC207H1`, with its prerequisite graph and what it unlocks |

## Credits

Job data comes from the [SimplifyJobs internship list](https://github.com/SimplifyJobs/Summer2027-Internships). Every result links back to the original posting. Course data comes from the [UofT Arts & Science calendar](https://artsci.calendar.utoronto.ca).
