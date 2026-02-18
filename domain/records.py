from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass
from typing import Literal

from .validation import parse_ymd


@dataclass(frozen=True)
class Record(ABC):
    date: str
    amount_original: float | None = None
    currency: str = "KZT"
    rate_at_operation: float = 1.0
    amount_kzt: float | None = None
    category: str = "General"
    _amount_init: InitVar[float | None] = None

    def __post_init__(self, amount: float | None) -> None:
        normalized_date = (self.date or "").strip()
        if normalized_date:
            parsed = parse_ymd(normalized_date)
            object.__setattr__(self, "date", parsed.isoformat())

        if self.amount_original is None and amount is not None:
            object.__setattr__(self, "amount_original", float(amount))

        if self.amount_kzt is None:
            if amount is not None:
                object.__setattr__(self, "amount_kzt", float(amount))
            elif self.amount_original is not None:
                object.__setattr__(self, "amount_kzt", float(self.amount_original))
            else:
                object.__setattr__(self, "amount_kzt", 0.0)

        if self.amount_original is None and self.amount_kzt is not None:
            object.__setattr__(self, "amount_original", float(self.amount_kzt))

        if not self.currency:
            object.__setattr__(self, "currency", "KZT")

    def signed_amount(self) -> float:
        """Backward-compatible alias."""
        return self.signed_amount_kzt()

    @property
    def amount(self) -> float:
        """Backward-compatible alias."""
        if self.amount_kzt is None:
            return 0.0
        return float(self.amount_kzt)

    @abstractmethod
    def signed_amount_kzt(self) -> float:
        raise NotImplementedError


class IncomeRecord(Record):
    def signed_amount_kzt(self) -> float:
        if self.amount_kzt is None:
            return 0.0
        return self.amount_kzt


class ExpenseRecord(Record):
    def signed_amount_kzt(self) -> float:
        if self.amount_kzt is None:
            return 0.0
        return -abs(self.amount_kzt)


@dataclass(frozen=True)
class MandatoryExpenseRecord(Record):
    description: str = ""
    period: Literal["daily", "weekly", "monthly", "yearly"] = "monthly"

    def signed_amount_kzt(self) -> float:
        if self.amount_kzt is None:
            return 0.0
        return -abs(self.amount_kzt)
