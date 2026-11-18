import os

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(autouse=True)
def clean_tables():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("truncate reminders, checkins restart identity")
    yield
