# Contributing to Trajectory

Thanks for helping. Trajectory is open source under the [MIT license](LICENSE).

The most useful things to add:

1. **Your school's courses.** Right now only UofT is in. Waterloo, McMaster, UBC, anyone.
2. **More job sources.** Right now jobs come from the SimplifyJobs list.
3. **Better skill tags.** Skills that are missing, or tagged on the wrong things.
4. **Bug fixes.** Anything that looks wrong on the site.

Not sure where to start? Look at issues labelled `good first issue`, or open an issue and ask.

## Set up on your computer

You need Python 3.12, Node 22 and Docker. You do not need a Supabase account.

```bash
git clone https://github.com/cchryx/trajectory.git
cd trajectory

# 1. Database (runs the SQL in db/ the first time)
docker compose up -d

# 2. Python
cp .env.example .env               # already points at the Docker database
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 3. Sample data: real jobs, a few sample courses, a sample timetable
python -m loaders.dev_seed         # add EMBEDDER=hash to skip the 70 MB model download

# 4. API on http://localhost:8000
uvicorn api.main:app --reload

# 5. Website on http://localhost:3000 (second terminal)
cd web
cp .env.example .env.local
npm install
npm run dev
```

To start the database again from empty: `docker compose down -v`, then `docker compose up -d`.

## Run the checks

Run these before you open a pull request. GitHub runs the same ones.

```bash
# Python tests (uses the Docker database)
TEST_DATABASE_URL=postgresql://postgres:pg@localhost:5433/trajectory EMBEDDER=hash pytest

# Website
cd web
npm run lint
npm run build
```

## Add your school

Example: someone at Waterloo adds Waterloo courses.

Courses are grouped as school > campus > faculty. Every school plugs into the same loader, search and planner. You write one file that reads your school's course list. The rest is shared.

1. **Find the data.** Look for an official API or open data first. Waterloo has the [Open Data API](https://uwaterloo.ca/open-data/) with a [courses endpoint](https://openapi.data.uwaterloo.ca/api-docs/index.html). It needs a free API key. If there is no API, read the public course calendar pages. Check `robots.txt` first.
2. **Copy the template.** Copy `loaders/schools/_template.py` to `loaders/schools/uwaterloo.py`.
3. **Fill in the ids.**
   - School id: short and lowercase, like `uwaterloo`.
   - Campus id: starts with the school id and a dash, like `uwaterloo-main`.
   - Faculty id: like `uwaterloo-math`. If the school has one calendar for everything, make one faculty.
4. **Write `fetch_courses()`.** It returns a list of courses in the shared shape. The template shows every field.
   - Save codes without spaces: `CS 135` becomes `CS135`.
   - Rewrite prerequisite wording into the shared format. `/` or `or` means any one. `,` `;` or `and` means all. For example, `One of CS 136, CS 146` becomes `CS136/CS146`.
   - Cache every response on disk. Wait at least 1 second between requests.
5. **Add your code format** to `trajectory/codes.py`, like `"uwaterloo": r"..."`. Test it on real prerequisite text. Make sure it does not match words like `or 146`.
6. **Register the school.** Add your module to `SCHOOLS` in `loaders/schools/__init__.py`.
7. **Add a test.** Save one real response in `tests/fixtures/`. Add a test that parses it, like the UofT tests in `tests/test_parsers.py`. `tests/test_schools.py` checks your ids for you.
8. **Try it.**
   ```bash
   python -m loaders.load_courses --faculty uwaterloo-math --subjects CS,MATH
   ```
   Then pick your school in the Courses page.
9. **Open a pull request.** If your school needs an API key, say so in the PR. The maintainer adds it as a GitHub secret.

What works for a new school right away: course search, the prerequisite graph, courses suggested for missing job skills, and the planner's prerequisite and exclusion checks.

What is UofT only for now: term and section times in the planner. They come from `loaders/load_timetable.py`. To add them for your school, write a module like `loaders/schools/uoft_timetable.py` that fills the `offerings` table. Without it, the planner still works. It just skips the term and clash checks.

## Add a job source

Jobs come from `loaders/load_postings.py`. Each posting is one row in the `postings` table. The `id` must be unique across sources, so start it with the source name, like `wwcode:1234`.

1. Write a loader like `load_postings.py` that maps the source into the same columns.
2. Mark postings `active = false` when they close. Do not delete them.
3. If the source has full descriptions, fill `description`. If not, `load_descriptions.py` tries the company's job board.
4. Add it to `.github/workflows/daily.yml`.
5. Only use sources that allow it. Check their terms.

## Fix skill tags

Skills live in `trajectory/skills.py`. A skill can be wrong in two ways:

- **Missing:** add it to the right group with the words that mean it.
- **Tagged on the wrong thing:** for example "Angular" on a physics course. Add a rule, then add a test in `tests/test_parsers.py` with the exact text that was wrong.

## Pull requests

1. Fork the repo and make a branch: `git checkout -b add-waterloo`.
2. Keep one change per pull request.
3. Write commit messages that say what changed and why.
4. Make sure the checks above pass.
5. Fill in the pull request template.

## Rules

- Be kind. See the [Code of Conduct](CODE_OF_CONDUCT.md).
- Never commit secrets: passwords, API keys, `.env` files. See [SECURITY.md](SECURITY.md).
- Never save resumes. The API reads them in memory only. Keep it that way.
- Be polite to school and job websites: official APIs first, 1 request per second, cache everything.
