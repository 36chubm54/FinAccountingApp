from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord
import csv
import tempfile
import os


class TestReport:
    def test_creation(self):
        records = [IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")]
        report = Report(records)
        assert report.records() == records

    def test_total_empty(self):
        report = Report([])
        assert report.total() == 0.0

    def test_total_single_income(self):
        records = [IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")]
        report = Report(records)
        assert report.total() == 100.0

    def test_total_single_expense(self):
        records = [ExpenseRecord(date="2025-01-01", amount=50.0, category="Food")]
        report = Report(records)
        assert report.total() == -50.0

    def test_total_multiple_records(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
            IncomeRecord(date="2025-01-03", amount=50.0, category="Bonus"),
        ]
        report = Report(records)
        assert report.total() == 120.0  # 100 - 30 + 50

    def test_filter_by_period(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-02-01", amount=30.0, category="Food"),
            IncomeRecord(date="2025-01-15", amount=50.0, category="Bonus"),
        ]
        report = Report(records)
        jan_report = report.filter_by_period("2025-01")
        assert len(jan_report.records()) == 2
        assert jan_report.total() == 150.0  # 100 + 50

    def test_filter_by_category(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
            IncomeRecord(date="2025-01-03", amount=50.0, category="Salary"),
        ]
        report = Report(records)
        salary_report = report.filter_by_category("Salary")
        assert len(salary_report.records()) == 2
        assert salary_report.total() == 150.0  # 100 + 50

    def test_grouped_by_category(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
            IncomeRecord(date="2025-01-03", amount=50.0, category="Salary"),
            ExpenseRecord(date="2025-01-04", amount=20.0, category="Food"),
        ]
        report = Report(records)
        groups = report.grouped_by_category()
        assert "Salary" in groups
        assert "Food" in groups
        assert groups["Salary"].total() == 150.0  # 100 + 50
        assert groups["Food"].total() == -50.0  # -30 - 20

    def test_sorted_by_date(self):
        records = [
            IncomeRecord(date="2025-01-03", amount=50.0, category="Bonus"),
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            IncomeRecord(date="2025-01-02", amount=25.0, category="Salary"),
        ]
        report = Report(records)
        sorted_report = report.sorted_by_date()
        sorted_dates = [r.date for r in sorted_report.records()]
        assert sorted_dates == ["2025-01-01", "2025-01-02", "2025-01-03"]

    def test_records_returns_copy(self):
        records = [IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")]
        report = Report(records)
        returned_records = report.records()
        returned_records.append(
            ExpenseRecord(date="2025-01-02", amount=50.0, category="Food")
        )
        assert len(report.records()) == 1  # Original unchanged

    def test_as_table(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
        ]
        report = Report(records)
        table_str = report.as_table()
        assert "Date" in table_str
        assert "Type" in table_str
        assert "Category" in table_str
        assert "Amount" in table_str
        assert "Salary" in table_str
        assert "Food" in table_str
        assert "TOTAL" in table_str

    def test_to_csv(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
        ]
        report = Report(records)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name
        try:
            report.to_csv(tmp_path)
            with open(tmp_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert rows[0] == ["Date", "Type", "Category", "Amount (KZT)"]
            assert rows[1] == ["2025-01-01", "Income", "Salary", "100.00"]
            assert rows[2] == ["2025-01-02", "Expense", "Food", "30.00"]
            assert rows[3] == ["TOTAL", "", "", "70.00"]
        finally:
            os.unlink(tmp_path)
