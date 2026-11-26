from datetime import datetime, timedelta, timezone

from app.models import CheckIn, Reminder

IST = timezone(timedelta(hours=5, minutes=30))


def test_naive_due_at_is_stored_as_ist(t):
    row = t.add_reminder(
        Reminder(title="Team meeting", due_at=datetime(2026, 11, 8, 16, 0))
    )
    assert row["due_at"] == datetime(2026, 11, 8, 16, 0, tzinfo=IST)


def test_checkins_with_same_time_list_higher_id_first(t):
    at = datetime(2026, 11, 8, 9, 0)
    first = t.add_checkin(CheckIn(kind="meal", note="a", at=at))
    second = t.add_checkin(CheckIn(kind="meal", note="b", at=at))
    ids = [r["id"] for r in t.list_checkins()]
    assert ids == [second["id"], first["id"]]


def test_limit_caps_results_and_none_means_all(t):
    for n in range(3):
        t.add_checkin(
            CheckIn(kind="mood", note=str(n), at=datetime(2026, 11, 8, 9, n))
        )
    assert len(t.list_checkins(limit=2)) == 2
    assert len(t.list_checkins()) == 3
    assert [r["note"] for r in t.list_checkins(limit=1)] == ["2"]


def test_delete_reminder_returns_none_for_missing_id(t):
    row = t.add_reminder(
        Reminder(title="x", due_at=datetime(2026, 11, 8, 16, 0))
    )
    assert t.delete_reminder(row["id"]) == {"id": row["id"]}
    assert t.delete_reminder(row["id"]) is None
