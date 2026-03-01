from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from infrastructure.repositories import JsonFileRecordRepository
from storage.json_storage import JsonStorage
from storage.sqlite_storage import SQLiteStorage


def create_backup(json_path: str) -> str | None:
    source = Path(json_path)
    if not source.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = source.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"{source.stem}_backup_{stamp}{source.suffix}"
    shutil.copy2(source, backup_path)
    print(f"[backup] JSON backup created: {backup_path}")
    return str(backup_path)


def export_to_json(sqlite_path: str, json_path: str, schema_path: str | None = None) -> None:
    sqlite_storage = SQLiteStorage(sqlite_path)
    try:
        sqlite_storage.initialize_schema(schema_path)
        wallets = sqlite_storage.get_wallets()
        records = sqlite_storage.get_records()
        transfers = sqlite_storage.get_transfers()
        mandatory_expenses = sqlite_storage.get_mandatory_expenses()

        writer = JsonStorage(json_path)
        writer_repo = writer._repo
        if not isinstance(writer_repo, JsonFileRecordRepository):
            raise RuntimeError("JsonStorage writer is not backed by JsonFileRecordRepository")
        writer_repo.replace_all_data(
            wallets=wallets,
            records=records,
            mandatory_expenses=mandatory_expenses,
            transfers=transfers,
        )
        print(f"[backup] SQLite exported to JSON: {json_path}")
    finally:
        sqlite_storage.close()
