"""Reminders and check-ins: the one place that owns their SQL and rules.

Everything runs on the shared asyncpg pool (set once at startup with
set_pool). Callers (HTTP routes, agent tools) get plain dicts and see
DB_ERRORS if the database fails. Formatting and error messages belong to
the callers.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import asyncpg

from app.models import CheckIn, Reminder

TZ = ZoneInfo("Asia/Kolkata")

# What callers should catch when the database is unavailable or a query fails.
DB_ERRORS = (asyncpg.PostgresError, asyncpg.InterfaceError, OSError)

_pool: asyncpg.Pool | None = None


def set_pool(pool: asyncpg.Pool | None) -> None:
    global _pool
    _pool = pool


def _get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("tracker pool not set: call tracker.set_pool() at startup")
    return _pool


def to_ist(dt: datetime) -> datetime:
    """Attach IST to a naive datetime, or convert an aware one to IST."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def _naive_ist(dt: datetime) -> datetime:
    """checkins.at is `timestamp` (no zone): asyncpg wants a naive value."""
    return dt if dt.tzinfo is None else to_ist(dt).replace(tzinfo=None)


def _row(record: asyncpg.Record | None) -> dict | None:
    return None if record is None else dict(record)


async def add_reminder(reminder: Reminder) -> dict | None:
    return _row(
        await _get_pool().fetchrow(
            "insert into reminders (title, due_at, lead_minutes, status) "
            "values ($1, $2, $3, $4) ON CONFLICT DO NOTHING returning *",
            reminder.title,
            to_ist(reminder.due_at),
            reminder.lead_minutes,
            reminder.status,
        )
    )


async def list_reminders(limit: int | None = None) -> list[dict]:
    rows = await _get_pool().fetch(
        "select * from reminders order by due_at, id limit $1", limit
    )
    return [dict(r) for r in rows]


async def delete_reminder(reminder_id: int) -> dict | None:
    return _row(
        await _get_pool().fetchrow(
            "delete from reminders where id = $1 returning id", reminder_id
        )
    )


async def add_checkin(checkin: CheckIn) -> dict:
    return _row(
        await _get_pool().fetchrow(
            "insert into checkins (kind, note, at) values ($1, $2, $3) returning *",
            checkin.kind,
            checkin.note,
            _naive_ist(checkin.at),
        )
    )


async def list_checkins(limit: int | None = None) -> list[dict]:
    rows = await _get_pool().fetch(
        "select * from checkins order by at desc, id desc limit $1", limit
    )
    return [dict(r) for r in rows]
