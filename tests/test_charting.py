from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from utils.charting import (
    aggregate_expenses_by_category,
    aggregate_daily_cashflow,
    aggregate_monthly_cashflow,
    extract_months,
    extract_years,
)


def test_aggregate_expenses_by_category_counts_expenses_only():
    records = [
        IncomeRecord(date="2026-01-10", _amount_init=1000.0, category="Salary"),
        ExpenseRecord(date="2026-01-11", _amount_init=200.0, category="Food"),
        ExpenseRecord(date="2026-01-12", _amount_init=150.0, category="Food"),
        MandatoryExpenseRecord(
            date="2026-01-15",
            _amount_init=300.0,
            category="Rent",
            description="January rent",
            period="monthly",
        ),
    ]

    totals = aggregate_expenses_by_category(records)

    assert totals["Food"] == 350.0
    assert totals["Rent"] == 300.0
    assert "Salary" not in totals


def test_aggregate_daily_cashflow_returns_expected_lengths():
    records = [
        IncomeRecord(date="2026-02-01", _amount_init=100.0, category="Salary"),
        ExpenseRecord(date="2026-02-01", _amount_init=20.0, category="Food"),
        ExpenseRecord(date="2026-02-14", _amount_init=30.0, category="Gift"),
        IncomeRecord(date="2026-03-01", _amount_init=999.0, category="Other"),
    ]

    income, expense = aggregate_daily_cashflow(records, 2026, 2)

    assert len(income) == 28
    assert len(expense) == 28
    assert income[0] == 100.0
    assert expense[0] == 20.0
    assert expense[13] == 30.0
    assert sum(income) == 100.0
    assert sum(expense) == 50.0


def test_aggregate_monthly_cashflow_groups_by_month():
    records = [
        IncomeRecord(date="2026-01-10", _amount_init=500.0, category="Salary"),
        ExpenseRecord(date="2026-01-11", _amount_init=100.0, category="Food"),
        IncomeRecord(date="2026-02-05", _amount_init=250.0, category="Bonus"),
        ExpenseRecord(date="2025-12-31", _amount_init=999.0, category="Other"),
    ]

    income, expense = aggregate_monthly_cashflow(records, 2026)

    assert income[0] == 500.0
    assert expense[0] == 100.0
    assert income[1] == 250.0
    assert expense[1] == 0.0
    assert sum(income) == 750.0
    assert sum(expense) == 100.0


def test_extract_months_and_years():
    records = [
        IncomeRecord(date="2024-12-31", _amount_init=10.0, category="A"),
        ExpenseRecord(date="2025-01-01", _amount_init=20.0, category="B"),
        IncomeRecord(date="2025-02-01", _amount_init=30.0, category="C"),
    ]

    months = extract_months(records)
    years = extract_years(records)

    assert months == ["2024-12", "2025-01", "2025-02"]
    assert years == [2024, 2025]
