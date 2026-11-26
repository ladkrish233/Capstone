import os
from pathlib import Path

import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent

from app.api.agent.tools import (
    add_checkin,
    add_reminder,
    current_time_line,
    get_time,
    list_checkins,
    list_reminders,
    search_knowledge,
)

load_dotenv()

MODEL=os.environ["AGENT_MODEL"]
prompt_path=Path(__file__).parent.parent.parent / "prompts" / "friend_v4.md"
BASE_INSTRUCTION=prompt_path.read_text(encoding="utf-8").replace(
    "{time}","shown in Current time line"
)

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

def build_agent(model : str | None = None,capabilities=None)->Agent:
    return Agent(
        MODEL or model,
        instructions=[BASE_INSTRUCTION,current_time_line],
        tools=[get_time,add_checkin,add_reminder,
            list_checkins,list_reminders,search_knowledge],
        capabilities=capabilities or [],
    )