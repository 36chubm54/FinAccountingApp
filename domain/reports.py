from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from prettytable import PrettyTable

from .records import IncomeRecord, MandatoryExpenseRecord, Record
from .validation import parse_report_period_start


class Report:
    def __init__(
        self,
        records: Iterable[Record],
        initial_balance: float = 0.0,
        balance_label: str = "Initial balance",
        opening_start_date: Optional[str] = None,
    ):
        self._records = list(records)
        self._initial_balance = initial_balance
        self._balance_label = balance_label
        self._opening_start_date = opening_start_date

    def total_fixed(self) -> float:
        """Accounting total by operation-time rates."""
        return self._initial_balance + sum(r.signed_amount_kzt() for r in self._records)

    def total(self) -> float:
        """Backward-compatible alias."""
        return self.total_fixed()

    def total_current(self, currency_service) -> float:
        total = self._initial_balance
        for record in self._records:
            converted = float(
                currency_service.convert(record.amount_original, record.currency)
            )
            sign = 1.0 if record.signed_amount_kzt() >= 0 else -1.0
            total += sign * abs(converted)
        return total

    def fx_difference(self, currency_service) -> float:
        return self.total_current(currency_service) - self.total_fixed()

    def filter_by_period(self, prefix: str) -> "Report":
        start_date = parse_report_period_start(prefix)
        filtered = [r for r in self._records if r.date.startswith(prefix)]
        return Report(
            filtered,
            self.opening_balance(start_date),
            balance_label=f"Opening balance as of {start_date}",
            opening_start_date=start_date,
        )

    def filter_by_category(self, category: str) -> "Report":
        filtered = [r for r in self._records if r.category == category]
        return Report(
            filtered,
            self._initial_balance,
            balance_label=self._balance_label,
            opening_start_date=self._opening_start_date,
        )

    def grouped_by_category(self) -> Dict[str, "Report"]:
        groups: Dict[str, List[Record]] = {}
        for record in self._records:
            if record.category not in groups:
                groups[record.category] = []
            groups[record.category].append(record)
        return {cat: Report(recs, 0.0) for cat, recs in groups.items()}

    def sorted_by_date(self) -> "Report":
        return Report(
            sorted(self._records, key=lambda r: r.date),
            self._initial_balance,
            balance_label=self._balance_label,
            opening_start_date=self._opening_start_date,
        )

    def records(self) -> list[Record]:
        return list(self._records)

    @property
    def initial_balance(self) -> float:
        return self._initial_balance

    @property
    def balance_label(self) -> str:
        return self._balance_label

    @property
    def opening_start_date(self) -> Optional[str]:
        return self._opening_start_date

    @property
    def is_opening_balance(self) -> bool:
        return self._opening_start_date is not None

    def opening_balance(self, start_date: str) -> float:
        return self._initial_balance + sum(
            record.signed_amount()
            for record in self._records
            if record.date < start_date
        )

    @staticmethod
    def _parse_year_month(date_str: str) -> Optional[Tuple[int, int]]:
        try:
            parts = date_str.split("-")
            if len(parts) < 2:
                return None
            year = int(parts[0])
            month = int(parts[1])
            if 1 <= month <= 12:
                return year, month
        except Exception:
            return None
        return None

    def _year_months(self) -> List[Tuple[int, int]]:
        year_months: List[Tuple[int, int]] = []
        for record in self._records:
            parsed = self._parse_year_month(record.date)
            if parsed:
                year_months.append(parsed)
        return year_months

    def monthly_income_expense_rows(
        self, year: Optional[int] = None, up_to_month: Optional[int] = None
    ) -> Tuple[int, List[Tuple[str, float, float]]]:
        year_months = self._year_months()
        today = date.today()

        if year is None:
            if year_months:
                year, _ = max(year_months)
            else:
                year, _ = today.year, today.month

        if up_to_month is None:
            months_in_year = [m for y, m in year_months if y == year]
            if months_in_year:
                up_to_month = max(months_in_year)
            else:
                up_to_month = today.month if year == today.year else 12

        up_to_month = max(1, min(12, up_to_month))

        aggregates: Dict[Tuple[int, int], Tuple[float, float]] = {}
        for record in self._records:
            parsed = self._parse_year_month(record.date)
            if not parsed:
                continue
            rec_year, rec_month = parsed
            if rec_year != year or not (1 <= rec_month <= up_to_month):
                continue
            income_total, expense_total = aggregates.get(
                (rec_year, rec_month), (0.0, 0.0)
            )
            if isinstance(record, IncomeRecord):
                income_total += record.amount
            else:
                expense_total += abs(record.amount)
            aggregates[(rec_year, rec_month)] = (income_total, expense_total)

        rows: List[Tuple[str, float, float]] = []
        for month in range(1, up_to_month + 1):
            income_total, expense_total = aggregates.get((year, month), (0.0, 0.0))
            rows.append((f"{year}-{month:02d}", income_total, expense_total))

        return year, rows

    def monthly_income_expense_table(
        self, year: Optional[int] = None, up_to_month: Optional[int] = None
    ) -> str:
        year, rows = self.monthly_income_expense_rows(year, up_to_month)
        table = PrettyTable()
        table.field_names = ["Month", "Income (KZT)", "Expense (KZT)"]

        total_income = 0.0
        total_expense = 0.0
        for month_label, income, expense in rows:
            total_income += income
            total_expense += expense
            table.add_row([month_label, f"{income:.2f}", f"{expense:.2f}"])

        table.add_row(
            ["TOTAL", f"{total_income:.2f}", f"{total_expense:.2f}"], divider=True
        )
        return str(table)

    def as_table(self, summary_mode: str = "full") -> str:
        table = PrettyTable()
        table.field_names = ["Date", "Type", "Category", "Amount (KZT)"]

        if self._initial_balance != 0:
            balance_str = (
                f"{self._initial_balance:.2f}"
                if self._initial_balance >= 0
                else f"({abs(self._initial_balance):.2f})"
            )
            table.add_row(["", self._balance_label, "", balance_str])

        sorted_records = sorted(self._records, key=lambda r: r.date)

        for record in sorted_records:
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            amount_value = record.amount
            amount_str = (
                f"{amount_value:.2f}"
                if amount_value >= 0
                else f"({abs(amount_value):.2f})"
            )
            table.add_row([record.date, record_type, record.category, amount_str])

        records_total = sum(r.signed_amount_kzt() for r in self._records)
        records_total_str = (
            f"{records_total:.2f}"
            if records_total >= 0
            else f"({abs(records_total):.2f})"
        )
        final_balance = self.total_fixed()
        final_balance_str = (
            f"{final_balance:.2f}"
            if final_balance >= 0
            else f"({abs(final_balance):.2f})"
        )

        if summary_mode == "total_only":
            table.add_row(["SUBTOTAL", "", "", final_balance_str], divider=True)
        else:
            table.add_row(["SUBTOTAL", "", "", records_total_str], divider=True)
            table.add_row(["FINAL BALANCE", "", "", final_balance_str], divider=True)

        return str(table)

    def to_csv(self, filepath: str) -> None:
        from utils.csv_utils import report_to_csv

        report_to_csv(self, filepath)

    @staticmethod
    def from_csv(filepath: str) -> "Report":
        from utils.csv_utils import report_from_csv

        return report_from_csv(filepath)
