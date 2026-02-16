import tempfile
import os

from domain.records import IncomeRecord, ExpenseRecord
from domain.reports import Report

from utils.pdf_utils import report_to_pdf


def test_report_pdf_roundtrip():
    records = [
        IncomeRecord(date="2025-01-01", _amount_init=100.0, category="Salary"),
        ExpenseRecord(date="2025-01-02", _amount_init=30.0, category="Food"),
    ]
    report = Report(records, initial_balance=25.0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        path = tmp.name
    try:
        report_to_pdf(report, path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)
