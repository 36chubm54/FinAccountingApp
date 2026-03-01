from __future__ import annotations

import math
from argparse import Namespace
from pathlib import Path

from backup import create_backup, export_to_json
from config import JSON_PATH, SQLITE_PATH, USE_SQLITE
from infrastructure.repositories import JsonFileRecordRepository, RecordRepository
from infrastructure.sqlite_repository import SQLiteRecordRepository
from migrate_json_to_sqlite import run_migration
from storage.json_storage import JsonStorage
from storage.sqlite_storage import SQLiteStorage

EPSILON = 0.00001


#
def _resolve_schema_path(schema_path: str) -> str:
    candidate = Path(schema_path)
    if candidate.is_absolute():
        return str(candidate)
    return str((Path(__file__).resolve().parent / "db" / candidate.name).resolve())


def _sqlite_has_data(sqlite_path: str, schema_path: str | None = None) -> bool:
    #
    if schema_path is not None:
        schema_path = _resolve_schema_path(schema_path)
    storage = SQLiteStorage(sqlite_path)
    try:
        storage.initialize_schema(schema_path)
        conn = storage._conn
        for table in ("wallets", "records", "transfers", "mandatory_expenses"):
            if int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) > 0:
                return True
        return False
    finally:
        storage.close()


def _wallet_balances_from_json(repository: RecordRepository) -> dict[int, float]:
    wallets = repository.load_wallets()
    records = repository.load_all()
    balances = {wallet.id: float(wallet.initial_balance) for wallet in wallets}
    for record in records:
        balances[int(record.wallet_id)] = balances.get(int(record.wallet_id), 0.0) + float(
            record.signed_amount_kzt()
        )
    return balances


def _wallet_balances_from_sqlite(sqlite_repo: SQLiteRecordRepository) -> dict[int, float]:
    conn = sqlite_repo._conn
    rows = conn.execute(
        """
        SELECT
            w.id AS wallet_id,
            w.initial_balance + COALESCE(
                SUM(CASE WHEN r.type = 'income' THEN r.amount_kzt ELSE -ABS(r.amount_kzt) END),
                0
            ) AS balance
        FROM wallets AS w
        LEFT JOIN records AS r ON r.wallet_id = w.id
        GROUP BY w.id, w.initial_balance
        ORDER BY w.id
        """
    ).fetchall()
    return {int(row[0]): float(row[1]) for row in rows}


def _validate_startup_integrity(
    json_path: str,
    sqlite_repo: SQLiteRecordRepository,
) -> None:
    json_storage = JsonStorage(json_path)
    json_wallets = json_storage.get_wallets()
    json_records = json_storage.get_records()
    json_transfers = json_storage.get_transfers()

    sqlite_wallets = sqlite_repo.load_wallets()
    sqlite_records = sqlite_repo.load_all()
    sqlite_transfers = sqlite_repo.load_transfers()

    if len(json_wallets) != len(sqlite_wallets):
        raise RuntimeError(
            f"Аварийный режим: wallets mismatch JSON={len(json_wallets)} "
            f"SQLite={len(sqlite_wallets)}"
        )
    if len(json_records) != len(sqlite_records):
        raise RuntimeError(
            f"Аварийный режим: records mismatch JSON={len(json_records)} "
            f"SQLite={len(sqlite_records)}"
        )
    if len(json_transfers) != len(sqlite_transfers):
        raise RuntimeError(
            f"Аварийный режим: transfers mismatch JSON={len(json_transfers)} "
            f"SQLite={len(sqlite_transfers)}"
        )

    json_repo = JsonFileRecordRepository(json_path)
    json_balances = _wallet_balances_from_json(json_repo)
    sqlite_balances = _wallet_balances_from_sqlite(sqlite_repo)

    net_worth_json = sum(json_balances.values())
    net_worth_sqlite = sum(sqlite_balances.values())
    if not math.isclose(net_worth_json, net_worth_sqlite, abs_tol=EPSILON):
        raise RuntimeError(
            f"Аварийный режим: net worth mismatch JSON={net_worth_json} SQLite={net_worth_sqlite}"
        )
    print("[bootstrap] Integrity check passed")


def bootstrap_repository() -> RecordRepository:
    if not USE_SQLITE:
        print("[bootstrap] Storage selected: JSON")
        return JsonFileRecordRepository(JSON_PATH)

    print("[bootstrap] Storage selected: SQLite")
    create_backup(JSON_PATH)

    db_has_data = _sqlite_has_data(SQLITE_PATH)
    if not db_has_data and Path(JSON_PATH).exists():
        print("[bootstrap] SQLite empty, starting one-time migration from JSON")
        code = run_migration(
            Namespace(
                json_path=JSON_PATH,
                sqlite_path=SQLITE_PATH,
                schema_path=_resolve_schema_path("db/schema.sql"),
                dry_run=False,
            )
        )
        if code != 0:
            raise RuntimeError("Аварийный режим: migration to SQLite failed")
    elif db_has_data:
        print("[bootstrap] SQLite already has data, migration skipped")
    else:
        print("[bootstrap] JSON source file not found, migration skipped")

    repository = SQLiteRecordRepository(
        SQLITE_PATH, schema_path=_resolve_schema_path("db/schema.sql")
    )
    if Path(JSON_PATH).exists():
        _validate_startup_integrity(JSON_PATH, repository)
    export_to_json(SQLITE_PATH, JSON_PATH, schema_path=_resolve_schema_path("db/schema.sql"))
    return repository
