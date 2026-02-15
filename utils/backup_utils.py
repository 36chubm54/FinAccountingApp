import json
import os
from typing import List, Tuple

from domain.import_policy import ImportPolicy
from domain.records import MandatoryExpenseRecord, Record
from utils.import_core import ImportSummary, parse_import_row, record_type_name


def export_full_backup_to_json(
    filepath: str,
    *,
    initial_balance: float,
    records: List[Record],
    mandatory_expenses: List[MandatoryExpenseRecord],
) -> None:
    payload_records = []
    for record in records:
        item = {
            "date": record.date,
            "type": record_type_name(record),
            "category": record.category,
            "amount_original": record.amount_original,
            "currency": record.currency,
            "rate_at_operation": record.rate_at_operation,
            "amount_kzt": record.amount_kzt,
            "description": "",
            "period": "",
        }
        if isinstance(record, MandatoryExpenseRecord):
            item["description"] = record.description
            item["period"] = record.period
        payload_records.append(item)

    payload_mandatory = []
    for expense in mandatory_expenses:
        payload_mandatory.append(
            {
                "date": expense.date,
                "type": "mandatory_expense",
                "category": expense.category,
                "amount_original": expense.amount_original,
                "currency": expense.currency,
                "rate_at_operation": expense.rate_at_operation,
                "amount_kzt": expense.amount_kzt,
                "description": expense.description,
                "period": expense.period,
            }
        )

    payload = {
        "initial_balance": float(initial_balance),
        "records": payload_records,
        "mandatory_expenses": payload_mandatory,
    }

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def import_full_backup_from_json(
    filepath: str,
) -> Tuple[float, List[Record], List[MandatoryExpenseRecord], ImportSummary]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, dict):
        raise ValueError("Invalid backup JSON structure: root must be object")

    initial_balance = float(data.get("initial_balance", 0.0))
    raw_records = data.get("records", [])
    raw_mandatory = data.get("mandatory_expenses", [])

    if not isinstance(raw_records, list) or not isinstance(raw_mandatory, list):
        raise ValueError(
            "Invalid backup JSON structure: records and mandatory_expenses must be arrays"
        )

    records: List[Record] = []
    mandatory_expenses: List[MandatoryExpenseRecord] = []
    errors: List[str] = []
    skipped = 0
    imported = 0

    for idx, item in enumerate(raw_records, start=1):
        if not isinstance(item, dict):
            skipped += 1
            errors.append(f"records[{idx}]: invalid item type")
            continue
        record, _, error = parse_import_row(
            item,
            row_label=f"records[{idx}]",
            policy=ImportPolicy.FULL_BACKUP,
        )
        if error:
            skipped += 1
            errors.append(error)
            continue
        if record is not None:
            imported += 1
            records.append(record)

    for idx, item in enumerate(raw_mandatory, start=1):
        if not isinstance(item, dict):
            skipped += 1
            errors.append(f"mandatory_expenses[{idx}]: invalid item type")
            continue
        item = dict(item)
        item["type"] = "mandatory_expense"
        record, _, error = parse_import_row(
            item,
            row_label=f"mandatory_expenses[{idx}]",
            policy=ImportPolicy.FULL_BACKUP,
            mandatory_only=True,
        )
        if error:
            skipped += 1
            errors.append(error)
            continue
        if isinstance(record, MandatoryExpenseRecord):
            imported += 1
            mandatory_expenses.append(record)

    return initial_balance, records, mandatory_expenses, (imported, skipped, errors)
