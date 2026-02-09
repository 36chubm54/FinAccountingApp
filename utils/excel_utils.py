from typing import List
import os
from openpyxl import Workbook, load_workbook
import gc

from domain.records import (
    IncomeRecord,
    ExpenseRecord,
    MandatoryExpenseRecord,
)
from domain.reports import Report


def _safe_str(value):
    return "" if value is None else str(value)


def report_to_xlsx(report: Report, filepath: str) -> None:
    """Export Report to an XLSX file."""
    wb = Workbook()
    ws = wb.active
    if ws is not None:
        ws.title = "Report"

    if ws is not None:
        ws.append(["Date", "Type", "Category", "Amount (KZT)"])

    # initial balance
    if getattr(report, "initial_balance", 0) != 0:
        if ws is not None:
            ws.append(["", "Initial Balance", "", f"{report.initial_balance:.2f}"])

    for record in sorted(report.records(), key=lambda r: r.date):
        if isinstance(record, IncomeRecord):
            record_type = "Income"
        elif isinstance(record, MandatoryExpenseRecord):
            record_type = "Mandatory Expense"
        else:
            record_type = "Expense"
        if ws is not None:
            ws.append([record.date, record_type, record.category, f"{record.amount:.2f}"])

    total = report.total()
    records_total = sum(r.signed_amount() for r in report.records())
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
            if summary_ws is not None:
                summary_ws.append([month_label, f"{income:.2f}", f"{expense:.2f}"])
        if summary_ws is not None:
            summary_ws.append(["TOTAL", f"{total_income:.2f}", f"{total_expense:.2f}"])

    # Create a second, intermediate sheet with grouped tables by category
    try:
        groups = report.grouped_by_category()
    except Exception:
        groups = {}

    # Insert By Category sheet as the second sheet (index=1)
    bycat_ws = wb.create_sheet(title="By Category", index=1)
    # For each category, write a small table: header, rows, subtotal
    for category, subreport in sorted(groups.items(), key=lambda x: x[0] or ""):
        if bycat_ws is not None:
            bycat_ws.append([f"Category: {category}"])
            bycat_ws.append(["Date", "Type", "Amount (KZT)"])
        records_total = 0.0
        for r in sorted(subreport.records(), key=lambda rr: rr.date):
            if isinstance(r, IncomeRecord):
                r_type = "Income"
            elif isinstance(r, MandatoryExpenseRecord):
                r_type = "Mandatory Expense"
            else:
                r_type = "Expense"
            amt = getattr(r, "amount", 0.0)
            records_total += (
                getattr(r, "amount", 0.0)
                if getattr(r, "amount", None) is not None
                else 0.0
            )
            if bycat_ws is not None:
                bycat_ws.append([getattr(r, "date", ""), r_type, f"{abs(amt):.2f}"])
        if bycat_ws is not None:
            bycat_ws.append(["SUBTOTAL", "", f"{abs(records_total):.2f}"])
            bycat_ws.append([""])
    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(
        filepath
    ) else None
    wb.save(filepath)
    try:
        wb.close()
    except Exception:
        pass
    try:
        del wb
    except Exception:
        pass
    gc.collect()


def report_from_xlsx(filepath: str) -> Report:
    """Import Report from an XLSX file and return a Report object."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"XLSX file not found: {filepath}")

    wb = load_workbook(filepath, data_only=True)
    if not wb.worksheets:
        return Report([], 0.0)
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return Report([], 0.0)

    # skip header
    start = 1
    records = []
    initial_balance = 0.0

    for row in rows[start:]:
        if not row or all(cell is None for cell in row):
            continue
        date = _safe_str(row[0]).strip()
        record_type = _safe_str(row[1]).strip()
        category = _safe_str(row[2]).strip()
        amount_raw = _safe_str(row[3]).strip()

        if date.upper() in ["SUBTOTAL", "FINAL BALANCE"]:
            continue

        if date == "" and record_type.lower() == "initial balance":
            try:
                initial_balance = float(amount_raw)
            except Exception:
                initial_balance = 0.0
            continue

        try:
            amt = amount_raw
            if isinstance(amt, str):
                amt = amt.strip()
                if amt.startswith("(") and amt.endswith(")"):
                    amt = "-" + amt[1:-1]
            amount = float(amt)
        except Exception:
            continue

        if record_type.lower() == "income":
            rec = IncomeRecord(date=date, amount=abs(amount), category=category)
        elif record_type.lower() == "expense":
            rec = ExpenseRecord(date=date, amount=abs(amount), category=category)
        elif record_type.lower() == "mandatory expense":
            rec = MandatoryExpenseRecord(
                date=date,
                amount=abs(amount),
                category=category,
                description="",
                period="monthly",  # type: ignore
            )
        else:
            continue

        records.append(rec)

    try:
        return Report(records, initial_balance)
    finally:
        try:
            wb.close()
        except Exception:
            pass
        try:
            del wb
        except Exception:
            pass
        gc.collect()


def export_mandatory_expenses_to_xlsx(
    expenses: List[MandatoryExpenseRecord], filepath: str
) -> None:
    wb = Workbook()
    ws = wb.active
    if ws is not None:
        ws.title = "Mandatory"
    if ws is not None:
        ws.append(["Amount (KZT)", "Category", "Description", "Period"])

    for e in expenses:
        amount = (
            f"{getattr(e, 'amount', 0):.2f}"
            if getattr(e, "amount", None) is not None
            else "0.00"
        )
        category = getattr(e, "category", "") or ""
        description = getattr(e, "description", "") or ""
        period = getattr(e, "period", "") or ""
        if ws is not None:
            ws.append([amount, category, description, period])

    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(
        filepath
    ) else None
    wb.save(filepath)
    try:
        wb.close()
    except Exception:
        pass
    try:
        del wb
    except Exception:
        pass
    gc.collect()


def import_mandatory_expenses_from_xlsx(filepath: str) -> List[MandatoryExpenseRecord]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"XLSX file not found: {filepath}")

    wb = load_workbook(filepath, data_only=True)
    ws = wb.active
    if ws is None:
        return []
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        return []

    expenses: List[MandatoryExpenseRecord] = []
    for row in rows[1:]:
        if not row or all(cell is None for cell in row):
            continue
        amount_raw = _safe_str(row[0]).strip()
        category = _safe_str(row[1]).strip()
        description = _safe_str(row[2]).strip()
        period = _safe_str(row[3]).strip().lower()

        try:
            amount = float(amount_raw)
        except Exception:
            continue

        valid_periods = ["daily", "weekly", "monthly", "yearly"]
        if period not in valid_periods:
            continue

        expense = MandatoryExpenseRecord(
            date="",
            amount=amount,
            category=category,
            description=description,
            period=period,  # type: ignore
        )
        expenses.append(expense)

    try:
        return expenses
    finally:
        try:
            wb.close()
        except Exception:
            pass
        try:
            del wb
        except Exception:
            pass
        gc.collect()
