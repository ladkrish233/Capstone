from fastapi import HTTPException,Header,APIRouter
from app.security import check_key
from app.models import Reminder,CheckIn
from app.db import (
    add_checkin,
    add_reminder,
    delete_reminder,
    get_db_health,
    list_checkins,
    list_reminders,
)

router=APIRouter()

@router.post("/reminders", status_code=201)
def create_reminders(reminder: Reminder,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return add_reminder(reminder)


@router.get("/reminders")
def list_reminder(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return list_reminders()


@router.post("/checkins", status_code=201)
def create_checkins(checkin: CheckIn,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return add_checkin(checkin)


@router.get("/checkins")
def list_checkin(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return list_checkins()


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminders(reminder_id: int,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    deleted = delete_reminder(reminder_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return deleted
