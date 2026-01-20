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


class JsonFileRecordRepository(RecordRepository):
    def __init__(self, file_path: str = "records.json"):
        self._file_path = file_path

    def save(self, record: Record) -> None:
        records = self.load_all()
        records.append(record)
        data = [
            {
                "type": "income" if isinstance(record, IncomeRecord) else "expense",
                "date": record.date,
                "amount": record.amount,
                "category": record.category,
            }
            for record in records
        ]
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_all(self) -> list[Record]:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        records = []
        for item in data:
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
        records = self.load_all()
        if 0 <= index < len(records):
            records.pop(index)
            data = [
                {
                    "type": "income" if isinstance(record, IncomeRecord) else "expense",
                    "date": record.date,
                    "amount": record.amount,
                    "category": record.category,
                }
                for record in records
            ]
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        return False
