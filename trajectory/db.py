"""Database connection helpers."""

import os
import sys

import psycopg
from dotenv import load_dotenv


def database_url():
    """Return DATABASE_URL from the environment or a .env file at the repo root."""
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL first (in .env or the environment).")
    return url


def connect():
    """Open one connection. Use it in a `with` block so it commits on success."""
    return psycopg.connect(database_url())
