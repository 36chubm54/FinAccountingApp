import pytest
from datetime import date, timedelta

from domain.validation import parse_ymd, ensure_not_future, ensure_valid_period


def test_parse_ymd_valid():
    assert parse_ymd("2025-02-01") == date(2025, 2, 1)


@pytest.mark.parametrize(
    "value",
    [
        "2025-13-01",
        "2025-00-10",
        "2025-02-30",
        "2025/02/01",
        "2025-2-1",
        "2025-02",
        "20265-01-02",
        "",
    ],
)
def test_parse_ymd_invalid(value):
    with pytest.raises(ValueError):
        parse_ymd(value)


def test_ensure_not_future_raises():
    future_date = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        ensure_not_future(future_date)


@pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "yearly"])
def test_ensure_valid_period_ok(period):
    ensure_valid_period(period)


def test_ensure_valid_period_raises():
    with pytest.raises(ValueError):
        ensure_valid_period("hourly")
