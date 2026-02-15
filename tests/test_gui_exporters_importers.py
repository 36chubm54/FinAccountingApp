from pathlib import Path
import os
import tempfile

from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from domain.reports import Report

from gui import exporters, importers


def make_sample_report():
    records = [
        IncomeRecord(date="2025-01-01", _amount_init=100.0, category="Salary"),
        ExpenseRecord(date="2025-01-02", _amount_init=30.0, category="Food"),
        MandatoryExpenseRecord(
            date="2025-01-03",
            _amount_init=20.0,
            category="Rent",
            description="Monthly rent",
            period="monthly",
        ),
    ]
    return Report(records, initial_balance=10.0)


def test_export_report_csv_xlsx_pdf():
    report = make_sample_report()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as csv_tmp:
        csv_path = Path(csv_tmp.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as xlsx_tmp:
        xlsx_path = Path(xlsx_tmp.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_tmp:
        pdf_path = Path(pdf_tmp.name)

    try:
        exporters.export_report(report, str(csv_path), "csv")
        assert csv_path.exists()
        text = csv_path.read_text(encoding="utf-8")
        assert "Date" in text
        assert "FINAL BALANCE" in text

        exporters.export_report(report, str(xlsx_path), "xlsx")
        assert xlsx_path.exists()
        assert xlsx_path.stat().st_size > 0

        exporters.export_report(report, str(pdf_path), "pdf")
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
    finally:
        for p in (csv_path, xlsx_path, pdf_path):
            if p.exists():
                os.unlink(p)


def test_export_and_import_mandatory_expenses_csv_xlsx():
    expenses = [
        MandatoryExpenseRecord(
            date="",
            _amount_init=50.0,
            category="Utilities",
            description="Water",
            period="monthly",
        ),
        MandatoryExpenseRecord(
            date="",
            _amount_init=120.0,
            category="Internet",
            description="ISP",
            period="monthly",
        ),
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as csv_tmp:
        csv_path = Path(csv_tmp.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as xlsx_tmp:
        xlsx_path = Path(xlsx_tmp.name)

    try:
        exporters.export_mandatory_expenses(expenses, str(csv_path), "csv")
        assert csv_path.exists()
        data, _ = importers.import_mandatory_expenses_from_csv(str(csv_path))
        assert len(data) == len(expenses)

        exporters.export_mandatory_expenses(expenses, str(xlsx_path), "xlsx")
        assert xlsx_path.exists()
        data2, _ = importers.import_mandatory_expenses_from_xlsx(str(xlsx_path))
        assert len(data2) == len(expenses)
    finally:
        for p in (csv_path, xlsx_path):
            if p.exists():
                os.unlink(p)


def test_import_records_from_csv_xlsx_roundtrip():
    report = make_sample_report()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as xlsx_tmp:
        xlsx_path = Path(xlsx_tmp.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as csv_tmp:
        csv_path = Path(csv_tmp.name)

    try:
        from utils.excel_utils import export_records_to_xlsx

        export_records_to_xlsx(report.records(), str(xlsx_path), report.initial_balance)
        records_xlsx, initial_balance_xlsx, _ = importers.import_records_from_xlsx(str(xlsx_path))
        assert len(records_xlsx) == len(report.records())
        assert initial_balance_xlsx == report.initial_balance

        from utils.csv_utils import export_records_to_csv

        export_records_to_csv(report.records(), str(csv_path), report.initial_balance)
        records_csv, initial_balance_csv, _ = importers.import_records_from_csv(str(csv_path))
        assert len(records_csv) == len(report.records())
        assert initial_balance_csv == report.initial_balance
    finally:
        for p in (csv_path, xlsx_path):
            if p.exists():
                os.unlink(p)
