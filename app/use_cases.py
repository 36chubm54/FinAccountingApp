from domain.records import IncomeRecord, ExpenseRecord
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
        return Report(self._repository.load_all(), self._repository.load_initial_balance())


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
