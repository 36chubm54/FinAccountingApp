import logging
from datetime import date as dt_date

from domain.import_policy import ImportPolicy
from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord
from domain.reports import Report
from domain.transfers import Transfer
from domain.wallets import Wallet
from infrastructure.repositories import RecordRepository

from .services import CurrencyService

logger = logging.getLogger(__name__)
SYSTEM_WALLET_ID = 1


def _build_rate(amount: float, amount_kzt: float, currency: str) -> float:
    if currency.upper() == "KZT":
        return 1.0
    if amount == 0:
        return 1.0
    return amount_kzt / amount


class CreateIncome:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self, *, date: str, amount: float, currency: str, category: str = "General"
    ) -> None:
        """Create and persist an income record."""
        amount_kzt = self._currency.convert(amount, currency)
        record = IncomeRecord(
            date=date,
            wallet_id=SYSTEM_WALLET_ID,
            amount_original=amount,
            currency=currency.upper(),
            rate_at_operation=_build_rate(amount, amount_kzt, currency),
            amount_kzt=amount_kzt,
            category=category,
        )
        self._repository.save(record)


class CreateExpense:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self, *, date: str, amount: float, currency: str, category: str = "General"
    ) -> None:
        """Create and persist an expense record."""
        amount_kzt = self._currency.convert(amount, currency)
        record = ExpenseRecord(
            date=date,
            wallet_id=SYSTEM_WALLET_ID,
            amount_original=amount,
            currency=currency.upper(),
            rate_at_operation=_build_rate(amount, amount_kzt, currency),
            amount_kzt=amount_kzt,
            category=category,
        )
        self._repository.save(record)


class GenerateReport:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, wallet_id: int | None = None) -> Report:
        wallets = self._repository.load_wallets()
        if not isinstance(wallets, list):
            return Report(
                self._repository.load_all(),
                self._repository.load_initial_balance(),
                wallet_id=wallet_id,
            )
        if wallet_id is None:
            initial_balance = sum(wallet.initial_balance for wallet in wallets)
        else:
            initial_balance = 0.0
            for wallet in wallets:
                if wallet.id == wallet_id:
                    initial_balance = wallet.initial_balance
                    break
        return Report(
            self._repository.load_all(),
            initial_balance,
            wallet_id=wallet_id,
        )


def _wallet_balance_kzt(wallet: Wallet, records: list) -> float:
    total = float(wallet.initial_balance)
    for record in records:
        if record.wallet_id == wallet.id:
            total += record.signed_amount_kzt()
    return total


class CreateWallet:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(
        self,
        *,
        name: str,
        currency: str,
        initial_balance: float,
        allow_negative: bool = False,
    ) -> Wallet:
        return self._repository.create_wallet(
            name=name,
            currency=currency,
            initial_balance=initial_balance,
            allow_negative=allow_negative,
        )


class GetWallets:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> list[Wallet]:
        return self._repository.load_wallets()


class CalculateWalletBalance:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, wallet_id: int) -> float:
        wallets = self._repository.load_wallets()
        wallet = next((w for w in wallets if w.id == wallet_id), None)
        if wallet is None:
            raise ValueError(f"Wallet not found: {wallet_id}")
        return _wallet_balance_kzt(wallet, self._repository.load_all())


class CalculateNetWorth:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute_fixed(self) -> float:
        wallets = self._repository.load_wallets()
        records = self._repository.load_all()
        return sum(_wallet_balance_kzt(wallet, records) for wallet in wallets)

    def execute_current(self) -> float:
        wallets = self._repository.load_wallets()
        records = self._repository.load_all()
        total = 0.0
        for wallet in wallets:
            total += float(self._currency.convert(wallet.initial_balance, wallet.currency))
        for record in records:
            if record.amount_original is not None:
                converted = float(self._currency.convert(record.amount_original, record.currency))
                sign = 1.0 if record.signed_amount_kzt() >= 0 else -1.0
                total += sign * abs(converted)
        return total


