import sys
from pathlib import Path
import argparse

from infrastructure.repositories import JsonFileRecordRepository
from app.use_cases import CreateIncome, CreateExpense, GenerateReport, DeleteRecord
from domain.records import IncomeRecord
from app.services import CurrencyService

# Ensure project package root is on sys.path so imports work regardless of CWD
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Financial Accounting CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add income command
    income_parser = subparsers.add_parser("add-income", help="Add income record")
    income_parser.add_argument(
        "--date", required=True, help="Date in YYYY-MM-DD format"
    )
    income_parser.add_argument("--amount", type=float, required=True, help="Amount")
    income_parser.add_argument(
        "--currency", default="KZT", help="Currency (default: KZT)"
    )
    income_parser.add_argument(
        "--category", default="General", help="Category (default: General)"
    )

    # Add expense command
    expense_parser = subparsers.add_parser("add-expense", help="Add expense record")
    expense_parser.add_argument(
        "--date", required=True, help="Date in YYYY-MM-DD format"
    )
    expense_parser.add_argument("--amount", type=float, required=True, help="Amount")
    expense_parser.add_argument(
        "--currency", default="KZT", help="Currency (default: KZT)"
    )
    expense_parser.add_argument(
        "--category", default="General", help="Category (default: General)"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate financial report")
    report_parser.add_argument(
        "--period", help="Filter by period (e.g., 2025-03 for March 2025)"
    )
    report_parser.add_argument("--category", help="Filter by category")
    report_parser.add_argument(
        "--group-by-category", action="store_true", help="Group results by category"
    )
    report_parser.add_argument(
        "--table", action="store_true", help="Display records in table format"
    )

    # Delete command
    subparsers.add_parser("delete", help="Delete a record interactively")

    args = parser.parse_args()

    repository = JsonFileRecordRepository()
    currency = CurrencyService()

    if args.command == "add-income":
        create_income = CreateIncome(repository, currency)
        create_income.execute(
            date=args.date,
            amount=args.amount,
            currency=args.currency,
            category=getattr(args, "category", "General"),
        )
        print(
            f"Added income: {args.amount} {args.currency} on {args.date} (category: {getattr(args, 'category', 'General')})"
        )

    elif args.command == "add-expense":
        create_expense = CreateExpense(repository, currency)
        create_expense.execute(
            date=args.date,
            amount=args.amount,
            currency=args.currency,
            category=getattr(args, "category", "General"),
        )
        print(
            f"Added expense: {args.amount} {args.currency} on {args.date} (category: {getattr(args, 'category', 'General')})"
        )

    elif args.command == "report":
        report = GenerateReport(repository).execute()
        if args.period:
            report = report.filter_by_period(args.period)
        if getattr(args, "category", None):
            report = report.filter_by_category(args.category)
        if getattr(args, "group_by_category", False):
            if getattr(args, "table", False):
                print("Detailed report grouped by category:")
                groups = report.grouped_by_category()
                for cat, cat_report in groups.items():
                    print(f"\nCategory: {cat}")
                    print(cat_report.as_table())
            else:
                groups = report.grouped_by_category()
                print("Report grouped by category:")
                for cat, cat_report in groups.items():
                    total = cat_report.total()
                    print(f"  {cat}: {total:.2f} KZT")
        elif getattr(args, "table", False):
            print(report.as_table())
            filters = []
            if args.period:
                filters.append(f"period: {args.period}")
            if getattr(args, "category", None):
                filters.append(f"category: {args.category}")
            if filters:
                print(f"Filtered by {', '.join(filters)}")
        else:
            total = report.total()
            print(f"Total: {total:.2f} KZT")
            filters = []
            if args.period:
                filters.append(f"period: {args.period}")
            if getattr(args, "category", None):
                filters.append(f"category: {args.category}")
            if filters:
                print(f"(Filtered by {', '.join(filters)})")

    elif args.command == "delete":
        # First show all records with indices
        all_records = repository.load_all()
        if not all_records:
            print("No records to delete.")
            return

        print("Current records:")
        for i, record in enumerate(all_records):
            record_type = "Income" if isinstance(record, IncomeRecord) else "Expense"
            print(
                f"[{i}] {record.date} - {record_type} - {record.category} - {record.amount:.2f} KZT"
            )

        # Ask for index to delete
        try:
            index_input = input(
                "\nEnter the index of the record to delete (or 'cancel' to abort): "
            ).strip()

            if index_input.lower() == "cancel":
                print("Deletion cancelled.")
                return

            index = int(index_input)

            # Validate and delete
            delete_use_case = DeleteRecord(repository)
            if delete_use_case.execute(index):
                print(f"Successfully deleted record at index {index}.")
            else:
                print(
                    f"Error: Invalid index {index}. Index must be between 0 and {len(all_records) - 1}"
                )

        except ValueError:
            print("Error: Please enter a valid number or 'cancel'.")
        except KeyboardInterrupt:
            print("\nDeletion cancelled.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
