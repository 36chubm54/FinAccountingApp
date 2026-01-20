from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Record(ABC):
    date: str
    amount: float
    category: str

    @abstractmethod
    def signed_amount(self) -> float:
        pass


class IncomeRecord(Record):
    def signed_amount(self) -> float:
        return self.amount


class ExpenseRecord(Record):
    def signed_amount(self) -> float:
        return -abs(self.amount)
