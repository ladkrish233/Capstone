from datetime import datetime, timedelta, timezone

from app import tracker
from app.models import CheckIn, Reminder

IST = timezone(timedelta(hours=5, minutes=30))


def test_naive_due_at_is_stored_as_ist():
    row = tracker.add_reminder(
        Reminder(title="Team meeting", due_at=datetime(2026, 11, 8, 16, 0))
    )
    assert row["due_at"] == datetime(2026, 11, 8, 16, 0, tzinfo=IST)


def test_checkins_with_same_time_list_higher_id_first():
    at = datetime(2026, 11, 8, 9, 0)
    first = tracker.add_checkin(CheckIn(kind="meal", note="a", at=at))
    second = tracker.add_checkin(CheckIn(kind="meal", note="b", at=at))
    ids = [r["id"] for r in tracker.list_checkins()]
    assert ids == [second["id"], first["id"]]


def test_limit_caps_results_and_none_means_all():
    for n in range(3):
        tracker.add_checkin(
            CheckIn(kind="mood", note=str(n), at=datetime(2026, 11, 8, 9, n))
        )
    assert len(tracker.list_checkins(limit=2)) == 2
    assert len(tracker.list_checkins()) == 3
    assert [r["note"] for r in tracker.list_checkins(limit=1)] == ["2"]


def test_delete_reminder_returns_none_for_missing_id():
    row = tracker.add_reminder(
        Reminder(title="x", due_at=datetime(2026, 11, 8, 16, 0))
    )
    assert tracker.delete_reminder(row["id"]) == {"id": row["id"]}
    assert tracker.delete_reminder(row["id"]) is None
