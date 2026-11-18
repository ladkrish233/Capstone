import os
import time

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from app.models import CheckIn, Reminder

load_dotenv()
URL = os.environ["DATABASE_URL"]


def get_db_health():
    start = time.perf_counter()
    with psycopg.connect(URL, connect_timeout=10) as conn:
        conn.execute("select 1").fetchone()
    return {"ok": True, "ms": round((time.perf_counter() - start) * 1000)}


def add_reminder(reminder: Reminder):
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        return conn.execute(
            """
        insert into reminders (title, due_at, lead_minutes, status)
        values (%s,%s,%s,%s)
        returning *
        """,
            (reminder.title, reminder.due_at, reminder.lead_minutes, reminder.status),
        ).fetchone()


def list_reminders():
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        return conn.execute(
            """
        select * from reminders order by due_at
        """,
        ).fetchall()


def add_checkin(checkin: CheckIn):
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        return conn.execute(
            """
        insert into checkins (kind,note,at)
        values (%s,%s,%s)
        returning *
        """,
            (checkin.kind, checkin.note, checkin.at),
        ).fetchone()


def list_checkins():
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        return conn.execute(
            """
        select * from checkins order by at desc
        """,
        ).fetchall()


def delete_reminder(reminder_id: int):
    with psycopg.connect(URL, row_factory=dict_row) as conn:
        return conn.execute(
            """
        delete from reminders where id=%s
        returning id
        """,
            (reminder_id,),
        ).fetchone()


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


if __name__ == "__main__":
    meeting = Reminder(
        title="Team meeting", due_at="2026-11-07T16:00:00", lead_minutes=10
    )
    saved = add_reminder(meeting)
    print("Saved : ", saved)
    meal = CheckIn(kind="meal", note="poha and chai")
    saved = add_checkin(meal)
    print("Saved : ", saved)
    print(list_reminders())
    print(list_checkins())
