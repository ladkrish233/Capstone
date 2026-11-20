import logging
from fastapi import FastAPI, Header, HTTPException
from app.agent import agent
from app.db import (
    add_checkin,
    add_reminder,
    delete_reminder,
    get_db_health,
    list_checkins,
    list_reminders,
)
from app.models import ChatRequest, ChatResponse, CheckIn, Reminder
from app.security import check_key
from app.voice import router as voice_router
from app.chat import router as chat_router
from app.warmup import router as warmup_router

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(warmup_router)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/db")
def db_health(x_health_key: str | None = Header(default=None)):
    check_key(x_health_key,"HEALTH_KEY")
    try:
        return get_db_health()
    except Exception:
        logger.exception("db health check failed")
        raise HTTPException(status_code=503,detail="db unavailable")

@app.post("/reminders", status_code=201)
def create_reminders(reminder: Reminder,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return add_reminder(reminder)


@app.get("/reminders")
def list_reminder(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return list_reminders()


@app.post("/checkins", status_code=201)
def create_checkins(checkin: CheckIn,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return add_checkin(checkin)


@app.get("/checkins")
def list_checkin(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return list_checkins()


@app.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminders(reminder_id: int,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    deleted = delete_reminder(reminder_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return deleted


