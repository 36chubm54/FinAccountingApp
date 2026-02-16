import csv
import logging
import os
from typing import List, Tuple

from domain.import_policy import ImportPolicy
from domain.records import MandatoryExpenseRecord, Record
from domain.reports import Report
from utils.import_core import (
    ImportSummary,
    norm_key,
    parse_import_row,
    record_type_name,
)

logger = logging.getLogger(__name__)

REPORT_HEADERS = ["Date", "Type", "Category", "Amount (KZT)"]
DATA_HEADERS = [
    "date",
    "type",
    "category",
    "amount_original",
    "currency",
    "rate_at_operation",
    "amount_kzt",
    "description",
    "period",
]


def _resolve_get_rate(currency_service):
    if currency_service is None:
        from app.services import CurrencyService

        currency_service = CurrencyService()
    return currency_service.get_rate


def report_to_csv(report: Report, filepath: str) -> None:
    """Export report view (fixed amounts) to CSV. Read-only format."""
    sorted_records = sorted(report.records(), key=lambda r: r.date)
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([report.statement_title, "", "", ""])
        writer.writerow(REPORT_HEADERS)
        writer.writerow(["", "", "", "Fixed amounts by operation-time FX rates"])

        if report.initial_balance != 0 or report.is_opening_balance:
            writer.writerow(
                ["", report.balance_label, "", f"{report.initial_balance:.2f}"]
            )

        for record in sorted_records:
            if record_type_name(record) == "income":
                record_type = "Income"
            elif record_type_name(record) == "mandatory_expense":
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            writer.writerow(
                [record.date, record_type, record.category, f"{record.amount_kzt:.2f}"]
            )

        records_total = sum(r.signed_amount_kzt() for r in report.records())
        writer.writerow(["SUBTOTAL", "", "", f"{records_total:.2f}"])
        writer.writerow(["FINAL BALANCE", "", "", f"{report.total_fixed():.2f}"])


def report_from_csv(filepath: str) -> Report:
    """Backward-compatible helper. Prefers data CSV and supports legacy report CSV."""
    records, initial_balance, _ = import_records_from_csv(filepath, ImportPolicy.LEGACY)
    return Report(records, initial_balance)


def export_records_to_csv(
    records: List[Record], filepath: str, initial_balance: float = 0.0
) -> None:
    """Export full data model to CSV for backup/restore."""
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=DATA_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "date": "",
                "type": "initial_balance",
                "category": "",
                "amount_original": initial_balance,
                "currency": "KZT",
                "rate_at_operation": 1.0,
                "amount_kzt": initial_balance,
                "description": "",
                "period": "",
            }
        )

        for record in records:
            payload = {
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
                payload["description"] = record.description
                payload["period"] = record.period
            writer.writerow(payload)


def import_records_from_csv(
    filepath: str,
    policy: ImportPolicy = ImportPolicy.FULL_BACKUP,
    currency_service=None,
) -> Tuple[List[Record], float, ImportSummary]:
    """Import full data model from CSV with validation and per-row error report."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    records: List[Record] = []
    initial_balance = 0.0
    errors: List[str] = []
    skipped = 0
    imported = 0

    get_rate = None
    if policy == ImportPolicy.CURRENT_RATE:
        get_rate = _resolve_get_rate(currency_service)

    with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
        preview_reader = csv.reader(csvfile)
        first_row = next(preview_reader, [])
        if first_row and str(first_row[0]).strip().startswith("Transaction statement"):
            pass
        else:
            csvfile.seek(0)
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames:
            return records, initial_balance, (0, 0, [])

        normalized_headers = {norm_key(h) for h in reader.fieldnames if h}
        is_report_csv = {"date", "type", "category", "amount_(kzt)"}.issubset(
            normalized_headers
        ) and "amount_original" not in normalized_headers

        for idx, row in enumerate(reader, start=2):
            row_lc = {norm_key(str(k)): v for k, v in row.items()}
            if not any(str(v or "").strip() for v in row_lc.values()):
                continue

            if is_report_csv:
                date_value = str(row_lc.get("date", "") or "").strip()
                if date_value.upper() in {"SUBTOTAL", "FINAL BALANCE"}:
                    continue
                if date_value == "" and str(
                    row_lc.get("type", "") or ""
                ).strip().lower() in {"initial balance", "opening balance"}:
                    row_lc["type"] = "initial_balance"
                    row_lc["amount_original"] = row_lc.get("amount_(kzt)")
                else:
                    row_lc["amount"] = row_lc.get("amount_(kzt)")

            record, parsed_balance, error = parse_import_row(
                row_lc,
                row_label=f"row {idx}",
                policy=policy,
                get_rate=get_rate,
                mandatory_only=False,
            )
            if error:
                skipped += 1
                errors.append(error)
                logger.warning("CSV import skipped %s", error)
                continue
            if parsed_balance is not None:
                initial_balance = parsed_balance
                continue
            if record is None:
                continue
            imported += 1
            records.append(record)

    return records, initial_balance, (imported, skipped, errors)


def export_mandatory_expenses_to_csv(
    expenses: List[MandatoryExpenseRecord], filepath: str
) -> None:
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=DATA_HEADERS)
        writer.writeheader()
        for expense in expenses:
            writer.writerow(
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


def import_mandatory_expenses_from_csv(
    filepath: str,
    policy: ImportPolicy = ImportPolicy.FULL_BACKUP,
    currency_service=None,
) -> Tuple[List[MandatoryExpenseRecord], ImportSummary]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    expenses: List[MandatoryExpenseRecord] = []
    errors: List[str] = []
    skipped = 0
    imported = 0

    get_rate = None
    if policy == ImportPolicy.CURRENT_RATE:
        get_rate = _resolve_get_rate(currency_service)

    with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames:
            return expenses, (0, 0, [])

        for idx, row in enumerate(reader, start=2):
            row_lc = {norm_key(str(k)): v for k, v in row.items()}
            if not any(str(v or "").strip() for v in row_lc.values()):
                continue

            record, _, error = parse_import_row(
                row_lc,
                row_label=f"row {idx}",
                policy=policy,
                get_rate=get_rate,
                mandatory_only=True,
            )
            if error:
                skipped += 1
                errors.append(error)
                logger.warning("Mandatory CSV import skipped %s", error)
                continue
            if isinstance(record, MandatoryExpenseRecord):
                imported += 1
                expenses.append(record)

    return expenses, (imported, skipped, errors)
