from fastapi import APIRouter, Header, HTTPException

from app.models import CheckIn, Reminder
from app.security import check_key
from app.tracker import (
    add_checkin,
    add_reminder,
    delete_reminder,
    list_checkins,
    list_reminders,
)

router=APIRouter()

@router.post("/reminders", status_code=201)
async def create_reminders(reminder: Reminder,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return await add_reminder(reminder)


@router.get("/reminders")
async def list_reminder(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return await list_reminders()


@router.post("/checkins", status_code=201)
async def create_checkins(checkin: CheckIn,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return await add_checkin(checkin)


@router.get("/checkins")
async def list_checkin(x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    return await list_checkins()


@router.delete("/reminders/{reminder_id}", status_code=204)
async def delete_reminders(reminder_id: int,x_api_key: str | None = Header(default=None)):
    check_key(x_api_key,"API_KEY")
    deleted = await delete_reminder(reminder_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return deleted
