from typing import Iterable, Dict
from prettytable import PrettyTable
from .records import Record, IncomeRecord


class Report:
    def __init__(self, records: Iterable[Record]):
        self._records = list(records)

    def total(self) -> float:
        """Calculate total signed amount of all records."""
        return sum(r.signed_amount() for r in self._records)

    def filter_by_period(self, prefix: str) -> "Report":
        """Return a new Report with records filtered by date prefix."""
        filtered = [r for r in self._records if r.date.startswith(prefix)]
        return Report(filtered)

    def filter_by_category(self, category: str) -> "Report":
        """Return a new Report with records filtered by category."""
        filtered = [r for r in self._records if r.category == category]
        return Report(filtered)

    def grouped_by_category(self) -> Dict[str, "Report"]:
        groups = {}
        for record in self._records:
            if record.category not in groups:
                groups[record.category] = []
            groups[record.category].append(record)
        return {cat: Report(recs) for cat, recs in groups.items()}

    def sorted_by_date(self) -> "Report":
        """Return a new Report sorted by date."""
        return Report(sorted(self._records, key=lambda r: r.date))

    def records(self) -> list[Record]:
        return list(self._records)

    def as_table(self) -> str:
        """Return a string representation of records in table format."""
        table = PrettyTable()
        table.field_names = ["Date", "Type", "Category", "Amount (KZT)"]

        sorted_records = sorted(self._records, key=lambda r: r.date)

        for record in sorted_records:
            record_type = "Income" if isinstance(record, IncomeRecord) else "Expense"
            amount_str = (
                f"{record.amount:.2f}"
                if record.amount >= 0
                else f"({abs(record.amount):.2f})"
            )
            table.add_row([record.date, record_type, record.category, amount_str])

        # Add total row
        total = self.total()
        total_str = f"{total:.2f}" if total >= 0 else f"({abs(total):.2f})"
        table.add_row(["TOTAL", "", "", total_str], divider=True)

        return str(table)
