from datetime import datetime
from pathlib import Path

import httpx
import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.anthropic import AnthropicModelSettings

from app.models import CheckIn, Reminder
from rag.knowledge import search_notes

load_dotenv()

prompt_path = Path(__file__).parent.parent / "prompts" / "friend_v4.md"
instruction = prompt_path.read_text(encoding="utf-8").replace(
    "{today}", datetime.today().isoformat()
)


logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

agent = Agent(
    "anthropic:claude-haiku-5-5",
    instructions=instruction,
    model_settings=AnthropicModelSettings(
        anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True
    ),
)


@agent.tool_plain
def get_time() -> str:
    """Return the current local time as HH:MM."""

    return datetime.now().strftime("%H:%m")


@agent.tool_plain
async def list_reminders() -> str:
    async with httpx.AsyncClient() as client:
        """List the user's saved reminders. Use this when the user asks what reminders they have, what is coming up, or whether they have anything scheduled. Returns every reminder as JSON, ordered by due time."""

        r = await client.get("http://localhost:8000/reminders")
        r.raise_for_status()
        return r.text


@agent.tool_plain
async def add_reminder(reminder: Reminder) -> str:
    """Save a reminder. Use this when the user asks to be reminded of something. due_at is the time to remind them, and lead_minutes is how many minutes before that to notify them."""

    due = reminder.due_at
    if due.tzinfo is not None:
        due = due.astimezone().replace(tzinfo=None)

    if due < datetime.now():
        raise ModelRetry("That time is in the past. Use a future date.")

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:8000/reminders", json=reminder.model_dump(mode="json")
            )
            r.raise_for_status()
            return r.text
    except httpx.HTTPStatusError as e:
        return f"Failed: {e.response.status_code} {e.response.text}"


@agent.tool_plain
async def list_checkins() -> str:
    """List the user's saved checkins. Use this when the user asks what checkins they have, what is coming up, or whether they have anything scheduled. Returns every checkins as JSON, ordered by due time."""

    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:8000/checkins")
        r.raise_for_status()
        return r.text


@agent.tool_plain
async def add_checkins(checkin: CheckIn) -> str:
    """Save a reminder. Use this when the user asks to be reminded of something. due_at is the time to remind them, and lead_minutes is how many minutes before that to notify them."""

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:8000/checkins", json=checkin.model_dump(mode="json")
            )
            r.raise_for_status()
            return r.text
    except httpx.HTTPStatusError as e:
        return f"Failed: {e.response.status_code} {e.response.text}"


@agent.tool_plain
def search_knowledge(query: str) -> str:
    """Search the user's saved notes, documents and files (recipes, places, travel, diet, work notes, tips).
    Call this FIRST for any question about food, recipes, places, health habits, projects or tips,
    because the user may have saved their own version. Do not use for reminders or check-ins."""
    return search_notes(query)


def tool_used(result) -> list[str]:
    names = []
    for messages in result.all_messages():
        if isinstance(messages, ModelResponse):
            for part in messages.parts:
                if isinstance(part, ToolCallPart):
                    names.append(part.tool_name)
    return names


if __name__ == "__main__":
    result = agent.run_sync("Skipped the gym today, feeling lazy")
    print(result.output)
    print(tool_used(result))
    print(result.usage.cache_write_tokens)
    print(result.usage.cache_read_tokens)
