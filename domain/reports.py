from typing import Iterable, Dict
from prettytable import PrettyTable
from .records import Record, IncomeRecord, ExpenseRecord
import csv
import os


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

    def to_csv(self, filepath: str) -> None:
        """Export the report to a CSV file."""
        sorted_records = sorted(self._records, key=lambda r: r.date)
        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Date", "Type", "Category", "Amount (KZT)"])
            for record in sorted_records:
                record_type = (
                    "Income" if isinstance(record, IncomeRecord) else "Expense"
                )
                writer.writerow(
                    [record.date, record_type, record.category, f"{record.amount:.2f}"]
                )
            # Add total row
            total = self.total()
            writer.writerow(["TOTAL", "", "", f"{total:.2f}"])

    @staticmethod
    def from_csv(filepath: str) -> "Report":
        """Import records from a CSV file and return a new Report."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        records = []
        with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)  # Skip header row

            for row in reader:
                if len(row) < 4:
                    continue  # Skip malformed rows

                date, record_type, category, amount_str = row[:4]

                # Skip total row
                if date.upper() == "TOTAL":
                    continue

                try:
                    # Parse amount, remove parentheses if present
                    amount_str = amount_str.strip()
                    if amount_str.startswith("(") and amount_str.endswith(")"):
                        amount_str = "-" + amount_str[1:-1]
                    amount = float(amount_str)
                except ValueError:
                    continue  # Skip rows with invalid amount

                # Determine record type
                if record_type.lower() == "income":
                    record = IncomeRecord(
                        date=date, amount=abs(amount), category=category
                    )
                elif record_type.lower() == "expense":
                    record = ExpenseRecord(
                        date=date, amount=abs(amount), category=category
                    )
                else:
                    continue  # Skip unknown record types

                records.append(record)

        return Report(records)
