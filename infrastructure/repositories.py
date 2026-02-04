import json
import os
import tempfile
from abc import ABC, abstractmethod
from domain.records import Record, IncomeRecord, ExpenseRecord, MandatoryExpenseRecord


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
                pass

    def save(self, record: Record) -> None:
        data = self._load_data()
        if isinstance(record, MandatoryExpenseRecord):
            record_data = {
                "type": "mandatory_expense",
                "date": record.date,
                "amount": record.amount,
                "category": record.category,
                "description": record.description,
                "period": record.period,
            }
        else:
            record_data = {
                "type": "income" if isinstance(record, IncomeRecord) else "expense",
                "date": record.date,
                "amount": record.amount,
                "category": record.category,
            }
        data["records"].append(record_data)
        self._save_data(data)

    def load_all(self) -> list[Record]:
        data = self._load_data()
        records = []
        for item in data["records"]:
            category = item.get("category", "General")
            if item["type"] == "income":
                record = IncomeRecord(
                    date=item["date"], amount=item["amount"], category=category
                )
            elif item["type"] == "expense":
                record = ExpenseRecord(
                    date=item["date"], amount=item["amount"], category=category
                )
            elif item["type"] == "mandatory_expense":
                record = MandatoryExpenseRecord(
                    date=item["date"],
                    amount=item["amount"],
                    category=category,
                    description=item["description"],
                    period=item["period"],
                )
            else:
                continue
            records.append(record)
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
        expense_data = {
            "date": expense.date,
            "amount": expense.amount,
            "category": expense.category,
            "description": expense.description,
            "period": expense.period,
        }
        data["mandatory_expenses"].append(expense_data)
        self._save_data(data)

    def load_mandatory_expenses(self) -> list[MandatoryExpenseRecord]:
        """Load all mandatory expenses."""
        data = self._load_data()
        expenses = []
        for item in data.get("mandatory_expenses", []):
            expense = MandatoryExpenseRecord(
                date=item["date"],
                amount=item["amount"],
                category=item["category"],
                description=item["description"],
                period=item["period"],
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
