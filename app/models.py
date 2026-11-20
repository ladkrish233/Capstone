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

class ChatRequest(BaseModel):
    message:str = Field(min_length=1,max_length=1000)
    session_id:str="main"

class ChatResponse(BaseModel):
    answer:str
