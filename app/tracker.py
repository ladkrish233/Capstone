"""Reminders and check-ins: the one place that owns their SQL and rules.

Callers (HTTP routes, agent tools) get plain dicts and see psycopg.Error
if the database fails. Formatting and error messages belong to the callers.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from app.models import CheckIn, Reminder

TZ = ZoneInfo("Asia/Kolkata")


def to_ist(dt: datetime) -> datetime:
    """Attach IST to a naive datetime, or convert an aware one to IST."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def _conn():
    return psycopg.connect(
        os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=15
    )


def add_reminder(reminder: Reminder) -> dict:
    with _conn() as conn:
        return conn.execute(
            "insert into reminders (title, due_at, lead_minutes, status) "
            "values (%s, %s, %s, %s) ON CONFLICT DO NOTHING returning *",
            (
                reminder.title,
                to_ist(reminder.due_at),
                reminder.lead_minutes,
                reminder.status,
            ),
        ).fetchone()


def list_reminders(limit: int | None = None) -> list[dict]:
    with _conn() as conn:
        return conn.execute(
            "select * from reminders order by due_at, id limit %s", (limit,)
        ).fetchall()


def delete_reminder(reminder_id: int) -> dict | None:
    with _conn() as conn:
        return conn.execute(
            "delete from reminders where id = %s returning id", (reminder_id,)
        ).fetchone()


def add_checkin(checkin: CheckIn) -> dict:
    with _conn() as conn:
        return conn.execute(
            "insert into checkins (kind, note, at) values (%s, %s, %s) returning *",
            (checkin.kind, checkin.note, checkin.at),
        ).fetchone()


def list_checkins(limit: int | None = None) -> list[dict]:
    with _conn() as conn:
        return conn.execute(
            "select * from checkins order by at desc, id desc limit %s", (limit,)
        ).fetchall()
