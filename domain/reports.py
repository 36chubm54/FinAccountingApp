from typing import Iterable, Dict
from prettytable import PrettyTable
from .records import Record, IncomeRecord, MandatoryExpenseRecord


class Report:
    def __init__(self, records: Iterable[Record], initial_balance: float = 0.0):
        self._records = list(records)
        self._initial_balance = initial_balance

    def total(self) -> float:
        """Calculate total signed amount of all records including initial balance."""
        return self._initial_balance + sum(r.signed_amount() for r in self._records)

    def filter_by_period(self, prefix: str) -> "Report":
        """Return a new Report with records filtered by date prefix."""
        filtered = [r for r in self._records if r.date.startswith(prefix)]
        return Report(filtered, self._initial_balance)

    def filter_by_category(self, category: str) -> "Report":
        """Return a new Report with records filtered by category."""
        filtered = [r for r in self._records if r.category == category]
        return Report(filtered, self._initial_balance)

    def grouped_by_category(self) -> Dict[str, "Report"]:
        groups = {}
        for record in self._records:
            if record.category not in groups:
                groups[record.category] = []
            groups[record.category].append(record)
        return {
            cat: Report(recs, self._initial_balance) for cat, recs in groups.items()
        }

    def sorted_by_date(self) -> "Report":
        """Return a new Report sorted by date."""
        return Report(
            sorted(self._records, key=lambda r: r.date), self._initial_balance
        )

    def records(self) -> list[Record]:
        return list(self._records)

    def as_table(self) -> str:
        """Return a string representation of records in table format."""
        table = PrettyTable()
        table.field_names = ["Date", "Type", "Category", "Amount (KZT)"]

        # Add initial balance row
        if self._initial_balance != 0:
            balance_str = (
                f"{self._initial_balance:.2f}"
                if self._initial_balance >= 0
                else f"({abs(self._initial_balance):.2f})"
            )
            table.add_row(["", "Initial Balance", "", balance_str])

        sorted_records = sorted(self._records, key=lambda r: r.date)

        for record in sorted_records:
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            amount_str = (
                f"{record.amount:.2f}"
                if record.amount >= 0
                else f"({abs(record.amount):.2f})"
            )
            table.add_row([record.date, record_type, record.category, amount_str])

        # Add total row for records
        records_total = sum(r.signed_amount() for r in self._records)
        records_total_str = (
            f"{records_total:.2f}"
            if records_total >= 0
            else f"({abs(records_total):.2f})"
        )
        table.add_row(["SUBTOTAL", "", "", records_total_str], divider=True)

        # Add final balance row
        final_balance = self.total()
        final_balance_str = (
            f"{final_balance:.2f}"
            if final_balance >= 0
            else f"({abs(final_balance):.2f})"
        )
        table.add_row(["FINAL BALANCE", "", "", final_balance_str], divider=True)

        return str(table)

    def to_csv(self, filepath: str) -> None:
        """Export the report to a CSV file."""
        from utils.csv_utils import report_to_csv

        report_to_csv(self, filepath)

    @staticmethod
    def from_csv(filepath: str) -> "Report":
        """Import records from a CSV file and return a new Report."""
        from utils.csv_utils import report_from_csv

        return report_from_csv(filepath)
