import asyncio
import os

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["API_KEY"] = "test-api-key"


@pytest.fixture(autouse=True)
def clean_tables():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("truncate reminders, checkins restart identity")
    yield


class _SyncTracker:
    """Calls the async tracker functions from sync tests on one event loop."""

    def __init__(self, loop):
        self._loop = loop

    def __getattr__(self, name):
        from app import tracker

        fn = getattr(tracker, name)
        return lambda *a, **k: self._loop.run_until_complete(fn(*a, **k))


@pytest.fixture
def t():
    from app import tracker
    from app.pool import make_pool

    loop = asyncio.new_event_loop()
    pool = loop.run_until_complete(make_pool())
    tracker.set_pool(pool)
    yield _SyncTracker(loop)
    tracker.set_pool(None)
    loop.run_until_complete(pool.close())
    loop.close()
