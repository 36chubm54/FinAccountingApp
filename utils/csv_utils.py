import csv
import os
from typing import List
from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from domain.reports import Report


def report_to_csv(report: Report, filepath: str) -> None:
    """Export the report to a CSV file."""
    sorted_records = sorted(report.records(), key=lambda r: r.date)
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Type", "Category", "Amount (KZT)"])

        # Add initial balance row if not zero
        if report._initial_balance != 0:
            writer.writerow(
                ["", "Initial Balance", "", f"{report._initial_balance:.2f}"]
            )

        for record in sorted_records:
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            writer.writerow(
                [record.date, record_type, record.category, f"{record.amount:.2f}"]
            )
        # Add total rows
        total = report.total()
        writer.writerow(
            [
                "SUBTOTAL",
                "",
                "",
                f"{sum(r.signed_amount() for r in report.records()):.2f}",
            ]
        )
        writer.writerow(["FINAL BALANCE", "", "", f"{total:.2f}"])


def report_from_csv(filepath: str) -> Report:
    """Import records from a CSV file and return a new Report."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    records = []
    initial_balance = 0.0

    with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header row

        for row in reader:
            if len(row) < 4:
                continue  # Skip malformed rows

            date, record_type, category, amount_str = row[:4]

            # Skip total row
            if date.upper() in ["SUBTOTAL", "FINAL BALANCE"]:
                continue

            # Check for initial balance row
            if date.strip() == "" and record_type.strip().lower() == "initial balance":
                try:
                    initial_balance = float(amount_str)
                    continue
                except ValueError:
                    continue  # Skip malformed initial balance

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
                record = IncomeRecord(date=date, amount=abs(amount), category=category)
            elif record_type.lower() == "expense":
                record = ExpenseRecord(date=date, amount=abs(amount), category=category)
            elif record_type.lower() == "mandatory expense":
                record = MandatoryExpenseRecord(
                    date=date,
                    amount=abs(amount),
                    category=category,
                    description="",
                    period="monthly",  # Default values for import
                )
            else:
                continue  # Skip unknown record types

            records.append(record)

    return Report(records, initial_balance)


def export_mandatory_expenses_to_csv(
    expenses: List[MandatoryExpenseRecord], filepath: str
) -> None:
    """Export mandatory expenses to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Amount (KZT)", "Category", "Description", "Period"])

        for expense in expenses:
            writer.writerow(
                [
                    f"{expense.amount:.2f}",
                    expense.category,
                    expense.description,
                    expense.period,
                ]
            )


def import_mandatory_expenses_from_csv(filepath: str) -> List[MandatoryExpenseRecord]:
    """Import mandatory expenses from a CSV file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    expenses = []

    with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header row

        for row in reader:
            if len(row) < 4:
                continue  # Skip malformed rows

            try:
                amount_str, category, description, period = row[:4]

                # Parse amount
                amount = float(amount_str.strip())

                # Validate period
                valid_periods = ["daily", "weekly", "monthly", "yearly"]
                if period.strip().lower() not in valid_periods:
                    continue  # Skip invalid periods

                # Create mandatory expense record
                expense = MandatoryExpenseRecord(
                    date="",  # Date will be empty for mandatory expenses (set when added to report)
                    amount=amount,
                    category=category.strip(),
                    description=description.strip(),
                    period=period.strip().lower(),  # type: ignore
                )
                expenses.append(expense)

            except ValueError:
                continue  # Skip rows with invalid amount

    return expenses
