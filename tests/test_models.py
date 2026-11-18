from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import CheckIn, Reminder


def test_notify_at_is_lead_minutes_before_due():
    r = Reminder(title="Team meeting", due_at="2026-11-07T16:00:00", lead_minutes=10)
    assert r.notify_at == datetime(2026, 11, 7, 15, 50)


def test_lead_minutes_default_is_10():
    r = Reminder(title="Team meeting", due_at="2026-11-07T16:00:00")
    assert r.lead_minutes == 10
    assert r.status == "pending"


def test_lead_minutes_above_240_is_rejected():
    with pytest.raises(ValidationError):
        Reminder(title="Team meeting", due_at="2026-11-07T16:00:00", lead_minutes=300)


def test_empty_title_is_rejected():
    with pytest.raises(ValidationError):
        Reminder(title="", due_at="2026-11-07T16:00:00")


def test_bad_checkin_kind_is_rejected():
    with pytest.raises(ValidationError):
        CheckIn(kind="bananas", note="not a real kind")


def test_valid_checkin_gets_a_timestamp():
    c = CheckIn(kind="meal", note="poha and chai")
    assert isinstance(c.at, datetime)
