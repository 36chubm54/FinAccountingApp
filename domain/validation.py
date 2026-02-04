from datetime import date
import calendar


def parse_ymd(value: str) -> date:
    parts = value.split("-")
    if len(parts) != 3:
        raise ValueError("Invalid date format")
    year, month, day = map(int, parts)
    if not (1 <= month <= 12):
        raise ValueError("Invalid month")
    last_day = calendar.monthrange(year, month)[1]
    if not (1 <= day <= last_day):
        raise ValueError("Invalid day")
    return date(year, month, day)


def ensure_not_future(value: date) -> None:
    if value > date.today():
        raise ValueError("Date cannot be in the future")


def ensure_valid_period(period: str) -> None:
    valid_periods = ["daily", "weekly", "monthly", "yearly"]
    if period not in valid_periods:
        raise ValueError(f"Invalid period: {period}. Must be one of {valid_periods}")
