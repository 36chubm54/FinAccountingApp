from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from typing import Iterable, Dict, List, Tuple

from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord, Record


def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def aggregate_expenses_by_category(records: Iterable[Record]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    for record in records:
        if isinstance(record, IncomeRecord):
            continue
        if isinstance(record, (ExpenseRecord, MandatoryExpenseRecord)):
            totals[record.category] = totals.get(record.category, 0.0) + abs(
                record.amount_kzt
            )
    return totals


def aggregate_daily_cashflow(
    records: Iterable[Record], year: int, month: int
) -> Tuple[List[float], List[float]]:
    days_in_month = monthrange(year, month)[1]
    income = [0.0 for _ in range(days_in_month)]
    expense = [0.0 for _ in range(days_in_month)]

    for record in records:
        dt = _parse_date(record.date)
        if not dt:
            continue
        if dt.year != year or dt.month != month:
            continue
        idx = dt.day - 1
        if isinstance(record, IncomeRecord):
            income[idx] += record.amount_kzt
        elif isinstance(record, (ExpenseRecord, MandatoryExpenseRecord)):
            expense[idx] += abs(record.amount_kzt)

    return income, expense


def aggregate_monthly_cashflow(
    records: Iterable[Record], year: int
) -> Tuple[List[float], List[float]]:
    income = [0.0 for _ in range(12)]
    expense = [0.0 for _ in range(12)]

    for record in records:
        dt = _parse_date(record.date)
        if not dt:
            continue
        if dt.year != year:
            continue
        idx = dt.month - 1
        if isinstance(record, IncomeRecord):
            income[idx] += record.amount_kzt
        elif isinstance(record, (ExpenseRecord, MandatoryExpenseRecord)):
            expense[idx] += abs(record.amount_kzt)

    return income, expense


def extract_years(records: Iterable[Record]) -> List[int]:
    years = set()
    for record in records:
        dt = _parse_date(record.date)
        if dt:
            years.add(dt.year)
    return sorted(years)


def extract_months(records: Iterable[Record]) -> List[str]:
    months = set()
    for record in records:
        dt = _parse_date(record.date)
        if dt:
            months.add(f"{dt.year:04d}-{dt.month:02d}")
    return sorted(months)
