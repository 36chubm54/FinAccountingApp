import json
import logging
import os
from collections.abc import Sequence
from datetime import date as dt_date

from domain.import_policy import ImportPolicy
from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord, Record
from domain.transfers import Transfer
from domain.wallets import Wallet
from utils.import_core import ImportSummary, parse_import_row, record_type_name

logger = logging.getLogger(__name__)
SYSTEM_WALLET_ID = 1


def _record_to_payload(record: Record) -> dict:
    item = {
        "date": record.date.isoformat() if isinstance(record.date, dt_date) else record.date,
        "type": record_type_name(record),
        "wallet_id": int(getattr(record, "wallet_id", SYSTEM_WALLET_ID)),
        "transfer_id": getattr(record, "transfer_id", None),
        "category": record.category,
        "amount_original": record.amount_original,
        "currency": record.currency,
        "rate_at_operation": record.rate_at_operation,
        "amount_kzt": record.amount_kzt,
        "description": str(getattr(record, "description", "") or ""),
        "period": "",
    }
    if isinstance(record, MandatoryExpenseRecord):
        item["period"] = record.period
    return item


def _wallet_to_payload(wallet: Wallet) -> dict:
    return {
        "id": int(wallet.id),
        "name": str(wallet.name),
        "currency": str(wallet.currency or "KZT").upper(),
        "initial_balance": float(wallet.initial_balance),
        "system": bool(wallet.system),
        "allow_negative": bool(wallet.allow_negative),
        "is_active": bool(wallet.is_active),
    }


def _transfer_to_payload(transfer: Transfer) -> dict:
    return {
        "id": int(transfer.id),
        "from_wallet_id": int(transfer.from_wallet_id),
        "to_wallet_id": int(transfer.to_wallet_id),
        "date": transfer.date.isoformat() if isinstance(transfer.date, dt_date) else transfer.date,
        "amount_original": float(transfer.amount_original),
        "currency": str(transfer.currency).upper(),
        "rate_at_operation": float(transfer.rate_at_operation),
        "amount_kzt": float(transfer.amount_kzt),
        "description": str(transfer.description or ""),
    }


def _validate_transfer_integrity(records: list[Record], transfers: list[Transfer]) -> list[str]:
    errors: list[str] = []
    by_transfer: dict[int, list[Record]] = {}
    for record in records:
        if record.transfer_id is None:
            continue
        by_transfer.setdefault(record.transfer_id, []).append(record)

    transfer_ids = {transfer.id for transfer in transfers}

    for transfer_id in sorted(by_transfer):
        if transfer_id not in transfer_ids:
            errors.append(f"Dangling transfer-linked records for missing transfer #{transfer_id}")

    for transfer in transfers:
        linked = by_transfer.get(transfer.id, [])
        if len(linked) != 2:
            errors.append(
                f"Transfer integrity violated for #{transfer.id}: "
                f"expected 2 linked records, got {len(linked)}"
            )
            continue
        types = {record.type for record in linked}
        if types != {"expense", "income"}:
            errors.append(
                f"Transfer integrity violated for #{transfer.id}: "
                "requires one expense and one income"
            )
            continue
        expense_record = next(
            (record for record in linked if isinstance(record, ExpenseRecord)), None
        )
        income_record = next(
            (record for record in linked if isinstance(record, IncomeRecord)), None
        )
        if expense_record is None or income_record is None:
            errors.append(
                f"Transfer integrity violated for #{transfer.id}: "
                "cannot resolve income/expense pair"
            )
            continue
        if expense_record.wallet_id != transfer.from_wallet_id:
            errors.append(f"Transfer #{transfer.id}: from_wallet_id mismatch")
        if income_record.wallet_id != transfer.to_wallet_id:
            errors.append(f"Transfer #{transfer.id}: to_wallet_id mismatch")

    return errors


