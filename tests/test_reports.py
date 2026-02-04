from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord


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

    def test_monthly_income_expense_rows_defaults_to_latest_year(self):
        records = [
            IncomeRecord(date="2024-12-31", amount=40.0, category="Old"),
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-02-01", amount=30.0, category="Food"),
        ]
        report = Report(records)
        year, rows = report.monthly_income_expense_rows()
        assert year == 2025
        assert len(rows) == 2
        assert rows[0][0] == "2025-01"
        assert rows[0][1] == 100.0
        assert rows[0][2] == 0.0
        assert rows[1][0] == "2025-02"
        assert rows[1][1] == 0.0
        assert rows[1][2] == 30.0

    def test_monthly_income_expense_rows_with_month_limit(self):
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-02-01", amount=30.0, category="Food"),
            IncomeRecord(date="2025-03-01", amount=50.0, category="Bonus"),
        ]
        report = Report(records)
        year, rows = report.monthly_income_expense_rows(year=2025, up_to_month=2)
        assert year == 2025
        assert len(rows) == 2
        assert rows[0][0] == "2025-01"
        assert rows[1][0] == "2025-02"
