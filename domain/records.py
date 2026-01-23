from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


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


@dataclass(frozen=True)
class MandatoryExpenseRecord(Record):
    description: str
    period: Literal["daily", "weekly", "monthly", "yearly"]

    def signed_amount(self) -> float:
        return -abs(self.amount)
