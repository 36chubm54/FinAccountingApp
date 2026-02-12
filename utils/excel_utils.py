from typing import List, Tuple
import os
import gc

from openpyxl import Workbook, load_workbook

from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord, Record
from domain.reports import Report

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


def _safe_str(value):
    return "" if value is None else str(value)


def _as_float(value, default: float = 0.0) -> float:
    try:
        raw = str(value).strip()
        if raw.startswith("(") and raw.endswith(")"):
            raw = "-" + raw[1:-1]
        return float(raw)
    except (TypeError, ValueError):
        return default


def _record_type_name(record: Record) -> str:
    if isinstance(record, IncomeRecord):
        return "income"
    if isinstance(record, MandatoryExpenseRecord):
        return "mandatory_expense"
    return "expense"


def report_to_xlsx(report: Report, filepath: str) -> None:
    """Export report view (fixed amounts) to XLSX. Read-only format."""
    wb = Workbook()
    ws = wb.active
    if ws is not None:
        ws.title = "Report"
        ws.append(["Date", "Type", "Category", "Amount (KZT)"])
        ws.append(["", "", "", "Fixed amounts by operation-time FX rates"])

    if getattr(report, "initial_balance", 0) != 0 and ws is not None:
        ws.append(["", "Initial Balance", "", f"{report.initial_balance:.2f}"])

    for record in sorted(report.records(), key=lambda r: r.date):
        if isinstance(record, IncomeRecord):
            record_type = "Income"
        elif isinstance(record, MandatoryExpenseRecord):
            record_type = "Mandatory Expense"
        else:
            record_type = "Expense"
        if ws is not None:
            ws.append(
                [record.date, record_type, record.category, f"{record.amount_kzt:.2f}"]
            )

    total = report.total_fixed()
    records_total = sum(r.signed_amount_kzt() for r in report.records())
    if ws is not None:
        ws.append(["SUBTOTAL", "", "", f"{records_total:.2f}"])
        ws.append(["FINAL BALANCE", "", "", f"{total:.2f}"])

    summary_year, monthly_rows = report.monthly_income_expense_rows()
    summary_ws = wb.create_sheet("Yearly Report")
    if summary_ws is not None:
        summary_ws.append([f"Month ({summary_year})", "Income (KZT)", "Expense (KZT)"])
        total_income = 0.0
        total_expense = 0.0
        for month_label, income, expense in monthly_rows:
            total_income += income
            total_expense += expense
            summary_ws.append([month_label, f"{income:.2f}", f"{expense:.2f}"])
        summary_ws.append(["TOTAL", f"{total_income:.2f}", f"{total_expense:.2f}"])

    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
    wb.save(filepath)
    try:
        wb.close()
    except Exception:
        pass
    gc.collect()


def export_records_to_xlsx(
    records: List[Record], filepath: str, initial_balance: float = 0.0
) -> None:
    wb = Workbook()
    ws = wb.active
    if ws is not None:
        ws.title = "Data"
        ws.append(DATA_HEADERS)
        ws.append(["", "initial_balance", "", initial_balance, "KZT", 1.0, initial_balance, "", ""])

    for record in records:
        payload = [
            record.date,
            _record_type_name(record),
            record.category,
            record.amount_original,
            record.currency,
            record.rate_at_operation,
            record.amount_kzt,
            "",
            "",
        ]
        if isinstance(record, MandatoryExpenseRecord):
            payload[7] = record.description
            payload[8] = record.period
        if ws is not None:
            ws.append(payload)

    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
    wb.save(filepath)
    try:
        wb.close()
    except Exception:
        pass
    gc.collect()


