from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord
import csv
import tempfile
import os
import pytest


def test_to_csv():
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
        assert rows[3] == ["SUBTOTAL", "", "", "70.00"]
    finally:
        os.unlink(tmp_path)


def test_to_csv_with_initial_balance():
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
        assert rows[4] == ["SUBTOTAL", "", "", "70.00"]
        assert rows[5] == ["FINAL BALANCE", "", "", "120.00"]
    finally:
        os.unlink(tmp_path)


def test_from_csv():
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


def test_from_csv_with_negative_amounts():
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


def test_from_csv_with_initial_balance():
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


def test_from_csv_file_not_found():
    with pytest.raises(FileNotFoundError):
        Report.from_csv("nonexistent_file.csv")
