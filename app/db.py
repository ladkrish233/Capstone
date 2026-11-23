import os
import time

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()
URL = os.environ["DATABASE_URL"]


def get_db_health():
    start = time.perf_counter()
    with psycopg.connect(URL, connect_timeout=10) as conn:
        conn.execute("select 1").fetchone()
    return {"ok": True, "ms": round((time.perf_counter() - start) * 1000)}


def add_cost_event(model: str, input_tokens: int, output_tokens: int, cost_usd: float):
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        return conn.execute(
            """
        insert into cost_events (model,input_tokens,output_tokens,cost_usd)
        values (%s,%s,%s,%s)
        returning *
        """,
            (model, input_tokens, output_tokens, cost_usd),
        ).fetchone()
