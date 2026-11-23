import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, headers={"x-api-key": os.environ["API_KEY"]})

REMINDER = {
    "title": "Team meeting",
    "due_at": "2026-11-08T16:00:00",
    "lead_minutes": 10,
}


def test_create_reminder_returns_201_and_id():
    r = client.post("/reminders", json=REMINDER)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["title"] == "Team meeting"
    assert body["status"] == "pending"


def test_list_reminders_is_empty_at_start():
    r = client.get("/reminders")
    assert r.status_code == 200
    assert r.json() == []


def test_lead_minutes_above_240_returns_422():
    r = client.post("/reminders", json={**REMINDER, "lead_minutes": 300})
    assert r.status_code == 422
    assert client.get("/reminders").json() == []


def test_delete_reminder_then_delete_again():
    created = client.post("/reminders", json=REMINDER).json()
    url = f"/reminders/{created['id']}"

    assert client.delete(url).status_code == 204
    assert client.delete(url).status_code == 404
    assert client.get("/reminders").json() == []


def test_delete_with_non_number_id_returns_422():
    assert client.delete("/reminders/abc").status_code == 422


def test_create_checkin_returns_201():
    r = client.post("/checkins", json={"kind": "meal", "note": "poha and chai"})
    assert r.status_code == 201
    assert r.json()["kind"] == "meal"


def test_bad_checkin_kind_returns_422():
    r = client.post("/checkins", json={"kind": "bananas", "note": "nope"})
    assert r.status_code == 422
    assert client.get("/checkins").json() == []
