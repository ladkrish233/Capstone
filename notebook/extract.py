from datetime import date

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.models import Reminder

load_dotenv()


def parser_reminder(sentence: str) -> Reminder:
    instructions = f"""
                You turn one spoken sentence into one reminder.

                Today's date is {date.today().isoformat()}. Use it to work out dates such as
                "tomorrow" or "Friday". The user is in India, so all times are local time.

                Rules:
                - Use only what the sentence says. Do not invent a time or a title.
                - Copy the lead time exactly as the user said it. Never change a number to fit
                the allowed range. If the user says 300 minutes, return 300.
                - If no lead time is given, use 10 minutes.
                - The title is the task in the user's own words, kept short. If the sentence
                has no clear task, use its first few words as the title. Never write
                placeholders such as UNKNOWN or N/A.
                """

    agent = Agent(
        "anthropic:claude-haiku-4-5-20251001",
        instructions=instructions,
        output_type=Reminder,
    )

    result = agent.run_sync(sentence)
    return result.output


try:
    print(parser_reminder("Remind me at 4 pm with lead time of 300 minutes"))
except UnexpectedModelBehavior:
    print("Could not make a valid reminder. Please give the time and lead time again.")
