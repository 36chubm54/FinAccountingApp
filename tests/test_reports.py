from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord
import csv
import tempfile
import os
import pytest


class TestReport:
    def test_creation(self):
        records = [IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")]
        report = Report(records)
        assert report.records() == records

    def test_creation_with_initial_balance(self):
        records = [IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")]
        report = Report(records, initial_balance=50.0)
        assert report.records() == records
        assert report.total() == 150.0

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
        report = Report(records, initial_balance=20.0)
        jan_report = report.filter_by_period("2025-01")
        assert len(jan_report.records()) == 2
        assert jan_report.total() == 170.0  # 20 + 100 + 50

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
        assert "SUBTOTAL" in table_str
        assert "FINAL BALANCE" in table_str

    def test_as_table_with_initial_balance(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
        ]
        report = Report(records, initial_balance=50.0)
        table_str = report.as_table()
        assert "Initial Balance" in table_str
        assert "50.00" in table_str
        assert "SUBTOTAL" in table_str
        assert "70.00" in table_str  # 100 - 30
        assert "FINAL BALANCE" in table_str
        assert "120.00" in table_str  # 50 + 70

    def test_to_csv(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
        ]
        report = Report(records)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            tmp_path = tmp.name
        try:
            report.to_csv(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert rows[0] == ["Date", "Type", "Category", "Amount (KZT)"]
            assert rows[1] == ["2025-01-01", "Income", "Salary", "100.00"]
            assert rows[2] == ["2025-01-02", "Expense", "Food", "30.00"]
            assert rows[3] == ["TOTAL", "", "", "70.00"]
        finally:
            os.unlink(tmp_path)

    def test_to_csv_with_initial_balance(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=30.0, category="Food"),
        ]
        report = Report(records, initial_balance=50.0)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            tmp_path = tmp.name
        try:
            report.to_csv(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert rows[0] == ["Date", "Type", "Category", "Amount (KZT)"]
            assert rows[1] == ["", "Initial Balance", "", "50.00"]
            assert rows[2] == ["2025-01-01", "Income", "Salary", "100.00"]
            assert rows[3] == ["2025-01-02", "Expense", "Food", "30.00"]
            assert rows[4] == ["TOTAL", "", "", "120.00"]
        finally:
            os.unlink(tmp_path)

    def test_from_csv(self):
        # Create a temporary CSV file
        csv_content = """Date,Type,Category,Amount (KZT)
2025-01-01,Income,Salary,100000.00
2025-01-02,Expense,Food,15000.00
2025-01-03,Income,Bonus,50000.00
TOTAL,,,-2000.00"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv", newline=""
        ) as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
        try:
            report = Report.from_csv(tmp_path)
            records = report.records()
            assert len(records) == 3

            # Check first record (Income)
            assert records[0].date == "2025-01-01"
            assert isinstance(records[0], IncomeRecord)
            assert records[0].category == "Salary"
            assert records[0].amount == 100000.0

            # Check second record (Expense)
            assert records[1].date == "2025-01-02"
            assert isinstance(records[1], ExpenseRecord)
            assert records[1].category == "Food"
            assert records[1].amount == 15000.0

            # Check third record (Income)
            assert records[2].date == "2025-01-03"
            assert isinstance(records[2], IncomeRecord)
            assert records[2].category == "Bonus"
            assert records[2].amount == 50000.0

        finally:
            os.unlink(tmp_path)

    def test_from_csv_with_negative_amounts(self):
        # Test CSV with negative amounts (expenses)
        csv_content = """Date,Type,Category,Amount (KZT)
2025-01-01,Income,Salary,100.00
2025-01-02,Expense,Food,(50.00)
TOTAL,,,-50.00"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv", newline=""
        ) as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
        try:
            report = Report.from_csv(tmp_path)
            records = report.records()
            assert len(records) == 2

            assert records[0].amount == 100.0
            assert records[1].amount == 50.0  # Should be positive for ExpenseRecord

        finally:
            os.unlink(tmp_path)

    def test_from_csv_with_initial_balance(self):
        # Test CSV import with initial balance
        csv_content = """Date,Type,Category,Amount (KZT)
,Initial Balance,,50000.00
2025-01-01,Income,Salary,100000.00
2025-01-02,Expense,Food,15000.00
TOTAL,,,-2000.00"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".csv", newline=""
        ) as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
        try:
            report = Report.from_csv(tmp_path)
            records = report.records()
            assert len(records) == 2
            assert report._initial_balance == 50000.0
            assert report.total() == 135000.0  # 50000 + 100000 - 15000

        finally:
            os.unlink(tmp_path)

    def test_from_csv_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Report.from_csv("nonexistent_file.csv")
