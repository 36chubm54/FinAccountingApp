import logging

from domain.import_policy import ImportPolicy
from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord
from domain.reports import Report
from infrastructure.repositories import RecordRepository

from .services import CurrencyService

logger = logging.getLogger(__name__)
SYSTEM_WALLET_ID = 1


def _build_rate(amount: float, amount_kzt: float, currency: str) -> float:
    if currency.upper() == "KZT":
        return 1.0
    if amount == 0:
        return 1.0
    return amount_kzt / amount


class CreateIncome:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self, *, date: str, amount: float, currency: str, category: str = "General"
    ) -> None:
        """Create and persist an income record."""
        amount_kzt = self._currency.convert(amount, currency)
        record = IncomeRecord(
            date=date,
            wallet_id=SYSTEM_WALLET_ID,
            amount_original=amount,
            currency=currency.upper(),
            rate_at_operation=_build_rate(amount, amount_kzt, currency),
            amount_kzt=amount_kzt,
            category=category,
        )
        self._repository.save(record)


class CreateExpense:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self, *, date: str, amount: float, currency: str, category: str = "General"
    ) -> None:
        """Create and persist an expense record."""
        amount_kzt = self._currency.convert(amount, currency)
        record = ExpenseRecord(
            date=date,
            wallet_id=SYSTEM_WALLET_ID,
            amount_original=amount,
            currency=currency.upper(),
            rate_at_operation=_build_rate(amount, amount_kzt, currency),
            amount_kzt=amount_kzt,
            category=category,
        )
        self._repository.save(record)


class GenerateReport:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, wallet_id: int | None = SYSTEM_WALLET_ID) -> Report:
        return Report(
            self._repository.load_all(),
            self._repository.load_initial_balance(),
            wallet_id=wallet_id,
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
        """Import records from CSV and atomically replace repository data."""
        from utils.csv_utils import import_records_from_csv

        records, initial_balance, summary = import_records_from_csv(
            filepath, policy=ImportPolicy.FULL_BACKUP
        )
        imported_count, skipped_count, _ = summary
        logger.info("CSV import parsed: imported=%s skipped=%s", imported_count, skipped_count)
        if skipped_count > 0:
            logger.warning("CSV import aborted due to validation errors: skipped=%s", skipped_count)
            raise ValueError("Import aborted: CSV contains invalid rows")
        self._repository.replace_records(records, initial_balance)
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
    ) -> None:
        """Create and persist a mandatory expense template."""
        from domain.validation import ensure_valid_period

        ensure_valid_period(period)

        amount_kzt = self._currency.convert(amount, currency)
        expense = MandatoryExpenseRecord(
            date="",  # Will be set when added to report
            wallet_id=SYSTEM_WALLET_ID,
            amount_original=amount,
            currency=currency.upper(),
            rate_at_operation=_build_rate(amount, amount_kzt, currency),
            amount_kzt=amount_kzt,
            category=category,
            description=description,
            period=period,  # type: ignore
        )
        self._repository.save_mandatory_expense(expense)


class GetMandatoryExpenses:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> list[MandatoryExpenseRecord]:
        """Return all mandatory expense templates."""
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
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int, date: str) -> bool:
        """Add selected mandatory expense to records with provided date."""
        mandatory_expenses = self._repository.load_mandatory_expenses()
        if 0 <= index < len(mandatory_expenses):
            expense = mandatory_expenses[index]
            # Create a new record with the specified date
            record = MandatoryExpenseRecord(
                date=date,
                wallet_id=SYSTEM_WALLET_ID,
                amount_original=expense.amount_original,
                currency=expense.currency,
                rate_at_operation=expense.rate_at_operation,
                amount_kzt=expense.amount_kzt,
                category=expense.category,
                description=expense.description,
                period=expense.period,
            )
            self._repository.save(record)
            return True
        return False
