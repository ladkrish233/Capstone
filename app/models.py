from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Reminder(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_at: datetime
    lead_minutes: int = Field(default=10, ge=0, le=240)
    status: Literal["pending", "done", "missed"] = "pending"

    @property
    def notify_at(self) -> datetime:
        return self.due_at - timedelta(minutes=self.lead_minutes)


class CheckIn(BaseModel):
    kind: str
    note: str
    at: datetime = Field(default_factory=datetime.now)

    @field_validator("kind")
    @classmethod
    def kind_must_be_known(cls, value) -> str:
        allowed = {"meal", "gym", "sleep", "mood"}
        if value not in allowed:
            raise ValueError(f"kind must be one of {sorted(allowed)}")
        return value


if __name__ == "__main__":
    meeting = Reminder(
        title="Team meeting", due_at="2026-11-07T16:00:00", lead_minutes=10
    )
    print("Reminder:", meeting)
    print("Call me at:", meeting.notify_at)

    lunch = CheckIn(kind="meal", note="poha and chai")
    print("Check-in:", lunch.model_dump_json())

    try:
        CheckIn(kind="dance", note="oops")
    except Exception as error:
        print("Caught bad data:", error.errors()[0]["msg"])
