from __future__ import annotations

from dataclasses import replace as dc_replace
from datetime import date as dt_date

from domain.records import IncomeRecord, MandatoryExpenseRecord, Record
from domain.transfers import Transfer
from domain.wallets import Wallet
from infrastructure.repositories import RecordRepository
from storage.sqlite_storage import SQLiteStorage

SYSTEM_WALLET_ID = 1


class SQLiteRecordRepository(RecordRepository):
    """RecordRepository implementation backed by SQLite."""

    def __init__(self, db_path: str = "finance.db", schema_path: str | None = None) -> None:
        self._storage = SQLiteStorage(db_path)
        self._storage.initialize_schema(schema_path)
        self._conn = self._storage._conn

    def close(self) -> None:
        self._storage.close()

    @staticmethod
    def _date_as_text(value: dt_date | str) -> str:
        if isinstance(value, dt_date):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _record_type(record: Record) -> str:
        if isinstance(record, MandatoryExpenseRecord):
            return "mandatory_expense"
        if isinstance(record, IncomeRecord):
            return "income"
        return "expense"

    def _next_id(self, table: str) -> int:
        return int(
            self._conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0]
        )

    def _validate_transfer_integrity(
        self, records: list[Record], transfers: list[Transfer]
    ) -> None:
        transfer_ids = {transfer.id for transfer in transfers}
        grouped: dict[int, list[Record]] = {}
        for record in records:
            if record.transfer_id is None:
                continue
            if record.transfer_id not in transfer_ids:
                raise ValueError(f"Dangling transfer link in record #{record.id}")
            grouped.setdefault(record.transfer_id, []).append(record)
        for transfer in transfers:
            linked = grouped.get(transfer.id, [])
            if len(linked) != 2:
                raise ValueError(
                    f"Transfer integrity violated for #{transfer.id}: {len(linked)} records"
                )
            if {record.type for record in linked} != {"income", "expense"}:
                raise ValueError(
                    f"Transfer integrity violated for #{transfer.id}: invalid record types"
                )

    def _insert_record_row(self, record: Record) -> None:
        period = record.period if isinstance(record, MandatoryExpenseRecord) else None
        self._conn.execute(
            """
            INSERT INTO records (
                id, type, date, wallet_id, transfer_id, amount_original, currency,
                rate_at_operation, amount_kzt, category, description, period
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(record.id),
                self._record_type(record),
                self._date_as_text(record.date),
                int(record.wallet_id),
                int(record.transfer_id) if record.transfer_id is not None else None,
                float(record.amount_original or 0.0),
                str(record.currency).upper(),
                float(record.rate_at_operation),
                float(record.amount_kzt or 0.0),
                str(record.category),
                str(record.description or ""),
                str(period) if period is not None else None,
            ),
        )

    def _insert_transfer_row(self, transfer: Transfer) -> None:
        self._conn.execute(
            """
            INSERT INTO transfers (
                id, from_wallet_id, to_wallet_id, date, amount_original, currency,
                rate_at_operation, amount_kzt, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(transfer.id),
                int(transfer.from_wallet_id),
                int(transfer.to_wallet_id),
                self._date_as_text(transfer.date),
                float(transfer.amount_original),
                str(transfer.currency).upper(),
                float(transfer.rate_at_operation),
                float(transfer.amount_kzt),
                str(transfer.description or ""),
            ),
        )

    def _insert_mandatory_row(self, expense: MandatoryExpenseRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO mandatory_expenses (
                id, date, wallet_id, amount_original, currency, rate_at_operation,
                amount_kzt, category, description, period
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(expense.id),
                self._date_as_text(expense.date),
                int(expense.wallet_id),
                float(expense.amount_original or 0.0),
                str(expense.currency).upper(),
                float(expense.rate_at_operation),
                float(expense.amount_kzt or 0.0),
                str(expense.category),
                str(expense.description or ""),
                str(expense.period),
            ),
        )

    def load_active_wallets(self) -> list[Wallet]:
        return [wallet for wallet in self.load_wallets() if wallet.is_active]

    def create_wallet(
        self,
        *,
        name: str,
        currency: str,
        initial_balance: float,
        allow_negative: bool = False,
        system: bool = False,
    ) -> Wallet:
        with self._conn:
            wallet_id = self._next_id("wallets")
            wallet = Wallet(
                id=wallet_id,
                name=str(name or f"Wallet {wallet_id}"),
                currency=str(currency or "KZT").upper(),
                initial_balance=float(initial_balance),
                system=bool(system),
                allow_negative=bool(allow_negative),
                is_active=True,
            )
            self.save_wallet(wallet)
            return wallet

    def save_wallet(self, wallet: Wallet) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO wallets (
                    id, name, currency, initial_balance, system, allow_negative, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    currency = excluded.currency,
                    initial_balance = excluded.initial_balance,
                    system = excluded.system,
                    allow_negative = excluded.allow_negative,
                    is_active = excluded.is_active
                """,
                (
                    int(wallet.id),
                    str(wallet.name),
                    str(wallet.currency).upper(),
                    float(wallet.initial_balance),
                    int(bool(wallet.system)),
                    int(bool(wallet.allow_negative)),
                    int(bool(wallet.is_active)),
                ),
            )

    def soft_delete_wallet(self, wallet_id: int) -> bool:
        wallet_id = int(wallet_id)
        with self._conn:
            row = self._conn.execute(
                "SELECT system FROM wallets WHERE id = ?",
                (wallet_id,),
            ).fetchone()
            if row is None:
                return False
            if bool(row[0]):
                return False
            self._conn.execute("UPDATE wallets SET is_active = 0 WHERE id = ?", (wallet_id,))
            return True

    def load_wallets(self) -> list[Wallet]:
        return self._storage.get_wallets()

    def get_system_wallet(self) -> Wallet:
        for wallet in self.load_wallets():
            if wallet.system or wallet.id == SYSTEM_WALLET_ID:
                return wallet
        return Wallet(
            id=SYSTEM_WALLET_ID,
            name="Main wallet",
            currency="KZT",
            initial_balance=0.0,
            system=True,
            allow_negative=False,
            is_active=True,
        )

    def save_transfer(self, transfer: Transfer) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO transfers (
                    id, from_wallet_id, to_wallet_id, date, amount_original, currency,
                    rate_at_operation, amount_kzt, description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    from_wallet_id = excluded.from_wallet_id,
                    to_wallet_id = excluded.to_wallet_id,
                    date = excluded.date,
                    amount_original = excluded.amount_original,
                    currency = excluded.currency,
                    rate_at_operation = excluded.rate_at_operation,
                    amount_kzt = excluded.amount_kzt,
                    description = excluded.description
                """,
                (
                    int(transfer.id),
                    int(transfer.from_wallet_id),
                    int(transfer.to_wallet_id),
                    self._date_as_text(transfer.date),
                    float(transfer.amount_original),
                    str(transfer.currency).upper(),
                    float(transfer.rate_at_operation),
                    float(transfer.amount_kzt),
                    str(transfer.description or ""),
                ),
            )

    def load_transfers(self) -> list[Transfer]:
        return self._storage.get_transfers()

    def replace_records_and_transfers(
        self, records: list[Record], transfers: list[Transfer]
    ) -> None:
        self._validate_transfer_integrity(records, transfers)
        with self._conn:
            self._conn.execute("DELETE FROM records")
            self._conn.execute("DELETE FROM transfers")
            for transfer in sorted(transfers, key=lambda item: item.id):
                self._insert_transfer_row(transfer)
            for record in sorted(records, key=lambda item: item.id):
                self._insert_record_row(record)

    def save(self, record: Record) -> None:
        record_id = int(getattr(record, "id", 0) or 0)
        if record_id <= 0:
            record_id = self._next_id("records")
            record = dc_replace(record, id=record_id)
        if self._conn.execute("SELECT 1 FROM records WHERE id = ?", (record_id,)).fetchone():
            record_id = self._next_id("records")
            record = dc_replace(record, id=record_id)
        with self._conn:
            self._insert_record_row(record)

    def load_all(self) -> list[Record]:
        return self._storage.get_records()

    def list_all(self) -> list[Record]:
        return self.load_all()

    def get_by_id(self, record_id: int) -> Record:
        record_id = int(record_id)
        for record in self.load_all():
            if int(getattr(record, "id", 0)) == record_id:
                return record
        raise ValueError(f"Record not found: {record_id}")

    def replace(self, record: Record) -> None:
        record_id = int(getattr(record, "id", 0) or 0)
        if record_id <= 0:
            raise ValueError("Record id must be positive")
        if not self._conn.execute("SELECT 1 FROM records WHERE id = ?", (record_id,)).fetchone():
            raise ValueError(f"Record not found: {record_id}")
        with self._conn:
            self._conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
            self._insert_record_row(record)

    def delete_by_index(self, index: int) -> bool:
        records = self.load_all()
        if not (0 <= int(index) < len(records)):
            return False
        target = records[int(index)]
        with self._conn:
            self._conn.execute("DELETE FROM records WHERE id = ?", (int(target.id),))
        return True

    def delete_all(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM records")

    def save_initial_balance(self, balance: float) -> None:
        with self._conn:
            row = self._conn.execute(
                "SELECT id FROM wallets WHERE id = ?", (SYSTEM_WALLET_ID,)
            ).fetchone()
            if row is None:
                self._conn.execute(
                    """
                    INSERT INTO wallets (
                        id, name, currency, initial_balance, system, allow_negative, is_active
                    ) VALUES (?, ?, ?, ?, 1, 0, 1)
                    """,
                    (SYSTEM_WALLET_ID, "Main wallet", "KZT", float(balance)),
                )
            else:
                self._conn.execute(
                    "UPDATE wallets SET initial_balance = ?, system = 1 WHERE id = ?",
                    (float(balance), SYSTEM_WALLET_ID),
                )

    def load_initial_balance(self) -> float:
        return float(self.get_system_wallet().initial_balance)

    def save_mandatory_expense(self, expense: MandatoryExpenseRecord) -> None:
        next_id = self._next_id("mandatory_expenses")
        normalized = dc_replace(expense, id=next_id)
        with self._conn:
            self._insert_mandatory_row(normalized)

    def load_mandatory_expenses(self) -> list[MandatoryExpenseRecord]:
        return self._storage.get_mandatory_expenses()

    def delete_mandatory_expense_by_index(self, index: int) -> bool:
        expenses = self.load_mandatory_expenses()
        if not (0 <= int(index) < len(expenses)):
            return False
        target = expenses[int(index)]
        with self._conn:
            self._conn.execute("DELETE FROM mandatory_expenses WHERE id = ?", (int(target.id),))
        return True

    def delete_all_mandatory_expenses(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM mandatory_expenses")

    def replace_records(self, records: list[Record], initial_balance: float) -> None:
        with self._conn:
            self.save_initial_balance(float(initial_balance))
            self._conn.execute("DELETE FROM records")
            for record in sorted(records, key=lambda item: item.id):
                self._insert_record_row(record)

    def replace_mandatory_expenses(self, expenses: list[MandatoryExpenseRecord]) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM mandatory_expenses")
            for index, expense in enumerate(expenses, start=1):
                self._insert_mandatory_row(dc_replace(expense, id=index))

    def replace_all_data(
        self,
        *,
        initial_balance: float = 0.0,
        wallets: list[Wallet] | None = None,
        records: list[Record],
        mandatory_expenses: list[MandatoryExpenseRecord],
        transfers: list[Transfer] | None = None,
    ) -> None:
        normalized_wallets = list(wallets or [])
        if not normalized_wallets:
            normalized_wallets = [
                Wallet(
                    id=SYSTEM_WALLET_ID,
                    name="Main wallet",
                    currency="KZT",
                    initial_balance=float(initial_balance),
                    system=True,
                    allow_negative=False,
                    is_active=True,
                )
            ]
        normalized_transfers = list(transfers or [])
        self._validate_transfer_integrity(records, normalized_transfers)
        with self._conn:
            self._conn.execute("DELETE FROM records")
            self._conn.execute("DELETE FROM mandatory_expenses")
            self._conn.execute("DELETE FROM transfers")
            self._conn.execute("DELETE FROM wallets")
            for wallet in sorted(normalized_wallets, key=lambda item: item.id):
                self._conn.execute(
                    """
                    INSERT INTO wallets (
                        id, name, currency, initial_balance, system, allow_negative, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(wallet.id),
                        str(wallet.name),
                        str(wallet.currency).upper(),
                        float(wallet.initial_balance),
                        int(bool(wallet.system)),
                        int(bool(wallet.allow_negative)),
                        int(bool(wallet.is_active)),
                    ),
                )
            for transfer in sorted(normalized_transfers, key=lambda item: item.id):
                self._insert_transfer_row(transfer)
            for record in sorted(records, key=lambda item: item.id):
                self._insert_record_row(record)
            for expense in sorted(mandatory_expenses, key=lambda item: item.id):
                self._insert_mandatory_row(expense)
