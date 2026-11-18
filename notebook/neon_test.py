import os
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()

NEON_DATABASE_URL = os.environ["NEON_DATABASE_URL"]

start = time.perf_counter()

with psycopg.connect(NEON_DATABASE_URL) as conn:
    one = time.perf_counter()
    row = conn.execute("SELECT 1").fetchone()
    two = time.perf_counter()
    version = conn.execute(
        "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
    ).fetchone()
    third = time.perf_counter()
    print("pgvector:", version[0] if version else "not installed")

print("for conn", (one - start) * 1000)
print("for first query", (two - one) * 1000)
print("for second query", (third - two) * 1000)
elapsed = (time.perf_counter() - start) * 1000
print(f"{elapsed:.0f} ms")
