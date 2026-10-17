"""Scheduler due logic: interval mode and one fixed time per day."""

from __future__ import annotations

import datetime

from app.jobs.automation import is_due


def _settings(**overrides):
    base = {
        "enabled": True,
        "interval_minutes": 60,
        "mode": "interval",
        "daily_time": None,
        "last_tick": None,
    }
    base.update(overrides)
    return base


def test_disabled_never_due():
    assert is_due(_settings(enabled=False)) is False


def test_interval_mode():
    now = datetime.datetime.now()

    assert is_due(_settings(last_tick=None)) is True
    assert is_due(_settings(last_tick=now - datetime.timedelta(minutes=30))) is False
    assert is_due(_settings(last_tick=now - datetime.timedelta(minutes=90))) is True


def test_daily_mode_waits_for_the_configured_time():
    now = datetime.datetime.now()
    target = datetime.time(0, 0)  # today's time is always >= 00:00

    # Never ticked: due as soon as the time has come.
    assert is_due(_settings(mode="daily", daily_time="00:00")) is True

    # Ticked today after the target: not due again today.
    last = datetime.datetime.combine(now.date(), target) + datetime.timedelta(
        minutes=5
    )
    assert is_due(_settings(mode="daily", daily_time="00:00", last_tick=last)) is False

    # Ticked yesterday: due again today.
    yesterday = last - datetime.timedelta(days=1)
    assert is_due(_settings(mode="daily", daily_time="00:00", last_tick=yesterday)) is True