class CreateTransfer:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self,
        *,
        from_wallet_id: int,
        to_wallet_id: int,
        transfer_date: str | dt_date,
        amount_original: float,
        currency: str,
        description: str = "",
        commission_amount: float = 0.0,
        commission_currency: str | None = None,
    ) -> int:
        if from_wallet_id == to_wallet_id:
            raise ValueError("Transfer wallets must be different")
        if amount_original <= 0:
            raise ValueError("Transfer amount must be positive")
        if commission_amount < 0:
            raise ValueError("Commission amount cannot be negative")

        wallets = {wallet.id: wallet for wallet in self._repository.load_wallets()}
        from_wallet = wallets.get(from_wallet_id)
        to_wallet = wallets.get(to_wallet_id)
        if from_wallet is None:
            raise ValueError(f"Wallet not found: {from_wallet_id}")
        if to_wallet is None:
            raise ValueError(f"Wallet not found: {to_wallet_id}")

        transfer_kzt = float(self._currency.convert(amount_original, currency))
        transfer_rate = _build_rate(amount_original, transfer_kzt, currency)

        commission_ccy = (commission_currency or currency).upper()
        commission_kzt = 0.0
        commission_rate = 1.0
        if commission_amount > 0:
            commission_kzt = float(self._currency.convert(commission_amount, commission_ccy))
            commission_rate = _build_rate(commission_amount, commission_kzt, commission_ccy)

        records = self._repository.load_all()
        from_balance = _wallet_balance_kzt(from_wallet, records)
        projected_balance = from_balance - transfer_kzt - commission_kzt
        if not from_wallet.allow_negative and projected_balance < 0:
            raise ValueError("Insufficient funds in source wallet")

        transfer_id = max((t.id for t in self._repository.load_transfers()), default=0) + 1
        transfer = Transfer(
            id=transfer_id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            date=transfer_date,
            amount_original=float(amount_original),
            currency=currency.upper(),
            rate_at_operation=transfer_rate,
            amount_kzt=transfer_kzt,
            description=description,
        )
        self._repository.save_transfer(transfer)

        expense_record = ExpenseRecord(
            date=transfer_date,
            wallet_id=from_wallet_id,
            transfer_id=transfer_id,
            amount_original=float(amount_original),
            currency=currency.upper(),
            rate_at_operation=transfer_rate,
            amount_kzt=transfer_kzt,
            category="Transfer",
        )
        income_record = IncomeRecord(
            date=transfer_date,
            wallet_id=to_wallet_id,
            transfer_id=transfer_id,
            amount_original=float(amount_original),
            currency=currency.upper(),
            rate_at_operation=transfer_rate,
            amount_kzt=transfer_kzt,
            category="Transfer",
        )
        self._repository.save(expense_record)
        self._repository.save(income_record)

        if commission_amount > 0:
            commission_record = ExpenseRecord(
                date=transfer_date,
                wallet_id=from_wallet_id,
                transfer_id=transfer_id,
                amount_original=float(commission_amount),
                currency=commission_ccy,
                rate_at_operation=commission_rate,
                amount_kzt=commission_kzt,
                category="Commission",
            )
            self._repository.save(commission_record)

        return transfer_id


class DeleteRecord:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int) -> bool:
        """Delete record by index. Returns True if deleted successfully."""
        return self._repository.delete_by_index(index)


class DeleteAllRecords:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> None:
        """Delete all records."""
        self._repository.delete_all()


class ImportFromCSV:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, filepath: str) -> int:
        """Import records from CSV and atomically replace repository data."""
        from utils.csv_utils import import_records_from_csv

        records, initial_balance, summary = import_records_from_csv(
            filepath, policy=ImportPolicy.FULL_BACKUP
        )
        imported_count, skipped_count, _ = summary
        logger.info("CSV import parsed: imported=%s skipped=%s", imported_count, skipped_count)
        if skipped_count > 0:
            logger.warning("CSV import aborted due to validation errors: skipped=%s", skipped_count)
            raise ValueError("Import aborted: CSV contains invalid rows")
        self._repository.replace_records(records, initial_balance)
        return imported_count


class CreateMandatoryExpense:
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(
        self,
        *,
        amount: float,
        currency: str,
        category: str,
        description: str,
        period: str,
    ) -> None:
        """Create and persist a mandatory expense template."""
        from domain.validation import ensure_valid_period

        ensure_valid_period(period)

        amount_kzt = self._currency.convert(amount, currency)
        expense = MandatoryExpenseRecord(
            date="",  # Will be set when added to report
            wallet_id=SYSTEM_WALLET_ID,
            amount_original=amount,
            currency=currency.upper(),
            rate_at_operation=_build_rate(amount, amount_kzt, currency),
            amount_kzt=amount_kzt,
            category=category,
            description=description,
            period=period,  # type: ignore
        )
        self._repository.save_mandatory_expense(expense)


class GetMandatoryExpenses:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> list[MandatoryExpenseRecord]:
        """Return all mandatory expense templates."""
        return self._repository.load_mandatory_expenses()


class DeleteMandatoryExpense:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int) -> bool:
        """Delete mandatory expense by index. Returns True if deleted."""
        return self._repository.delete_mandatory_expense_by_index(index)


class DeleteAllMandatoryExpenses:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> None:
        """Delete all mandatory expenses."""
        self._repository.delete_all_mandatory_expenses()


class AddMandatoryExpenseToReport:
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int, date: str) -> bool:
        """Add selected mandatory expense to records with provided date."""
        mandatory_expenses = self._repository.load_mandatory_expenses()
        if 0 <= index < len(mandatory_expenses):
            expense = mandatory_expenses[index]
            # Create a new record with the specified date
            record = MandatoryExpenseRecord(
                date=date,
                wallet_id=SYSTEM_WALLET_ID,
                amount_original=expense.amount_original,
                currency=expense.currency,
                rate_at_operation=expense.rate_at_operation,
                amount_kzt=expense.amount_kzt,
                category=expense.category,
                description=expense.description,
                period=expense.period,
            )
            self._repository.save(record)
            return True
        return False
