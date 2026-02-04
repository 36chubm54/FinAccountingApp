from typing import List
import os
import io
import csv
import gc
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib import colors


from domain.records import IncomeRecord, MandatoryExpenseRecord
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
    # Build table data
    data = []
    header = ["Date", "Type", "Category", "Amount (KZT)"]
    data.append(header)

    if getattr(report, "initial_balance", 0) != 0:
        data.append(["", "Initial Balance", "", f"{report.initial_balance:.2f}"])

    for record in sorted(report.records(), key=lambda r: r.date):
        if isinstance(record, IncomeRecord):
            record_type = "Income"
        elif isinstance(record, MandatoryExpenseRecord):
            record_type = "Mandatory Expense"
        else:
            record_type = "Expense"
        data.append(
            [
                _safe_str(record.date),
                record_type,
                _safe_str(record.category),
                f"{record.amount:.2f}",
            ]
        )

    total = report.total()
    records_total = sum(r.signed_amount() for r in report.records())
    data.append(["SUBTOTAL", "", "", f"{records_total:.2f}"])
    data.append(["FINAL BALANCE", "", "", f"{total:.2f}"])

    # Ensure directory
    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(
        filepath
    ) else None

    # Build PDF with a Table for nicer tabular layout and word-wrap
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    available_width = A4[0] - 60
    col_widths = [
        available_width * 0.18,
        available_width * 0.22,
        available_width * 0.40,
        available_width * 0.20,
    ]

    font_name = _register_cyrillic_font()
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle(
        [
            ("FONT", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )
    table.setStyle(style)
    elems = [table]

    summary_year, monthly_rows = report.monthly_income_expense_rows()
    summary_header = [f"Month ({summary_year})", "Income (KZT)", "Expense (KZT)"]
    summary_data = [summary_header]
    total_income = 0.0
    total_expense = 0.0
    for month_label, income, expense in monthly_rows:
        total_income += income
        total_expense += expense
        summary_data.append(
            [month_label, f"{income:.2f}", f"{expense:.2f}"]
        )
    summary_data.append(
        ["TOTAL", f"{total_income:.2f}", f"{total_expense:.2f}"]
    )

    summary_col_widths = [
        available_width * 0.30,
        available_width * 0.35,
        available_width * 0.35,
    ]
    summary_table = Table(summary_data, colWidths=summary_col_widths, repeatRows=1)
    summary_style = TableStyle(
        [
            ("FONT", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )
    summary_table.setStyle(summary_style)
    elems.append(Spacer(1, 14))
    elems.append(summary_table)

    doc.build(elems)
    gc.collect()


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

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    available_width = A4[0] - 60
    col_widths = [
        available_width * 0.18,
        available_width * 0.22,
        available_width * 0.40,
        available_width * 0.20,
    ]

    font_name = _register_cyrillic_font()
    data = []
    header = ["Amount (KZT)", "Category", "Description", "Period"]
    data.append(header)
    for e in expenses:
        amt = (
            f"{getattr(e, 'amount', 0):.2f}"
            if getattr(e, "amount", None) is not None
            else "0.00"
        )
        data.append(
            [
                amt,
                _safe_str(getattr(e, "category", "")),
                _safe_str(getattr(e, "description", "")),
                _safe_str(getattr(e, "period", "")),
            ]
        )

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle(
        [
            ("FONT", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )
    table.setStyle(style)
    elems = [table]
    doc.build(elems)
    gc.collect()
