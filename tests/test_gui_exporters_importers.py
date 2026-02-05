from pathlib import Path

from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from domain.reports import Report

from gui import exporters, importers


def make_sample_report():
    records = [
        IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
        ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
        MandatoryExpenseRecord(
            date="2025-01-03",
            amount=20.0,
            category="Rent",
            description="Monthly rent",
            period="monthly",
        ),
    ]
    return Report(records, initial_balance=10.0)


def test_export_report_csv_xlsx_pdf(tmp_path: Path):
    report = make_sample_report()

    # CSV
    csv_path = tmp_path / "out" / "report.csv"
    exporters.export_report(report, str(csv_path), "csv")
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert "Date" in text
    assert "FINAL BALANCE" in text

    # XLSX
    xlsx_path = tmp_path / "out" / "report.xlsx"
    exporters.export_report(report, str(xlsx_path), "xlsx")
    assert xlsx_path.exists()
    assert xlsx_path.stat().st_size > 0

    # PDF
    pdf_path = tmp_path / "out" / "report.pdf"
    exporters.export_report(report, str(pdf_path), "pdf")
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_export_and_import_mandatory_expenses_csv_xlsx(tmp_path: Path):
    expenses = [
        MandatoryExpenseRecord(
            date="",
            amount=50.0,
            category="Utilities",
            description="Water",
            period="monthly",
        ),
        MandatoryExpenseRecord(
            date="",
            amount=120.0,
            category="Internet",
            description="ISP",
            period="monthly",
        ),
    ]

    csv_path = tmp_path / "mandatory.csv"
    exporters.export_mandatory_expenses(expenses, str(csv_path), "csv")
    assert csv_path.exists()
    data = importers.import_mandatory_expenses_from_csv(str(csv_path))
    assert len(data) == len(expenses)

    xlsx_path = tmp_path / "mandatory.xlsx"
    exporters.export_mandatory_expenses(expenses, str(xlsx_path), "xlsx")
    assert xlsx_path.exists()
    data2 = importers.import_mandatory_expenses_from_xlsx(str(xlsx_path))
    assert len(data2) == len(expenses)


def test_import_report_from_csv_xlsx_roundtrip(tmp_path: Path):
    report = make_sample_report()
    xlsx_path = tmp_path / "roundtrip.xlsx"
    csv_path = tmp_path / "roundtrip.csv"
    
    # use utils to write a proper xlsx, then import via importers
    from utils.excel_utils import report_to_xlsx

    report_to_xlsx(report, str(xlsx_path))
    imported = importers.import_report_from_xlsx(str(xlsx_path))
    assert imported is not None
    assert len(imported.records()) == len(report.records())
    
    # use utils to write a proper csv, then import via importers
    from utils.csv_utils import report_to_csv
    report_to_csv(report, str(csv_path))
    imported_csv = importers.import_report_from_csv(str(csv_path))
    assert imported_csv is not None
    assert len(imported_csv.records()) == len(report.records())
    
