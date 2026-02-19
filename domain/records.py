from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass
from datetime import date as dt_date
from typing import Literal

from .validation import parse_ymd


@dataclass(frozen=True)
class Record(ABC):
    date: dt_date | str
    wallet_id: int = 1
    transfer_id: int | None = None
    amount_original: float | None = None
    currency: str = "KZT"
    rate_at_operation: float = 1.0
    amount_kzt: float | None = None
    category: str = "General"
    _amount_init: InitVar[float | None] = None

    def __post_init__(self, amount: float | None) -> None:
        date_value: dt_date | None = None
        if isinstance(self.date, dt_date):
            date_value = self.date
        else:
            normalized_date = (self.date or "").strip()
            if normalized_date:
                date_value = parse_ymd(normalized_date)
        if date_value is not None:
            object.__setattr__(self, "date", date_value)

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

        try:
            wallet_id = int(self.wallet_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("wallet_id must be an integer") from exc
        if wallet_id <= 0:
            raise ValueError("wallet_id must be a positive integer")
        object.__setattr__(self, "wallet_id", wallet_id)

        if self.transfer_id is not None:
            try:
                transfer_id = int(self.transfer_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("transfer_id must be an integer") from exc
            if transfer_id <= 0:
                raise ValueError("transfer_id must be a positive integer")
            object.__setattr__(self, "transfer_id", transfer_id)

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

    @property
    @abstractmethod
    def type(self) -> str:
        raise NotImplementedError


class IncomeRecord(Record):
    @property
    def type(self) -> str:
        return "income"

    def signed_amount_kzt(self) -> float:
        if self.amount_kzt is None:
            return 0.0
        return self.amount_kzt


class ExpenseRecord(Record):
    @property
    def type(self) -> str:
        return "expense"

    def signed_amount_kzt(self) -> float:
        if self.amount_kzt is None:
            return 0.0
        return -abs(self.amount_kzt)


@dataclass(frozen=True)
class MandatoryExpenseRecord(Record):
    description: str = ""
    period: Literal["daily", "weekly", "monthly", "yearly"] = "monthly"

    @property
    def type(self) -> str:
        return "expense"

    def signed_amount_kzt(self) -> float:
        if self.amount_kzt is None:
            return 0.0
        return -abs(self.amount_kzt)