def _derive_transfers_from_linked_records(
    records: list[Record],
) -> tuple[list[Transfer], list[str]]:
    transfers: list[Transfer] = []
    errors: list[str] = []
    grouped: dict[int, list[Record]] = {}
    for record in records:
        if record.transfer_id is not None:
            grouped.setdefault(record.transfer_id, []).append(record)

    for transfer_id in sorted(grouped):
        linked = grouped[transfer_id]
        if len(linked) != 2:
            errors.append(
                f"Transfer integrity violated for #{transfer_id}: "
                f"expected 2 linked records, got {len(linked)}"
            )
            continue
        expense_record = next(
            (record for record in linked if isinstance(record, ExpenseRecord)), None
        )
        income_record = next(
            (record for record in linked if isinstance(record, IncomeRecord)), None
        )
        if expense_record is None or income_record is None:
            errors.append(
                f"Transfer integrity violated for #{transfer_id}: "
                "requires one expense and one income"
            )
            continue
        try:
            transfers.append(
                Transfer(
                    id=transfer_id,
                    from_wallet_id=expense_record.wallet_id,
                    to_wallet_id=income_record.wallet_id,
                    date=expense_record.date,
                    amount_original=float(expense_record.amount_original or 0.0),
                    currency=str(expense_record.currency or "KZT").upper(),
                    rate_at_operation=float(expense_record.rate_at_operation),
                    amount_kzt=float(expense_record.amount_kzt or 0.0),
                    description=str(expense_record.description or ""),
                )
            )
        except Exception as exc:
            errors.append(f"Transfer #{transfer_id}: invalid linked records ({exc})")

    return transfers, errors


