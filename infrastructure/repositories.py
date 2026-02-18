import json
import logging
import os
import tempfile
import threading
from abc import ABC, abstractmethod

from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord, Record

logger = logging.getLogger(__name__)


class RecordRepository(ABC):
    @abstractmethod
    def save(self, record: Record) -> None:
        pass

    @abstractmethod
    def load_all(self) -> list[Record]:
        pass

    @abstractmethod
    def delete_by_index(self, index: int) -> bool:
        """Delete record by index. Returns True if deleted, False if index out of range."""
        pass

    @abstractmethod
    def delete_all(self) -> None:
        """Delete all records."""
        pass

    @abstractmethod
    def save_initial_balance(self, balance: float) -> None:
        """Save initial balance."""
        pass

    @abstractmethod
    def load_initial_balance(self) -> float:
        """Load initial balance. Returns 0.0 if not set."""
        pass

    @abstractmethod
    def save_mandatory_expense(self, expense: MandatoryExpenseRecord) -> None:
        """Save mandatory expense."""
        pass

    @abstractmethod
    def load_mandatory_expenses(self) -> list[MandatoryExpenseRecord]:
        """Load all mandatory expenses."""
        pass

    @abstractmethod
    def delete_mandatory_expense_by_index(self, index: int) -> bool:
        """Delete mandatory expense by index. Returns True if deleted."""
        pass

    @abstractmethod
    def delete_all_mandatory_expenses(self) -> None:
        """Delete all mandatory expenses."""
        pass

    @abstractmethod
    def replace_records(self, records: list[Record], initial_balance: float) -> None:
        """Atomically replace all records and initial balance."""
        pass

    @abstractmethod
    def replace_mandatory_expenses(self, expenses: list[MandatoryExpenseRecord]) -> None:
        """Atomically replace mandatory expenses."""
        pass

    @abstractmethod
    def replace_all_data(
        self,
        *,
        initial_balance: float,
        records: list[Record],
        mandatory_expenses: list[MandatoryExpenseRecord],
    ) -> None:
        """Atomically replace full repository dataset."""
        pass


