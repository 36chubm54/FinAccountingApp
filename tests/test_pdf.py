import tempfile
import os

from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from domain.reports import Report

from utils.pdf_utils import (
    report_to_pdf,
    export_mandatory_expenses_to_pdf,
)


def test_report_pdf_roundtrip():
    records = [
        IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
        ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
    ]
    report = Report(records, initial_balance=25.0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        path = tmp.name
    try:
        report_to_pdf(report, path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)


def test_mandatory_pdf_roundtrip():
    expenses = [
        MandatoryExpenseRecord(
            date="", amount=12.5, category="Sub", description="d1", period="monthly"
        ),
        MandatoryExpenseRecord(
            date="", amount=7.75, category="Svc", description="d2", period="yearly"
        ),
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        path = tmp.name
    try:
        export_mandatory_expenses_to_pdf(expenses, path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)
