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
        return Report(self._repository.load_all())


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