class JsonFileRecordRepository(RecordRepository):
    _path_locks: dict[str, threading.RLock] = {}
    _path_locks_guard = threading.Lock()

    def __init__(self, file_path: str = "records.json"):
        self._file_path = file_path
        abs_path = os.path.abspath(file_path)
        with self._path_locks_guard:
            if abs_path not in self._path_locks:
                self._path_locks[abs_path] = threading.RLock()
            self._lock = self._path_locks[abs_path]

    def _load_data(self) -> dict:
        with self._lock:
            try:
                with open(self._file_path, encoding="utf-8") as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.warning(
                    "Failed to load JSON data from %s, using empty dataset",
                    self._file_path,
                )
                return {"initial_balance": 0.0, "records": [], "mandatory_expenses": []}
        if isinstance(data, list):
            # Migrate old format
            logger.info("Migrating JSON repository format: list -> object")
            data = {"initial_balance": 0.0, "records": data}
        if not isinstance(data, dict):
            logger.info("Migrating JSON repository format: invalid root -> default object")
            data = {"initial_balance": 0.0, "records": [], "mandatory_expenses": []}

        if "initial_balance" not in data or not isinstance(
            data.get("initial_balance"), (int, float)
        ):
            data["initial_balance"] = 0.0
        if "records" not in data or not isinstance(data.get("records"), list):
            data["records"] = []
        if "mandatory_expenses" not in data or not isinstance(data.get("mandatory_expenses"), list):
            data["mandatory_expenses"] = []
        return data

    def _save_data(self, data: dict) -> None:
        with self._lock:
            directory = os.path.dirname(self._file_path) or "."
            fd, tmp_path = tempfile.mkstemp(prefix=".records_", suffix=".json", dir=directory)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self._file_path)
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    logger.exception("Failed to cleanup temporary file during save: %s", tmp_path)

    @staticmethod
    def _as_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _record_to_dict(self, record: Record, record_type: str) -> dict:
        payload = {
            "type": record_type,
            "date": record.date,
            "amount_original": record.amount_original,
            "currency": record.currency,
            "rate_at_operation": record.rate_at_operation,
            "amount_kzt": record.amount_kzt,
            "category": record.category,
        }
        if isinstance(record, MandatoryExpenseRecord):
            payload["description"] = record.description
            payload["period"] = record.period
        return payload

    def _parse_record_common(self, item: dict) -> dict:
        # Lazy migration for legacy records without amount_kzt.
        if "amount_kzt" in item:
            amount_kzt = self._as_float(item.get("amount_kzt", 0.0), 0.0)
            amount_original = self._as_float(item.get("amount_original", amount_kzt), amount_kzt)
            currency = str(item.get("currency", "KZT") or "KZT").upper()
            rate_at_operation = self._as_float(item.get("rate_at_operation", 1.0), 1.0)
        else:
            legacy_amount = self._as_float(item.get("amount", 0.0), 0.0)
            amount_original = legacy_amount
            amount_kzt = legacy_amount
            currency = "KZT"
            rate_at_operation = 1.0

        return {
            "date": str(item.get("date", "") or ""),
            "amount_original": amount_original,
            "currency": currency,
            "rate_at_operation": rate_at_operation,
            "amount_kzt": amount_kzt,
            "category": str(item.get("category", "General") or "General"),
        }

    def save(self, record: Record) -> None:
        with self._lock:
            data = self._load_data()
            if isinstance(record, MandatoryExpenseRecord):
                record_data = self._record_to_dict(record, "mandatory_expense")
            else:
                record_data = self._record_to_dict(
                    record, "income" if isinstance(record, IncomeRecord) else "expense"
                )
            data["records"].append(record_data)
            self._save_data(data)

    def load_all(self) -> list[Record]:
        data = self._load_data()
        records = []
        for index, item in enumerate(data.get("records", [])):
            if not isinstance(item, dict):
                logger.warning("Skipping non-dict record at index %s", index)
                continue
            try:
                typ = item.get("type", "income")
                common = self._parse_record_common(item)

                if typ == "income":
                    record = IncomeRecord(**common)
                elif typ == "expense":
                    record = ExpenseRecord(**common)
                elif typ == "mandatory_expense":
                    description = str(item.get("description", "") or "")
                    period = str(item.get("period", "monthly") or "monthly")
                    record = MandatoryExpenseRecord(
                        **common,
                        description=description,
                        period=period,  # type: ignore[arg-type]
                    )
                else:
                    logger.warning("Unknown record type '%s' at index %s, skipping", typ, index)
                    continue
                records.append(record)
            except Exception as e:
                logger.exception("Skipping invalid record at index %s: %s", index, e)
                continue
        return records

    def delete_by_index(self, index: int) -> bool:
        """Delete record by index. Returns True if deleted, False if index out of range."""
        with self._lock:
            data = self._load_data()
            if 0 <= index < len(data["records"]):
                data["records"].pop(index)
                self._save_data(data)
                return True
            return False

    def delete_all(self) -> None:
        """Delete all records."""
        with self._lock:
            data = self._load_data()
            data["records"] = []
            self._save_data(data)

    def save_initial_balance(self, balance: float) -> None:
        """Save initial balance."""
        with self._lock:
            data = self._load_data()
            data["initial_balance"] = balance
            self._save_data(data)

    def load_initial_balance(self) -> float:
        """Load initial balance. Returns 0.0 if not set."""
        data = self._load_data()
        return data.get("initial_balance", 0.0)

    def save_mandatory_expense(self, expense: MandatoryExpenseRecord) -> None:
        """Save mandatory expense."""
        with self._lock:
            data = self._load_data()
            if "mandatory_expenses" not in data:
                data["mandatory_expenses"] = []
            expense_data = self._record_to_dict(expense, "mandatory_expense")
            expense_data.pop("type", None)
            data["mandatory_expenses"].append(expense_data)
            self._save_data(data)

    def load_mandatory_expenses(self) -> list[MandatoryExpenseRecord]:
        """Load all mandatory expenses."""
        data = self._load_data()
        expenses = []
        for index, item in enumerate(data.get("mandatory_expenses", [])):
            if not isinstance(item, dict):
                logger.warning("Skipping non-dict mandatory expense at index %s", index)
                continue
            common = self._parse_record_common(item)
            expense = MandatoryExpenseRecord(
                **common,
                description=str(item.get("description", "") or ""),
                period=str(item.get("period", "monthly") or "monthly"),  # type: ignore[arg-type]
            )
            expenses.append(expense)
        return expenses

    def delete_mandatory_expense_by_index(self, index: int) -> bool:
        """Delete mandatory expense by index. Returns True if deleted."""
        with self._lock:
            data = self._load_data()
            if "mandatory_expenses" in data and 0 <= index < len(data["mandatory_expenses"]):
                data["mandatory_expenses"].pop(index)
                self._save_data(data)
                return True
            return False

    def delete_all_mandatory_expenses(self) -> None:
        """Delete all mandatory expenses."""
        with self._lock:
            data = self._load_data()
            data["mandatory_expenses"] = []
            self._save_data(data)

    def replace_records(self, records: list[Record], initial_balance: float) -> None:
        with self._lock:
            data = self._load_data()
            data["initial_balance"] = float(initial_balance)
            data["records"] = []
            for record in records:
                if isinstance(record, MandatoryExpenseRecord):
                    data["records"].append(self._record_to_dict(record, "mandatory_expense"))
                else:
                    record_type = "income" if isinstance(record, IncomeRecord) else "expense"
                    data["records"].append(self._record_to_dict(record, record_type))
            self._save_data(data)

    def replace_mandatory_expenses(self, expenses: list[MandatoryExpenseRecord]) -> None:
        with self._lock:
            data = self._load_data()
            data["mandatory_expenses"] = []
            for expense in expenses:
                payload = self._record_to_dict(expense, "mandatory_expense")
                payload.pop("type", None)
                data["mandatory_expenses"].append(payload)
            self._save_data(data)

    def replace_all_data(
        self,
        *,
        initial_balance: float,
        records: list[Record],
        mandatory_expenses: list[MandatoryExpenseRecord],
    ) -> None:
        with self._lock:
            data = {
                "initial_balance": float(initial_balance),
                "records": [],
                "mandatory_expenses": [],
            }
            for record in records:
                if isinstance(record, MandatoryExpenseRecord):
                    data["records"].append(self._record_to_dict(record, "mandatory_expense"))
                else:
                    record_type = "income" if isinstance(record, IncomeRecord) else "expense"
                    data["records"].append(self._record_to_dict(record, record_type))
            for expense in mandatory_expenses:
                payload = self._record_to_dict(expense, "mandatory_expense")
                payload.pop("type", None)
                data["mandatory_expenses"].append(payload)
            self._save_data(data)
