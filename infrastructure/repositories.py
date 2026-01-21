import json
from abc import ABC, abstractmethod
from domain.records import Record, IncomeRecord, ExpenseRecord


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


class JsonFileRecordRepository(RecordRepository):
    def __init__(self, file_path: str = "records.json"):
        self._file_path = file_path

    def _load_data(self) -> dict:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"initial_balance": 0.0, "records": []}
        if isinstance(data, list):
            # Migrate old format
            return {"initial_balance": 0.0, "records": data}
        return data

    def _save_data(self, data: dict) -> None:
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save(self, record: Record) -> None:
        data = self._load_data()
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
