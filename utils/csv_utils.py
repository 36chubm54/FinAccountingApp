import csv
import os
from typing import List, Tuple

from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord, Record
from domain.reports import Report


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


def _norm_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _as_float(value, default: float = 0.0) -> float:
    try:
        raw = str(value).strip()
        if raw.startswith("(") and raw.endswith(")"):
            raw = "-" + raw[1:-1]
        return float(raw)
    except (TypeError, ValueError):
        return default


def _safe_type(value: str) -> str:
    normalized = _norm_key(value)
    if normalized in {"income", "expense", "mandatory_expense"}:
        return normalized
    if normalized in {"mandatory_expense_record", "mandatory_expenses"}:
        return "mandatory_expense"
    if normalized in {"mandatory", "mandatoryexpense", "mandatory_expense"}:
        return "mandatory_expense"
    return normalized


def _record_type_name(record: Record) -> str:
    if isinstance(record, IncomeRecord):
        return "income"
    if isinstance(record, MandatoryExpenseRecord):
        return "mandatory_expense"
    return "expense"


def _parse_data_row(row: dict) -> Record | None:
    row_lc = {_norm_key(str(k)): v for k, v in row.items()}

    date = str(row_lc.get("date", "") or "")
    record_type = _safe_type(str(row_lc.get("type", "") or ""))
    category = str(row_lc.get("category", "General") or "General")

    if "amount_kzt" in row_lc:
        amount_kzt = _as_float(row_lc.get("amount_kzt"), 0.0)
        amount_original = _as_float(row_lc.get("amount_original"), amount_kzt)
        currency = str(row_lc.get("currency", "KZT") or "KZT").upper()
        rate = _as_float(row_lc.get("rate_at_operation"), 1.0)
    else:
        legacy_amount = _as_float(
            row_lc.get("amount", row_lc.get("amount_(kzt)", row_lc.get("amount_kzt", 0.0))),
            0.0,
        )
        amount_original = legacy_amount
        amount_kzt = legacy_amount
        currency = "KZT"
        rate = 1.0

    common = {
        "date": date,
        "amount_original": amount_original,
        "currency": currency,
        "rate_at_operation": rate,
        "amount_kzt": amount_kzt,
        "category": category,
    }

    if record_type == "income":
        return IncomeRecord(**common)
    if record_type == "expense":
        common["amount_original"] = abs(common["amount_original"])
        common["amount_kzt"] = abs(common["amount_kzt"])
        return ExpenseRecord(**common)
    if record_type in {"mandatory_expense", "mandatory expense"}:
        common["amount_original"] = abs(common["amount_original"])
        common["amount_kzt"] = abs(common["amount_kzt"])
        period = str(row_lc.get("period", "monthly") or "monthly").lower()
        if period not in {"daily", "weekly", "monthly", "yearly"}:
            period = "monthly"
        return MandatoryExpenseRecord(
            **common,
            description=str(row_lc.get("description", "") or ""),
            period=period,  # type: ignore[arg-type]
        )
    return None


def report_to_csv(report: Report, filepath: str) -> None:
    """Export report view (fixed amounts) to CSV. Read-only format."""
    sorted_records = sorted(report.records(), key=lambda r: r.date)
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(REPORT_HEADERS)
        writer.writerow(["", "", "", "Fixed amounts by operation-time FX rates"])

        if report.initial_balance != 0:
            writer.writerow(["", "Initial Balance", "", f"{report.initial_balance:.2f}"])

        for record in sorted_records:
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            writer.writerow(
                [record.date, record_type, record.category, f"{record.amount_kzt:.2f}"]
            )

        records_total = sum(r.signed_amount_kzt() for r in report.records())
        writer.writerow(["SUBTOTAL", "", "", f"{records_total:.2f}"])
        writer.writerow(["FINAL BALANCE", "", "", f"{report.total_fixed():.2f}"])


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
                "type": _record_type_name(record),
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


def import_records_from_csv(filepath: str) -> Tuple[List[Record], float]:
    """Import full data model from CSV. Supports legacy CSV with `amount` only."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    records: List[Record] = []
    initial_balance = 0.0

    with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames:
            return records, initial_balance

        normalized_headers = {_norm_key(h) for h in reader.fieldnames if h}
        is_report_csv = {"date", "type", "category", "amount_(kzt)"}.issubset(
            normalized_headers
        ) and "amount_original" not in normalized_headers

        for row in reader:
            row_lc = {_norm_key(str(k)): v for k, v in row.items()}
            if not any(str(v or "").strip() for v in row_lc.values()):
                continue

            row_type = _safe_type(str(row_lc.get("type", "") or "")).lower()

            if is_report_csv:
                date = str(row_lc.get("date", "") or "")
                if date.upper() in {"SUBTOTAL", "FINAL BALANCE"}:
                    continue
                if (
                    date.strip() == ""
                    and str(row_lc.get("type", "")).strip().lower() == "initial balance"
                ):
                    initial_balance = _as_float(row_lc.get("amount_(kzt)", 0.0), 0.0)
                    continue
                row_lc["amount"] = row_lc.get("amount_(kzt)", 0.0)
            elif row_type == "initial_balance":
                initial_balance = _as_float(
                    row_lc.get("amount_original", row_lc.get("amount_kzt", 0.0)), 0.0
                )
                continue

            record = _parse_data_row(row_lc)
            if record is not None:
                records.append(record)

    return records, initial_balance


def report_from_csv(filepath: str) -> Report:
    """Backward-compatible helper. Prefers data CSV and supports legacy report CSV."""
    records, initial_balance = import_records_from_csv(filepath)
    return Report(records, initial_balance)


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


def import_mandatory_expenses_from_csv(filepath: str) -> List[MandatoryExpenseRecord]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    expenses: List[MandatoryExpenseRecord] = []
    with open(filepath, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames:
            return expenses

        for row in reader:
            row_lc = {_norm_key(str(k)): v for k, v in row.items()}
            if not any(str(v or "").strip() for v in row_lc.values()):
                continue

            record_type = _safe_type(str(row_lc.get("type", "mandatory_expense") or ""))
            if record_type not in {"mandatory_expense", "mandatory expense"}:
                # Legacy mandatory-only CSV has no type column.
                if "type" in row_lc:
                    continue

            if "amount_kzt" not in row_lc:
                amount = _as_float(
                    row_lc.get("amount", row_lc.get("amount_(kzt)", 0.0)), 0.0
                )
                row_lc["amount_original"] = amount
                row_lc["amount_kzt"] = amount
                row_lc["currency"] = "KZT"
                row_lc["rate_at_operation"] = 1.0

            period = str(row_lc.get("period", "monthly") or "monthly").lower()
            if period not in {"daily", "weekly", "monthly", "yearly"}:
                continue

            expenses.append(
                MandatoryExpenseRecord(
                    date=str(row_lc.get("date", "") or ""),
                    amount_original=_as_float(row_lc.get("amount_original"), 0.0),
                    currency=str(row_lc.get("currency", "KZT") or "KZT").upper(),
                    rate_at_operation=_as_float(row_lc.get("rate_at_operation"), 1.0),
                    amount_kzt=_as_float(row_lc.get("amount_kzt"), 0.0),
                    category=str(row_lc.get("category", "Mandatory") or "Mandatory"),
                    description=str(row_lc.get("description", "") or ""),
                    period=period,  # type: ignore[arg-type]
                )
            )

    return expenses
