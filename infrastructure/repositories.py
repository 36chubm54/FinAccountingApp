import json
import os
import tempfile
import logging
from abc import ABC, abstractmethod
from domain.records import Record, IncomeRecord, ExpenseRecord, MandatoryExpenseRecord

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


class JsonFileRecordRepository(RecordRepository):
    def __init__(self, file_path: str = "records.json"):
        self._file_path = file_path

    def _load_data(self) -> dict:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(
                "Failed to load JSON data from %s, using empty dataset", self._file_path
            )
            return {"initial_balance": 0.0, "records": [], "mandatory_expenses": []}
        if isinstance(data, list):
            # Migrate old format
            data = {"initial_balance": 0.0, "records": data}
        if not isinstance(data, dict):
            data = {"initial_balance": 0.0, "records": [], "mandatory_expenses": []}

        if "initial_balance" not in data or not isinstance(
            data.get("initial_balance"), (int, float)
        ):
            data["initial_balance"] = 0.0
        if "records" not in data or not isinstance(data.get("records"), list):
            data["records"] = []
        if "mandatory_expenses" not in data or not isinstance(
            data.get("mandatory_expenses"), list
        ):
            data["mandatory_expenses"] = []
        return data

    def _save_data(self, data: dict) -> None:
        directory = os.path.dirname(self._file_path) or "."
        fd, tmp_path = tempfile.mkstemp(
            prefix=".records_", suffix=".json", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._file_path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

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
            amount_original = self._as_float(
                item.get("amount_original", amount_kzt), amount_kzt
            )
            currency = str(item.get("currency", "KZT") or "KZT").upper()
            rate_at_operation = self._as_float(
                item.get("rate_at_operation", 1.0), 1.0
            )
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
                    logger.warning(
                        "Unknown record type '%s' at index %s, skipping", typ, index
                    )
                    continue
                records.append(record)
            except Exception as e:
                logger.exception("Skipping invalid record at index %s: %s", index, e)
                continue
        return records

    def delete_by_index(self, index: int) -> bool:
        """Delete record by index. Returns True if deleted, False if index out of range."""
        data = self._load_data()
        if 0 <= index < len(data["records"]):
            data["records"].pop(index)
            self._save_data(data)
            return True
        return False

    def delete_all(self) -> None:
        """Delete all records."""
        data = self._load_data()
        data["records"] = []
        self._save_data(data)

    def save_initial_balance(self, balance: float) -> None:
        """Save initial balance."""
        data = self._load_data()
        data["initial_balance"] = balance
        self._save_data(data)

    def load_initial_balance(self) -> float:
        """Load initial balance. Returns 0.0 if not set."""
        data = self._load_data()
        return data.get("initial_balance", 0.0)

    def save_mandatory_expense(self, expense: MandatoryExpenseRecord) -> None:
        """Save mandatory expense."""
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
                logger.warning(
                    "Skipping non-dict mandatory expense at index %s", index
                )
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
        data = self._load_data()
        if "mandatory_expenses" in data and 0 <= index < len(
            data["mandatory_expenses"]
        ):
            data["mandatory_expenses"].pop(index)
            self._save_data(data)
            return True
        return False

    def delete_all_mandatory_expenses(self) -> None:
        """Delete all mandatory expenses."""
        data = self._load_data()
        data["mandatory_expenses"] = []
        self._save_data(data)