def export_full_backup_to_json(
    filepath: str,
    *,
    wallets: Sequence[Wallet] | None = None,
    records: Sequence[Record],
    mandatory_expenses: Sequence[MandatoryExpenseRecord],
    transfers: Sequence[Transfer] = (),
    initial_balance: float = 0.0,
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
    payload = {
        "wallets": [_wallet_to_payload(wallet) for wallet in normalized_wallets],
        "records": [_record_to_payload(record) for record in records],
        "mandatory_expenses": [_record_to_payload(expense) for expense in mandatory_expenses],
        "transfers": [_transfer_to_payload(transfer) for transfer in transfers],
    }

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def import_full_backup_from_json(
    filepath: str,
) -> tuple[list[Wallet], list[Record], list[MandatoryExpenseRecord], list[Transfer], ImportSummary]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    with open(filepath, encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, dict):
        raise ValueError("Invalid backup JSON structure: root must be object")

    migrated_legacy = not all(key in data for key in ("wallets", "records", "transfers"))

    raw_records = data.get("records", [])
    raw_mandatory = data.get("mandatory_expenses", [])
    raw_wallets = data.get("wallets", [])
    raw_transfers = data.get("transfers", [])

    if not isinstance(raw_records, list) or not isinstance(raw_mandatory, list):
        raise ValueError(
            "Invalid backup JSON structure: records and mandatory_expenses must be arrays"
        )

    if migrated_legacy:
        if not isinstance(raw_wallets, list):
            raw_wallets = []
        if not isinstance(raw_transfers, list):
            raw_transfers = []

    if not isinstance(raw_wallets, list) or not isinstance(raw_transfers, list):
        raise ValueError("Invalid backup JSON structure: wallets and transfers must be arrays")

    errors: list[str] = []
    skipped = 0
    imported = 0

    wallets: list[Wallet] = []
    if raw_wallets:
        for idx, item in enumerate(raw_wallets, start=1):
            if not isinstance(item, dict):
                skipped += 1
                errors.append(f"wallets[{idx}]: invalid item type")
                continue
            try:
                wallet = Wallet(
                    id=int(item.get("id", 0)),
                    name=str(item.get("name", "") or f"Wallet {idx}"),
                    currency=str(item.get("currency", "KZT") or "KZT").upper(),
                    initial_balance=float(item.get("initial_balance", 0.0) or 0.0),
                    system=bool(item.get("system", int(item.get("id", 0)) == SYSTEM_WALLET_ID)),
                    allow_negative=bool(item.get("allow_negative", False)),
                    is_active=bool(item.get("is_active", True)),
                )
                wallets.append(wallet)
                imported += 1
            except Exception as exc:
                skipped += 1
                errors.append(f"wallets[{idx}]: invalid wallet ({exc})")
    else:
        # Legacy migration: move global initial_balance into system wallet.
        legacy_balance = float(data.get("initial_balance", 0.0) or 0.0)
        wallets = [
            Wallet(
                id=SYSTEM_WALLET_ID,
                name="Main wallet",
                currency="KZT",
                initial_balance=legacy_balance,
                system=True,
                allow_negative=False,
                is_active=True,
            )
        ]

    wallet_ids = {wallet.id for wallet in wallets}
    if SYSTEM_WALLET_ID not in wallet_ids:
        wallets.insert(
            0,
            Wallet(
                id=SYSTEM_WALLET_ID,
                name="Main wallet",
                currency="KZT",
                initial_balance=0.0,
                system=True,
                allow_negative=False,
                is_active=True,
            ),
        )
        wallet_ids = {wallet.id for wallet in wallets}

    records: list[Record] = []
    for idx, item in enumerate(raw_records, start=1):
        if not isinstance(item, dict):
            skipped += 1
            errors.append(f"records[{idx}]: invalid item type")
            continue
        record_payload = dict(item)
        if "wallet_id" not in record_payload:
            record_payload["wallet_id"] = SYSTEM_WALLET_ID
        record, _, error = parse_import_row(
            record_payload,
            row_label=f"records[{idx}]",
            policy=ImportPolicy.FULL_BACKUP,
        )
        if error:
            skipped += 1
            errors.append(error)
            continue
        if record is None:
            continue
        if record.wallet_id not in wallet_ids:
            skipped += 1
            errors.append(f"records[{idx}]: wallet not found ({record.wallet_id})")
            continue
        imported += 1
        records.append(record)

    mandatory_expenses: list[MandatoryExpenseRecord] = []
    for idx, item in enumerate(raw_mandatory, start=1):
        if not isinstance(item, dict):
            skipped += 1
            errors.append(f"mandatory_expenses[{idx}]: invalid item type")
            continue
        payload = dict(item)
        payload["type"] = "mandatory_expense"
        if "wallet_id" not in payload:
            payload["wallet_id"] = SYSTEM_WALLET_ID
        record, _, error = parse_import_row(
            payload,
            row_label=f"mandatory_expenses[{idx}]",
            policy=ImportPolicy.FULL_BACKUP,
            mandatory_only=True,
        )
        if error:
            skipped += 1
            errors.append(error)
            continue
        if isinstance(record, MandatoryExpenseRecord):
            if record.wallet_id not in wallet_ids:
                skipped += 1
                errors.append(f"mandatory_expenses[{idx}]: wallet not found ({record.wallet_id})")
                continue
            imported += 1
            mandatory_expenses.append(record)

    transfers: list[Transfer] = []
    if raw_transfers:
        for idx, item in enumerate(raw_transfers, start=1):
            if not isinstance(item, dict):
                skipped += 1
                errors.append(f"transfers[{idx}]: invalid item type")
                continue
            try:
                transfer = Transfer(
                    id=int(item.get("id", 0)),
                    from_wallet_id=int(item.get("from_wallet_id", 0)),
                    to_wallet_id=int(item.get("to_wallet_id", 0)),
                    date=str(item.get("date", "") or ""),
                    amount_original=float(item.get("amount_original", 0.0) or 0.0),
                    currency=str(item.get("currency", "KZT") or "KZT").upper(),
                    rate_at_operation=float(item.get("rate_at_operation", 1.0) or 1.0),
                    amount_kzt=float(item.get("amount_kzt", 0.0) or 0.0),
                    description=str(item.get("description", "") or ""),
                )
            except Exception as exc:
                skipped += 1
                errors.append(f"transfers[{idx}]: invalid transfer ({exc})")
                continue
            if transfer.from_wallet_id not in wallet_ids or transfer.to_wallet_id not in wallet_ids:
                skipped += 1
                errors.append(f"transfers[{idx}]: wallet not found")
                continue
            transfers.append(transfer)
            imported += 1
    else:
        derived, derive_errors = _derive_transfers_from_linked_records(records)
        transfers.extend(derived)
        skipped += len(derive_errors)
        errors.extend(derive_errors)

    integrity_errors = _validate_transfer_integrity(records, transfers)
    if integrity_errors:
        skipped += len(integrity_errors)
        errors.extend(integrity_errors)

    logger.info(
        "JSON backup import completed: imported=%s skipped=%s file=%s legacy=%s",
        imported,
        skipped,
        filepath,
        migrated_legacy,
    )
    return wallets, records, mandatory_expenses, transfers, (imported, skipped, errors)
