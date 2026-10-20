"""API tests against a real Postgres with pgvector.

They run only when TEST_DATABASE_URL is set, and use the fake embedder (no model download).
Load data first:  python -m loaders.load_postings && python -m loaders.tag_skills &&
                  python -m loaders.embed_postings, and load_courses with the fixture.
"""

import io
import os

import pytest

DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB, reason="set TEST_DATABASE_URL to run API tests")

RESUME = """Jane Student
Computer Science, University of Toronto
Skills: Python, Java, SQL, Git, Docker, React, machine learning, PyTorch
Experience: Software engineering intern. Built REST APIs in Python and FastAPI.
Projects: trained a computer vision model with PyTorch and OpenCV.
"""


@pytest.fixture(scope="module")
def client():
    os.environ["DATABASE_URL"] = DB
    os.environ["EMBEDDER"] = "hash"
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:
        yield c


def make_pdf(text):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    y = 800
    for line in text.splitlines():
        pdf.drawString(50, y, line)
        y -= 16
    pdf.save()
    return buf.getvalue()


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_filters(client):
    data = client.get("/filters").json()
    assert data["open_postings"] > 0
    assert any("2027" in t for t in data["terms"])


def test_match_pdf(client):
    res = client.post("/match", files={"file": ("resume.pdf", make_pdf(RESUME), "application/pdf")})
    assert res.status_code == 200, res.text
    data = res.json()
    assert {"Python", "Java", "PyTorch"} <= set(data["resume_skills"])
    jobs = data["jobs"]
    assert 0 < len(jobs) <= 20
    fits = [j["fit"] for j in jobs]
    assert fits == sorted(fits, reverse=True)
    for j in jobs:
        assert set(j["matched_skills"]) <= set(data["resume_skills"])
        assert not set(j["missing_skills"]) & set(data["resume_skills"])


def test_match_text_with_filter(client):
    res = client.post("/match", data={"text": RESUME, "country": "CA"})
    assert res.status_code == 200
    assert res.json()["jobs"]


def test_rejects_bad_uploads(client):
    assert client.post("/match").status_code == 400
    res = client.post("/match", files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert res.status_code == 415
    big = b"%PDF" + b"0" * (2 * 1024 * 1024)
    assert client.post("/match", files={"file": ("x.pdf", big, "application/pdf")}).status_code == 413


def test_course_search_and_detail(client):
    for mode in ("keyword", "vector", "hybrid"):
        res = client.get("/courses/search", params={"q": "software design java", "mode": mode})
        assert res.status_code == 200
        ids = [r["id"] for r in res.json()["results"]]
        assert "uoft:CSC207H1" in ids, (mode, ids)

    assert client.get("/courses/search", params={"q": "CSC 263"}).json()["results"][0]["code"] == "CSC263H1"

    course = client.get("/courses/uoft:CSC311H1").json()
    assert course["title"] == "Introduction to Machine Learning"
    froms = {e["from"] for e in course["graph"]["edges"]}
    assert {"uoft:CSC207H1", "uoft:CSC148H1"} <= froms  # two steps back
    assert client.get("/courses/uoft:CSC207H1").json()["unlocks"][0]["code"] == "CSC311H1"
    assert client.get("/courses/uoft:NOPE").status_code == 404
