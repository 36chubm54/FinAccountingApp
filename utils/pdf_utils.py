from typing import List
import os
import io
import csv
import gc
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
from domain.reports import Report


def _safe_str(value):
    return "" if value is None else str(value)


def _register_cyrillic_font() -> str:
    """Try to register a TTF font that supports Cyrillic and return its name.

    Tries common locations for DejaVuSans and Windows Arial. Falls back to
    built-in Helvetica (may not render Cyrillic correctly).
    """
    # Candidate paths
    candidates = []
    # Common Linux path for DejaVu
    candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    # Windows Fonts
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if windir:
        candidates.append(os.path.join(windir, "Fonts", "DejaVuSans.ttf"))
        candidates.append(os.path.join(windir, "Fonts", "Arial.ttf"))
        candidates.append(os.path.join(windir, "Fonts", "Times.ttf"))
    # Try venv/share or local
    candidates.append("DejaVuSans.ttf")

    for path in candidates:
        try:
            if path and os.path.exists(path):
                name = os.path.splitext(os.path.basename(path))[0]
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    return name
                except Exception:
                    continue
        except Exception:
            continue

    # Last resort: try to register by name (may work if font already available)
    for name in ("DejaVuSans", "Arial", "TimesNewRoman"):
        try:
            pdfmetrics.registerFont(TTFont(name, name))
            return name
        except Exception:
            continue

    # Fallback to a built-in font
    return "Helvetica"


def report_to_pdf(report: Report, filepath: str) -> None:
    """Export report as a text-based PDF (contains CSV-like lines)."""
    # Build CSV-like text in memory
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Type", "Category", "Amount (KZT)"])

    if getattr(report, "_initial_balance", 0) != 0:
        writer.writerow(["", "Initial Balance", "", f"{report._initial_balance:.2f}"])

    for record in sorted(report.records(), key=lambda r: r.date):
        if isinstance(record, IncomeRecord):
            record_type = "Income"
        elif isinstance(record, MandatoryExpenseRecord):
            record_type = "Mandatory Expense"
        else:
            record_type = "Expense"
        writer.writerow(
            [
                _safe_str(record.date),
                record_type,
                _safe_str(record.category),
                f"{record.amount:.2f}",
            ]
        )

    total = report.total()
    records_total = sum(r.signed_amount() for r in report.records())
    writer.writerow(["SUBTOTAL", "", "", f"{records_total:.2f}"])
    writer.writerow(["FINAL BALANCE", "", "", f"{total:.2f}"])

    text = buf.getvalue()
    buf.close()

    # Render text into PDF
    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(
        filepath
    ) else None
    c = canvas.Canvas(filepath, pagesize=A4)
    height = A4[1]  # Height of A4 page in points
    lines = text.splitlines()
    y = height - 40
    font_name = _register_cyrillic_font()
    # Use a monospaced-like size; registered font may not be monospaced
    font_size = 10
    for line in lines:
        try:
            c.setFont(font_name, font_size)
        except Exception:
            c.setFont("Helvetica", font_size)
        c.drawString(30, y, line)
        y -= 14
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    try:
        del c
    except Exception:
        pass
    gc.collect()


def report_from_pdf(filepath: str) -> Report:
    """Import report from a PDF previously exported by report_to_pdf."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    reader = PdfReader(filepath)
    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(text_parts)

    # Parse CSV-like content
    buf = io.StringIO(text)
    rows = list(csv.reader(buf))
    buf.close()

    if not rows:
        return Report([], 0.0)

    records = []
    initial_balance = 0.0
    start = 1
    for row in rows[start:]:
        if not row or all(cell.strip() == "" for cell in row):
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
                period="monthly",
            )
        else:
            continue

        records.append(rec)

    try:
        del reader
    except Exception:
        pass
    gc.collect()
    return Report(records, initial_balance)


def export_mandatory_expenses_to_pdf(
    expenses: List[MandatoryExpenseRecord], filepath: str
) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Amount (KZT)", "Category", "Description", "Period"])
    for e in expenses:
        amt = (
            f"{getattr(e, 'amount', 0):.2f}"
            if getattr(e, "amount", None) is not None
            else "0.00"
        )
        writer.writerow(
            [
                amt,
                _safe_str(getattr(e, "category", "")),
                _safe_str(getattr(e, "description", "")),
                _safe_str(getattr(e, "period", "")),
            ]
        )
    text = buf.getvalue()
    buf.close()

    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(
        filepath
    ) else None
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    lines = text.splitlines()
    y = height - 40
    font_name = _register_cyrillic_font()
    font_size = 10
    for line in lines:
        try:
            c.setFont(font_name, font_size)
        except Exception:
            c.setFont("Helvetica", font_size)
        c.drawString(30, y, line)
        y -= 14
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    try:
        del c
    except Exception:
        pass
    gc.collect()


def import_mandatory_expenses_from_pdf(filepath: str) -> List[MandatoryExpenseRecord]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF file not found: {filepath}")
    reader = PdfReader(filepath)
    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(text_parts)
    buf = io.StringIO(text)
    rows = list(csv.reader(buf))
    buf.close()
    expenses: List[MandatoryExpenseRecord] = []
    for row in rows[1:]:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        try:
            amount = float(_safe_str(row[0]).strip())
        except Exception:
            continue
        category = _safe_str(row[1]).strip()
        description = _safe_str(row[2]).strip()
        period = _safe_str(row[3]).strip().lower()
        valid_periods = ["daily", "weekly", "monthly", "yearly"]
        if period not in valid_periods:
            continue
        expense = MandatoryExpenseRecord(
            date="",
            amount=amount,
            category=category,
            description=description,
            period=period,
        )
        expenses.append(expense)
    try:
        del reader
    except Exception:
        pass
    gc.collect()
    return expenses
