import tempfile
import os

from domain.records import (
    IncomeRecord,
    ExpenseRecord,
    MandatoryExpenseRecord,
)
from domain.reports import Report

from utils.excel_utils import (
    report_to_xlsx,
    report_from_xlsx,
    export_mandatory_expenses_to_xlsx,
    import_mandatory_expenses_from_xlsx,
)

from utils.csv_utils import (
    export_mandatory_expenses_to_csv,
    import_mandatory_expenses_from_csv,
)


def test_report_xlsx_roundtrip():
    records = [
        IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
        ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
    ]
    report = Report(records, initial_balance=50.0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = tmp.name
    try:
        report_to_xlsx(report, tmp_path)
        imported = report_from_xlsx(tmp_path)
        assert len(imported.records()) == 2
        assert abs(imported._initial_balance - 50.0) < 1e-6
        assert abs(imported.total() - report.total()) < 1e-6
    finally:
        os.unlink(tmp_path)


def test_mandatory_xlsx_roundtrip():
    expenses = [
        MandatoryExpenseRecord(
            date="", amount=10.0, category="Sub", description="d1", period="monthly"
        ),
        MandatoryExpenseRecord(
            date="", amount=20.5, category="Svc", description="d2", period="yearly"
        ),
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = tmp.name
    try:
        export_mandatory_expenses_to_xlsx(expenses, tmp_path)
        imported = import_mandatory_expenses_from_xlsx(tmp_path)
        assert len(imported) == 2
        assert imported[0].amount == 10.0
        assert imported[1].period == "yearly"
    finally:
        os.unlink(tmp_path)


def test_mandatory_csv_roundtrip():
    expenses = [
        MandatoryExpenseRecord(
            date="", amount=5.0, category="A", description="x", period="daily"
        ),
    ]
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv", mode="w", newline=""
    ) as tmp:
        tmp_path = tmp.name
    try:
        export_mandatory_expenses_to_csv(expenses, tmp_path)
        imported = import_mandatory_expenses_from_csv(tmp_path)
        assert len(imported) == 1
        assert imported[0].amount == 5.0
        assert imported[0].period == "daily"
    finally:
        os.unlink(tmp_path)
