"""Tests for services/charts.py — period bounds and timezone handling."""
from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app.services.charts import get_period_bounds

_CHICAGO = ZoneInfo("America/Chicago")


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """Convenience helper to build a UTC-aware datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_daily_start_reflects_chicago_midnight() -> None:
    """The daily period start must be local midnight in America/Chicago, not UTC."""
    # Simulate "now" as 2024-03-15 03:00 UTC = 2024-03-14 22:00 CST (UTC-5)
    # So local Chicago midnight is 2024-03-14 00:00 CST = 2024-03-14 05:00 UTC
    fake_now = _utc(2024, 3, 15, 3, 0)

    with patch("app.services.charts.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        # Make replace() and astimezone() work transparently on real datetimes
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        start, end = get_period_bounds("daily")

    # Expected: 2024-03-14 00:00 CST = 2024-03-14 06:00 UTC (UTC-6 standard)
    # CST is UTC-6; CDT is UTC-5.  March 15 03:00 UTC is after the spring-forward
    # (2024-03-10 02:00 local), so Chicago is on CDT (UTC-5).
    # 2024-03-14 22:00 CST → 2024-03-15 03:00 UTC (but CST was -6 before spring-forward)
    # Re-check: spring-forward 2024 was 2024-03-10.  So 2024-03-15 is CDT (UTC-5).
    # 2024-03-15 03:00 UTC = 2024-03-14 22:00 CDT (UTC-5).
    # Chicago midnight that day: 2024-03-14 00:00 CDT = 2024-03-14 05:00 UTC.
    expected_start = _utc(2024, 3, 14, 5, 0)
    assert start == expected_start


def test_daily_start_is_not_utc_midnight() -> None:
    """Confirm daily start differs from UTC midnight when Chicago is offset."""
    # Pick a time where UTC midnight != Chicago midnight: Jan 20 10:00 UTC = 04:00 CST
    fake_now = _utc(2024, 1, 20, 10, 0)

    with patch("app.services.charts.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        start, _ = get_period_bounds("daily")

    utc_midnight = _utc(2024, 1, 20, 0, 0)
    assert start != utc_midnight, "daily start must not be UTC midnight"

    # Chicago is CST (UTC-6) in January.  Local midnight was 2024-01-20 00:00 CST
    # = 2024-01-20 06:00 UTC.
    expected_start = _utc(2024, 1, 20, 6, 0)
    assert start == expected_start


def test_weekly_start_is_monday() -> None:
    """Weekly period always starts on the Monday of the current ISO week."""
    # 2024-03-15 is a Friday
    fake_now = _utc(2024, 3, 15, 12, 0)

    with patch("app.services.charts.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        start, _ = get_period_bounds("weekly")

    assert start.weekday() == 0  # 0 = Monday
    assert start == _utc(2024, 3, 11, 0, 0)


def test_monthly_start_is_first_of_month() -> None:
    """Monthly period always starts on the 1st at 00:00 UTC."""
    fake_now = _utc(2024, 3, 15, 12, 0)

    with patch("app.services.charts.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        start, _ = get_period_bounds("monthly")

    assert start == _utc(2024, 3, 1, 0, 0)


def test_end_is_slightly_after_now() -> None:
    """end is always 1 second ahead of now for an inclusive upper bound."""
    fake_now = _utc(2024, 3, 15, 12, 0)

    with patch("app.services.charts.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        _, end = get_period_bounds("daily")

    from datetime import timedelta
    assert end == fake_now + timedelta(seconds=1)
