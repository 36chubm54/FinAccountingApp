from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from domain.reports import Report
from infrastructure.repositories import RecordRepository
from .services import CurrencyService


class CreateIncome:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self, *, date: str, amount: float, currency: str, category: str = "General"
    ):
        normalized = self._currency.convert(amount, currency)
        record = IncomeRecord(date=date, amount=normalized, category=category)
        self._repository.save(record)


class CreateExpense:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self, *, date: str, amount: float, currency: str, category: str = "General"
    ):
        normalized = self._currency.convert(amount, currency)
        record = ExpenseRecord(date=date, amount=normalized, category=category)
        self._repository.save(record)


class GenerateReport:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> Report:
        return Report(
            self._repository.load_all(), self._repository.load_initial_balance()
        )


class DeleteRecord:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int) -> bool:
        """Delete record by index. Returns True if deleted successfully."""
        return self._repository.delete_by_index(index)


class DeleteAllRecords:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> None:
        """Delete all records."""
        self._repository.delete_all()


class ImportFromCSV:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, filepath: str) -> int:
        """Import records from CSV file, replace all existing records in repository. Returns number of imported records."""
        report = Report.from_csv(filepath)

        # Delete all existing records first
        self._repository.delete_all()

        # Import new records
        imported_count = 0
        for record in report.records():
            self._repository.save(record)
            imported_count += 1
        return imported_count


class CreateMandatoryExpense:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self,
        *,
        amount: float,
        currency: str,
        category: str,
        description: str,
        period: str,
    ):
        from typing import Literal

        valid_periods: list[Literal["daily", "weekly", "monthly", "yearly"]] = [
            "daily",
            "weekly",
            "monthly",
            "yearly",
        ]
        if period not in valid_periods:
            raise ValueError(
                f"Invalid period: {period}. Must be one of {valid_periods}"
            )

        normalized = self._currency.convert(amount, currency)
        expense = MandatoryExpenseRecord(
            date="",  # Will be set when added to report
            amount=normalized,
            category=category,
            description=description,
            period=period,  # type: ignore
        )
        self._repository.save_mandatory_expense(expense)


class GetMandatoryExpenses:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> list[MandatoryExpenseRecord]:
        return self._repository.load_mandatory_expenses()


class DeleteMandatoryExpense:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int) -> bool:
        """Delete mandatory expense by index. Returns True if deleted."""
        return self._repository.delete_mandatory_expense_by_index(index)


class DeleteAllMandatoryExpenses:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> None:
        """Delete all mandatory expenses."""
        self._repository.delete_all_mandatory_expenses()


class AddMandatoryExpenseToReport:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(self, index: int, date: str):
        mandatory_expenses = self._repository.load_mandatory_expenses()
        if 0 <= index < len(mandatory_expenses):
            expense = mandatory_expenses[index]
            # Create a new record with the specified date
            record = MandatoryExpenseRecord(
                date=date,
                amount=expense.amount,
                category=expense.category,
                description=expense.description,
                period=expense.period,
            )
            self._repository.save(record)
            return True
        return False
