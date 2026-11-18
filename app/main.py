import logging
import os
import secrets

from fastapi import FastAPI, Header, HTTPException

from app.db import (
    add_checkin,
    add_reminder,
    delete_reminder,
    get_db_health,
    list_checkins,
    list_reminders,
)
from app.models import CheckIn, Reminder

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def db_health(x_health_key: str | None = Header(default=None)):
    expected = os.environ.get("HEALTH_KEY", "")
    given = x_health_key or ""
    if not expected or not secrets.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        return get_db_health()
    except Exception:
        logger.exception("db health check failed")
        raise HTTPException(status_code=503, detail="db unavailable")


@app.post("/reminders", status_code=201)
def create_reminders(reminder: Reminder):
    return add_reminder(reminder)


@app.get("/reminders")
def list_reminder():
    return list_reminders()


@app.post("/checkins", status_code=201)
def create_checkins(checkin: CheckIn):
    return add_checkin(checkin)


@app.get("/checkins")
def list_checkin():
    return list_checkins()


@app.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminders(reminder_id: int):
    deleted = delete_reminder(reminder_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return deleted