def _parse_record_row(raw: dict) -> Record | None:
    date = _safe_str(raw.get("date", "")).strip()
    typ = _safe_str(raw.get("type", "")).strip().lower().replace(" ", "_")
    category = _safe_str(raw.get("category", "General")).strip() or "General"

    if "amount_kzt" in raw and raw.get("amount_kzt") not in (None, ""):
        amount_kzt = _as_float(raw.get("amount_kzt"), 0.0)
        amount_original = _as_float(raw.get("amount_original"), amount_kzt)
        currency = _safe_str(raw.get("currency", "KZT")).strip().upper() or "KZT"
        rate = _as_float(raw.get("rate_at_operation"), 1.0)
    else:
        legacy_amount = _as_float(raw.get("amount", raw.get("amount_(kzt)", 0.0)), 0.0)
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

    if typ == "income":
        return IncomeRecord(**common)
    if typ == "expense":
        common["amount_original"] = abs(common["amount_original"])
        common["amount_kzt"] = abs(common["amount_kzt"])
        return ExpenseRecord(**common)
    if typ in {"mandatory_expense", "mandatoryexpense", "mandatory"}:
        common["amount_original"] = abs(common["amount_original"])
        common["amount_kzt"] = abs(common["amount_kzt"])
        period = _safe_str(raw.get("period", "monthly")).strip().lower() or "monthly"
        if period not in {"daily", "weekly", "monthly", "yearly"}:
            period = "monthly"
        return MandatoryExpenseRecord(
            **common,
            description=_safe_str(raw.get("description", "")).strip(),
            period=period,  # type: ignore[arg-type]
        )
    return None


def import_records_from_xlsx(filepath: str) -> Tuple[List[Record], float]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"XLSX file not found: {filepath}")

    wb = load_workbook(filepath, data_only=True)
    try:
        if not wb.worksheets:
            return [], 0.0

        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return [], 0.0

        headers = [_safe_str(h).strip().lower().replace(" ", "_") for h in rows[0]]
        records: List[Record] = []
        initial_balance = 0.0

        is_report_xlsx = {"date", "type", "category", "amount_(kzt)"}.issubset(set(headers))

        for row in rows[1:]:
            if not row or all(cell is None for cell in row):
                continue

            raw = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            row_type = _safe_str(raw.get("type", "")).strip().lower().replace(" ", "_")

            if is_report_xlsx:
                date_cell = _safe_str(raw.get("date", "")).strip()
                if date_cell.upper() in {"SUBTOTAL", "FINAL_BALANCE", "FINAL BALANCE"}:
                    continue
                if date_cell == "" and row_type == "initial_balance":
                    initial_balance = _as_float(raw.get("amount_(kzt)", 0.0), 0.0)
                    continue
                raw["amount"] = raw.get("amount_(kzt)", 0.0)
            elif row_type == "initial_balance":
                initial_balance = _as_float(
                    raw.get("amount_original", raw.get("amount_kzt", 0.0)), 0.0
                )
                continue

            record = _parse_record_row(raw)
            if record is not None:
                records.append(record)

        return records, initial_balance
    finally:
        try:
            wb.close()
        except Exception:
            pass
        gc.collect()


def report_from_xlsx(filepath: str) -> Report:
    records, initial_balance = import_records_from_xlsx(filepath)
    return Report(records, initial_balance)


def export_mandatory_expenses_to_xlsx(
    expenses: List[MandatoryExpenseRecord], filepath: str
) -> None:
    wb = Workbook()
    ws = wb.active
    if ws is not None:
        ws.title = "Mandatory"
        ws.append(DATA_HEADERS)

    for e in expenses:
        if ws is not None:
            ws.append(
                [
                    e.date,
                    "mandatory_expense",
                    e.category,
                    e.amount_original,
                    e.currency,
                    e.rate_at_operation,
                    e.amount_kzt,
                    e.description,
                    e.period,
                ]
            )

    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
    wb.save(filepath)
    try:
        wb.close()
    except Exception:
        pass
    gc.collect()


def import_mandatory_expenses_from_xlsx(filepath: str) -> List[MandatoryExpenseRecord]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"XLSX file not found: {filepath}")

    records, _ = import_records_from_xlsx(filepath)
    return [r for r in records if isinstance(r, MandatoryExpenseRecord)]
