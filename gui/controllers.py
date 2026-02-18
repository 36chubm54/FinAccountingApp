from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha1

from app.use_cases import (
    AddMandatoryExpenseToReport,
    CreateExpense,
    CreateIncome,
    CreateMandatoryExpense,
    DeleteAllMandatoryExpenses,
    DeleteAllRecords,
    DeleteMandatoryExpense,
    DeleteRecord,
    GenerateReport,
    GetMandatoryExpenses,
)
from domain.import_policy import ImportPolicy
from domain.records import IncomeRecord, MandatoryExpenseRecord, Record
from infrastructure.repositories import RecordRepository


@dataclass(frozen=True)
class RecordListItem:
    record_id: str
    repository_index: int
    label: str


class FinancialController:
    def __init__(self, repository: RecordRepository, currency_service) -> None:
        self._repository = repository
        self._currency = currency_service

    def build_record_list_items(self) -> list[RecordListItem]:
        records = self._repository.load_all()
        return self._build_list_items(records)

    def delete_record(self, repository_index: int) -> bool:
        return DeleteRecord(self._repository).execute(repository_index)

    def delete_all_records(self) -> None:
        DeleteAllRecords(self._repository).execute()

    def create_income(self, *, date: str, amount: float, currency: str, category: str) -> None:
        CreateIncome(self._repository, self._currency).execute(
            date=date, amount=amount, currency=currency, category=category
        )

    def create_expense(self, *, date: str, amount: float, currency: str, category: str) -> None:
        CreateExpense(self._repository, self._currency).execute(
            date=date, amount=amount, currency=currency, category=category
        )

    def generate_report(self):
        return GenerateReport(self._repository).execute()

    def create_mandatory_expense(
        self,
        *,
        amount: float,
        currency: str,
        category: str,
        description: str,
        period: str,
    ) -> None:
        CreateMandatoryExpense(self._repository, self._currency).execute(
            amount=amount,
            currency=currency,
            category=category,
            description=description,
            period=period,
        )

    def load_mandatory_expenses(self) -> list[MandatoryExpenseRecord]:
        return GetMandatoryExpenses(self._repository).execute()

    def add_mandatory_to_report(self, mandatory_index: int, record_date: str) -> bool:
        return AddMandatoryExpenseToReport(self._repository).execute(mandatory_index, record_date)

    def delete_mandatory_expense(self, index: int) -> bool:
        return DeleteMandatoryExpense(self._repository).execute(index)

    def delete_all_mandatory_expenses(self) -> None:
        DeleteAllMandatoryExpenses(self._repository).execute()

    def import_records(
        self, fmt: str, filepath: str, policy: ImportPolicy
    ) -> tuple[int, int, list[str]]:
        if fmt == "CSV":
            from gui.importers import import_records_from_csv

            records, initial_balance, summary = import_records_from_csv(
                filepath, policy=policy, currency_service=self._currency
            )
            self._ensure_import_valid(summary)
            self._repository.replace_records(records, initial_balance)
            return summary

        if fmt == "XLSX":
            from gui.importers import import_records_from_xlsx

            records, initial_balance, summary = import_records_from_xlsx(
                filepath, policy=policy, currency_service=self._currency
            )
            self._ensure_import_valid(summary)
            self._repository.replace_records(records, initial_balance)
            return summary

        if fmt == "JSON":
            from gui.importers import import_full_backup

            initial_balance, records, mandatory_expenses, summary = import_full_backup(filepath)
            self._ensure_import_valid(summary)
            self._repository.replace_all_data(
                initial_balance=initial_balance,
                records=records,
                mandatory_expenses=mandatory_expenses,
            )
            return summary

        raise ValueError(f"Unsupported format: {fmt}")

    def import_mandatory(self, fmt: str, filepath: str) -> tuple[int, int, list[str]]:
        if fmt == "CSV":
            from gui.importers import import_mandatory_expenses_from_csv

            expenses, summary = import_mandatory_expenses_from_csv(
                filepath,
                policy=ImportPolicy.FULL_BACKUP,
                currency_service=self._currency,
            )
        elif fmt == "XLSX":
            from gui.importers import import_mandatory_expenses_from_xlsx

            expenses, summary = import_mandatory_expenses_from_xlsx(
                filepath,
                policy=ImportPolicy.FULL_BACKUP,
                currency_service=self._currency,
            )
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        # Keep existing behavior: imported templates are recalculated via use-case.
        self._ensure_import_valid(summary)
        self.delete_all_mandatory_expenses()
        create_use_case = CreateMandatoryExpense(self._repository, self._currency)
        for expense in expenses:
            create_use_case.execute(
                amount=expense.amount_original,
                currency=expense.currency,
                category=expense.category,
                description=expense.description,
                period=expense.period,
            )
        return summary

    @staticmethod
    def _ensure_import_valid(summary: tuple[int, int, list[str]]) -> None:
        _, skipped, errors = summary
        if skipped > 0:
            details = "; ".join(errors[:3]) if errors else "invalid rows"
            raise ValueError(f"Import aborted: {skipped} invalid rows ({details})")

    @staticmethod
    def _build_list_items(records: Iterable[Record]) -> list[RecordListItem]:
        items: list[RecordListItem] = []
        for repository_index, record in enumerate(records):
            amount_original = float(record.amount_original or 0.0)
            amount_kzt = float(record.amount_kzt or 0.0)
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            signature = (
                f"{record.date}|{record_type}|{record.category}|"
                f"{amount_original}|{record.currency}|{amount_kzt}|{repository_index}"
            )
            record_id = sha1(signature.encode("utf-8")).hexdigest()[:12]
            label = (
                f"[{repository_index}] {record.date} - {record_type} - {record.category} - "
                f"{amount_original:.2f} {record.currency} "
                f"(={amount_kzt:.2f} KZT)"
            )
            items.append(
                RecordListItem(
                    record_id=record_id,
                    repository_index=repository_index,
                    label=label,
                )
            )
        return items
