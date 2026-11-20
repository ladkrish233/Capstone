import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import logfire
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import ModelResponse, ToolCallPart

from app.models import CheckIn, Reminder
from rag.knowledge import search_notes

load_dotenv()

TZ = ZoneInfo("Asia/Kolkata")
URL = os.environ["DATABASE_URL"]
MODEL = os.environ["AGENT_MODEL"]  # for example "openrouter:<provider>/<model>" (must support tool calling)

prompt_path = Path(__file__).parent.parent / "prompts" / "friend_v4.md"
BASE_INSTRUCTIONS = prompt_path.read_text(encoding="utf-8").replace(
    "{today}", "shown in the Current time line"
)


logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

agent = Agent(MODEL, instructions=[BASE_INSTRUCTIONS])


@agent.instructions
def current_time_line() -> str:
    now = datetime.now(TZ)
    return f"Current time: {now:%A, %d %B %Y, %H:%M} IST."


def _conn():
    return psycopg.connect(URL, row_factory=dict_row, connect_timeout=15)


def _local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


@agent.tool_plain
def get_time() -> str:
    """Return the current time in India as HH:MM."""
    return datetime.now(TZ).strftime("%H:%M")


@agent.tool_plain
def list_reminders() -> str:
    """List the user's saved reminders. Use this when the user asks what reminders
    they have, what is coming up, or whether anything is scheduled."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                "select id, title, due_at, lead_minutes, status from reminders "
                "order by due_at limit 50"
            ).fetchall()
    except psycopg.Error:
        return "Could not read reminders right now."
    if not rows:
        return "No reminders saved."
    return "\n".join(
        f"{r['id']}: {r['title']} at {_local(r['due_at']):%a %d %b %H:%M} "
        f"(notify {r['lead_minutes']} min before, {r['status']})"
        for r in rows
    )


@agent.tool_plain
def add_reminder(reminder: Reminder) -> str:
    """Save a reminder. Use this when the user asks to be reminded of something.
    due_at is the time to remind them, and lead_minutes is how many minutes
    before that to notify them."""
    due = _local(reminder.due_at)
    if due < datetime.now(TZ):
        raise ModelRetry("That time is in the past. Use a future date.")
    try:
        with _conn() as conn:
            row = conn.execute(
                "insert into reminders (title, due_at, lead_minutes, status) "
                "values (%s, %s, %s, %s) returning id",
                (reminder.title, due, reminder.lead_minutes, reminder.status),
            ).fetchone()
    except psycopg.Error:
        return "Could not save the reminder right now."
    return f"Saved reminder {row['id']}: {reminder.title} at {due:%a %d %b %H:%M} IST."


@agent.tool_plain
def list_checkins() -> str:
    """List the user's most recent check-ins (mood, workouts, habits they logged).
    Use this when the user asks what they logged or how they have been doing."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                "select * from checkins order by id desc limit 20"
            ).fetchall()
    except psycopg.Error:
        return "Could not read check-ins right now."
    if not rows:
        return "No check-ins saved."
    return "\n".join(f"{r['id']}: {r['kind']} - {r['note']}" for r in rows)


@agent.tool_plain
def add_checkin(checkin: CheckIn) -> str:
    """Log a check-in. Use this when the user says how they feel or reports something
    they did (kind says what type of check-in it is, note is a short description)."""
    try:
        with _conn() as conn:
            row = conn.execute(
                "insert into checkins (kind, note) values (%s, %s) returning id",
                (checkin.kind, checkin.note),
            ).fetchone()
    except psycopg.Error:
        return "Could not save the check-in right now."
    return f"Logged check-in {row['id']}."


@agent.tool_plain
def search_knowledge(query: str) -> str:
    """Search the user's saved notes, documents and files (recipes, places, travel,
    diet, work notes, tips). Call this FIRST for any question about food, recipes,
    places, health habits, projects or tips, because the user may have saved their
    own version. Do not use for reminders or check-ins."""
    return search_notes(query)

def tool_used(result) -> list[str]:
    names = []
    for message in result.all_messages():
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    names.append(part.tool_name)
    return names