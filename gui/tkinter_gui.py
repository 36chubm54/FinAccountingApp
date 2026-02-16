import sys
from typing import Union, Dict, Optional
import tkinter as tk
from tkinter import ttk
import logging
from pathlib import Path
from tkinter import (
    messagebox,
    Listbox,
    Scrollbar,
    VERTICAL,
    filedialog,
)
import os
from datetime import datetime

from infrastructure.repositories import JsonFileRecordRepository
from app.use_cases import (
    CreateIncome,
    CreateExpense,
    GenerateReport,
    DeleteRecord,
    DeleteAllRecords,
    CreateMandatoryExpense,
    GetMandatoryExpenses,
    DeleteMandatoryExpense,
    DeleteAllMandatoryExpenses,
    AddMandatoryExpenseToReport,
)
from domain.records import IncomeRecord, MandatoryExpenseRecord
from domain.import_policy import ImportPolicy
from app.services import CurrencyService
from domain.reports import Report
from utils.charting import (
    aggregate_expenses_by_category,
    aggregate_daily_cashflow,
    aggregate_monthly_cashflow,
    extract_months,
    extract_years,
)

from gui.helpers import open_in_file_manager

logger = logging.getLogger(__name__)


# Ensure project package root is on sys.path so imports work regardless of CWD
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

IMPORT_FORMATS = {
    "CSV": {
        "ext": ".csv",
        "desc": "CSV",
    },
    "XLSX": {
        "ext": ".xlsx",
        "desc": "Excel",
    },
    "JSON": {
        "ext": ".json",
        "desc": "JSON",
    },
}


class FinancialApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Financial Accounting")
        self.geometry("1000x800")
        self.minsize(900, 600)

        self.repository = JsonFileRecordRepository(
            str(Path(__file__).resolve().parent.parent / "records.json")
        )
        self.currency = CurrencyService()

        # Build main Notebook with four tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_infographics = ttk.Frame(notebook)
        self.tab_operations = ttk.Frame(notebook)
        self.tab_reports = ttk.Frame(notebook)
        self.tab_settings = ttk.Frame(notebook)

        notebook.add(self.tab_infographics, text="Infographics")
        notebook.add(self.tab_operations, text="Operations")
        notebook.add(self.tab_reports, text="Reports")
        notebook.add(self.tab_settings, text="Settings")

        # Build UI inside tabs
        self.infographics_tab(self.tab_infographics)
        self.operations_tab(self.tab_operations)
        self.reports_tab(self.tab_reports)
        self.settings_tab(self.tab_settings)

        # Initial data refresh
        self._refresh_charts()

    def infographics_tab(self, parent: Union[tk.Frame, ttk.Frame]) -> None:
        pie_frame = tk.LabelFrame(parent, text="Expenses by category")
        pie_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        pie_controls = tk.Frame(pie_frame)
        pie_controls.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(pie_controls, text="Month:").pack(side=tk.LEFT)

        self.pie_month_var = tk.StringVar()
        self.pie_month_menu = tk.OptionMenu(pie_controls, self.pie_month_var, "")
        self.pie_month_menu.pack(side=tk.LEFT, padx=6)
        self.pie_month_var.trace_add("write", self._on_chart_filter_change)

        daily_frame = tk.LabelFrame(parent, text="Income/expense by day of month")
        daily_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        monthly_frame = tk.LabelFrame(parent, text="Income/expense by months of year")
        monthly_frame.grid(
            row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10
        )

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        self.expense_pie_canvas = tk.Canvas(
            pie_frame, height=240, bg="white", highlightthickness=0
        )
        self.expense_pie_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 6))

        legend_container = tk.Frame(pie_frame)
        legend_container.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.expense_legend_canvas = tk.Canvas(
            legend_container, height=110, highlightthickness=0
        )
        self.expense_legend_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        legend_scroll = tk.Scrollbar(
            legend_container,
            orient="vertical",
            command=self.expense_legend_canvas.yview,
        )
        legend_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.expense_legend_canvas.configure(yscrollcommand=legend_scroll.set)

        self.expense_legend_frame = tk.Frame(self.expense_legend_canvas)
        self.expense_legend_canvas.create_window(
            (0, 0), window=self.expense_legend_frame, anchor="nw"
        )

        def _update_legend_scroll(_event=None):
            self.expense_legend_canvas.configure(
                scrollregion=self.expense_legend_canvas.bbox("all")
            )

        self.expense_legend_frame.bind("<Configure>", _update_legend_scroll)
        self.expense_legend_canvas.bind("<MouseWheel>", self._on_legend_mousewheel)
        self.expense_legend_frame.bind("<MouseWheel>", self._on_legend_mousewheel)

        self.bind_all("<MouseWheel>", self._on_legend_mousewheel)

        daily_controls = tk.Frame(daily_frame)
        daily_controls.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(daily_controls, text="Month:").pack(side=tk.LEFT)

        self.chart_month_var = tk.StringVar()
        self.chart_month_menu = tk.OptionMenu(daily_controls, self.chart_month_var, "")
        self.chart_month_menu.pack(side=tk.LEFT, padx=6)
        self.chart_month_var.trace_add("write", self._on_chart_filter_change)

        self.daily_bar_canvas = tk.Canvas(
            daily_frame, height=220, bg="white", highlightthickness=0
        )
        self.daily_bar_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        monthly_controls = tk.Frame(monthly_frame)
        monthly_controls.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(monthly_controls, text="Year:").pack(side=tk.LEFT)

        self.chart_year_var = tk.StringVar()
        self.chart_year_menu = tk.OptionMenu(monthly_controls, self.chart_year_var, "")
        self.chart_year_menu.pack(side=tk.LEFT, padx=6)
        self.chart_year_var.trace_add("write", self._on_chart_filter_change)

        self.monthly_bar_canvas = tk.Canvas(
            monthly_frame, height=220, bg="white", highlightthickness=0
        )
        self.monthly_bar_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._chart_refresh_suspended = False
        self._chart_redraw_job = None

        def _schedule_redraw(_event=None):
            if self._chart_redraw_job is not None:
                try:
                    self.after_cancel(self._chart_redraw_job)
                except Exception:
                    pass
            self._chart_redraw_job = self.after(120, self._refresh_charts)

        self.expense_pie_canvas.bind("<Configure>", _schedule_redraw)
        self.daily_bar_canvas.bind("<Configure>", _schedule_redraw)
        self.monthly_bar_canvas.bind("<Configure>", _schedule_redraw)

    def operations_tab(self, parent: Union[tk.Frame, ttk.Frame]) -> None:
        parent.grid_columnconfigure(1, weight=1)

        # Left: Add record form
        form_frame = tk.LabelFrame(parent, text="Add operation")
        form_frame.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)

        tk.Label(form_frame, text="Type:").grid(
            row=0, column=0, sticky="w", padx=6, pady=4
        )
        type_var = tk.StringVar(value="Income")
        tk.OptionMenu(form_frame, type_var, "Income", "Expense").grid(
            row=0, column=1, padx=6, pady=4
        )

        tk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(
            row=1, column=0, sticky="w", padx=6, pady=4
        )
        date_entry = tk.Entry(form_frame)
        date_entry.grid(row=1, column=1, padx=6, pady=4)

        tk.Label(form_frame, text="Amount:").grid(
            row=2, column=0, sticky="w", padx=6, pady=4
        )
        amount_entry = tk.Entry(form_frame)
        amount_entry.grid(row=2, column=1, padx=6, pady=4)

        tk.Label(form_frame, text="Currency:").grid(
            row=3, column=0, sticky="w", padx=6, pady=4
        )
        currency_entry = tk.Entry(form_frame)
        currency_entry.insert(0, "KZT")
        currency_entry.grid(row=3, column=1, padx=6, pady=4)

        tk.Label(form_frame, text="Category:").grid(
            row=4, column=0, sticky="w", padx=6, pady=4
        )
        category_entry = tk.Entry(form_frame)
        category_entry.insert(0, "General")
        category_entry.grid(row=4, column=1, padx=6, pady=4)

        def save_record():
            date_str = date_entry.get().strip()
            if not date_str:
                messagebox.showerror("Error", "Date is required.")
                return
            try:
                from domain.validation import parse_ymd, ensure_not_future

                entered_date = parse_ymd(date_str)
                ensure_not_future(entered_date)
            except ValueError as e:
                messagebox.showerror(
                    "Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD."
                )
                return

            amount_str = amount_entry.get().strip()
            if not amount_str:
                messagebox.showerror("Error", "Amount is required.")
                return
            try:
                amount = float(amount_str)
            except ValueError:
                messagebox.showerror("Error", "Invalid amount.")
                return

            currency = (currency_entry.get() or "KZT").strip()
            category = (category_entry.get() or "General").strip()

            try:
                use_class = (
                    CreateIncome if type_var.get() == "Income" else CreateExpense
                )
                use_case = use_class(self.repository, self.currency)
                use_case.execute(
                    date=date_str, amount=amount, currency=currency, category=category
                )
                if type_var.get() == "Income":
                    messagebox.showinfo("Success", "Income record added.")
                else:  # Expense
                    messagebox.showinfo("Success", "Expense record added.")
                date_entry.delete(0, tk.END)
                amount_entry.delete(0, tk.END)
                category_entry.delete(0, tk.END)
                self._refresh_list()
                self._refresh_charts()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add record: {str(e)}")

        save_btn = tk.Button(form_frame, text="Save", command=save_record)
        save_btn.grid(row=5, column=0, columnspan=2, pady=8)

        # Right: Records list
        list_frame = tk.LabelFrame(parent, text="List of operations")
        list_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.records_listbox = Listbox(list_frame)
        self.records_listbox.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        scrollbar = Scrollbar(
            list_frame, orient=VERTICAL, command=self.records_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns", pady=6)
        self.records_listbox.config(yscrollcommand=scrollbar.set)

        def delete_selected():
            selection = self.records_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a record to delete.")
                return
            index = selection[0]
            delete_use_case = DeleteRecord(self.repository)
            if delete_use_case.execute(index):
                messagebox.showinfo("Success", f"Deleted record at index {index}.")
                self._refresh_list()
                self._refresh_charts()
            else:
                messagebox.showerror("Error", "Failed to delete record.")

        def delete_all():
            confirm = messagebox.askyesno(
                "Confirm Delete All",
                "Are you sure you want to delete ALL records? This action cannot be undone.",
            )
            if confirm:
                DeleteAllRecords(self.repository).execute()
                messagebox.showinfo("Success", "All records have been deleted.")
                self._refresh_list()
                self._refresh_charts()

        def import_records_data():
            mode_label = import_mode_var.get()
            policy = self._import_policy_from_ui(mode_label)
            fmt = import_format_var.get()
            cfg = IMPORT_FORMATS.get(fmt)
            if not cfg:
                messagebox.showerror("Error", f"Unsupported import format: {fmt}")
                return

            filepath = filedialog.askopenfilename(
                defaultextension=cfg["ext"],
                filetypes=[(f"{fmt} files", f"*{cfg['ext']}"), ("All files", "*.*")],
                title=f"Select {cfg['desc']} file to import",
            )
            if not filepath:
                return

            if policy == ImportPolicy.CURRENT_RATE:
                messagebox.showwarning(
                    "Current Rate Import",
                    "For CURRENT_RATE mode, exchange rates will be fixed at import time.",
                )

            if not messagebox.askyesno(
                "Confirm Import",
                f"Are you sure you want to import from file '{filepath}'? This will replace all existing records.",
            ):
                return

            try:
                imported_count, skipped_count, errors = self._import_record_by_format(
                    fmt, filepath, policy
                )
                details = ""
                if skipped_count:
                    details = (
                        f"\nSkipped: {skipped_count} rows."
                        f"\nFirst errors:\n- " + "\n- ".join(errors[:5])
                    )
                messagebox.showinfo(
                    "Success",
                    f"Successfully imported {imported_count} records from {cfg['desc']} file.\nAll existing records have been replaced."
                    + details,
                )
                self._refresh_list()
                self._refresh_charts()

            except FileNotFoundError:
                logger.exception(f"{cfg['desc']} import file not found: %s", filepath)
                messagebox.showerror("Error", f"File not found: {filepath}")
            except Exception as e:
                logger.exception(f"Failed to import {cfg['desc']} from %s", filepath)
                messagebox.showerror(
                    "Error", f"Failed to import {cfg['desc']}: {str(e)}"
                )

        def export_records_data():
            fmt = import_format_var.get()
            cfg = IMPORT_FORMATS.get(fmt)
            if not cfg or fmt == "JSON":
                messagebox.showerror("Error", "Unsupported export format for records.")
                return
            records = self.repository.load_all()
            filepath = filedialog.asksaveasfilename(
                defaultextension=cfg["ext"],
                filetypes=[
                    (f"{cfg['desc']} files", f"*{cfg['ext']}"),
                    ("All files", "*.*"),
                ],
                title=f"Save records as {cfg['desc']}",
            )
            if not filepath:
                return
            try:
                from gui.exporters import export_records

                export_records(
                    records,
                    filepath,
                    fmt.lower(),
                    initial_balance=self.repository.load_initial_balance(),
                )
                messagebox.showinfo("Success", f"Records exported to {filepath}")
                open_in_file_manager(os.path.dirname(filepath))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export records: {str(e)}")

        btn_frame = tk.Frame(list_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=6)

        tk.Button(btn_frame, text="Delete Selected", command=delete_selected).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btn_frame, text="Delete All", command=delete_all).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btn_frame, text="Refresh", command=self._refresh_list).pack(
            side=tk.LEFT, padx=6
        )

        # Import controls (reuse existing import handler)
        import_mode_var = tk.StringVar(value="Import Records (Current Rate)")
        tk.OptionMenu(
            btn_frame,
            import_mode_var,
            "Full Backup",
            "Import Records (Current Rate)",
            "Legacy Import",
        ).pack(side=tk.LEFT, padx=6)
        import_format_var = tk.StringVar(value="CSV")
        tk.OptionMenu(btn_frame, import_format_var, "CSV", "XLSX").pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btn_frame, text="Import", command=import_records_data).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btn_frame, text="Export Data", command=export_records_data).pack(
            side=tk.LEFT, padx=6
        )

        # Initial refresh
        self._refresh_list()

    def reports_tab(self, parent: Union[tk.Frame, ttk.Frame]) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(parent)
        controls.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

        tk.Label(controls, text="Period (e.g., 2025-03):").grid(
            row=0, column=0, sticky="w"
        )
        period_entry = tk.Entry(controls)
        period_entry.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(controls, text="Category:").grid(row=1, column=0, sticky="w")
        category_entry = tk.Entry(controls)
        category_entry.grid(row=1, column=1, padx=6, pady=4)

        group_var = tk.BooleanVar()
        tk.Checkbutton(controls, text="Group by category", variable=group_var).grid(
            row=2, column=0, columnspan=2, sticky="w"
        )

        table_var = tk.BooleanVar()
        tk.Checkbutton(controls, text="Display as table", variable=table_var).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        result_frame = tk.Frame(parent)
        result_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=6)
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        result_text = tk.Text(result_frame, wrap="word")
        result_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = Scrollbar(result_frame, orient=VERTICAL, command=result_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        result_text.config(yscrollcommand=scrollbar.set)

        current_report: Dict[str, Optional[Report]] = {"report": None}
        report_mode_var = tk.StringVar(value="fixed")

        tk.Label(controls, text="Totals mode:").grid(
            row=0, column=2, sticky="w", padx=(12, 0)
        )
        ttk.Radiobutton(
            controls,
            text="On fixed rate",
            variable=report_mode_var,
            value="fixed",
        ).grid(row=1, column=2, sticky="w", padx=(12, 0))
        ttk.Radiobutton(
            controls,
            text="On current rate",
            variable=report_mode_var,
            value="current",
        ).grid(row=2, column=2, sticky="w", padx=(12, 0))

        def generate():
            report = GenerateReport(self.repository).execute()
            period = period_entry.get().strip()
            if period:
                try:
                    report = report.filter_by_period(period)
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
                    return
            cat = category_entry.get().strip()
            if cat:
                report = report.filter_by_category(cat)

            current_report["report"] = report

            result_text.delete(1.0, tk.END)
            summary_year = None
            summary_up_to_month = None
            if period:
                try:
                    parts = period.split("-")
                    if parts and parts[0].isdigit():
                        summary_year = int(parts[0])
                    if len(parts) > 1 and parts[1].isdigit():
                        summary_up_to_month = int(parts[1])
                except Exception:
                    summary_year = None
                    summary_up_to_month = None

            if group_var.get():
                if table_var.get():
                    groups = report.grouped_by_category()
                    for cat, cat_report in groups.items():
                        result_text.insert(tk.END, f"\nCategory: {cat}\n")
                        result_text.insert(
                            tk.END,
                            cat_report.as_table(summary_mode="total_only") + "\n",
                        )
                else:
                    groups = report.grouped_by_category()
                    for cat, cat_report in groups.items():
                        if report_mode_var.get() == "current":
                            total = cat_report.total_current(self.currency)
                        else:
                            total = cat_report.total_fixed()
                        result_text.insert(tk.END, f"{cat}: {total:.2f} KZT\n")
            elif table_var.get():
                result_text.insert(tk.END, report.as_table())
            else:
                balance_value = report.initial_balance
                balance_label = (
                    "Opening balance" if report.is_opening_balance else "Initial balance"
                )
                records_total_fixed = sum(
                    r.signed_amount_kzt() for r in report.records()
                )
                final_balance_fixed = report.total_fixed()
                final_balance_current = report.total_current(self.currency)
                fx_diff = report.fx_difference(self.currency)
                result_text.insert(
                    tk.END, f"{balance_label}: {balance_value:.2f} KZT\n"
                )
                if report_mode_var.get() == "current":
                    result_text.insert(
                        tk.END,
                        f"Records Total (fixed): {records_total_fixed:.2f} KZT\n",
                    )
                    result_text.insert(
                        tk.END,
                        f"Final Balance (current rate): {final_balance_current:.2f} KZT\n",
                    )
                else:
                    result_text.insert(
                        tk.END,
                        f"Records Total (fixed): {records_total_fixed:.2f} KZT\n",
                    )
                    result_text.insert(
                        tk.END,
                        f"Final Balance (operation rate): {final_balance_fixed:.2f} KZT\n",
                    )
                result_text.insert(tk.END, f"FX Difference: {fx_diff:.2f} KZT\n")

            summary_table = report.monthly_income_expense_table(
                year=summary_year, up_to_month=summary_up_to_month
            )
            result_text.insert(
                tk.END, "\n\nMonthly Income/Expense Summary (Past & Current Months)\n"
            )
            result_text.insert(tk.END, summary_table + "\n")

        generate_btn = tk.Button(controls, text="Generate", command=generate)
        generate_btn.grid(row=4, column=0, pady=8)

        export_format_var = tk.StringVar(value="CSV")
        tk.OptionMenu(controls, export_format_var, "CSV", "XLSX", "PDF").grid(
            row=4, column=1, padx=6
        )

        def export_any():
            report = current_report.get("report")
            if report is None:
                messagebox.showerror("Error", "Please generate a report first.")
                return
            fmt = export_format_var.get()
            filepath = filedialog.asksaveasfilename(
                defaultextension=f".{fmt.lower()}", title="Save Report"
            )
            if not filepath:
                return
            try:
                from gui.exporters import export_report

                export_report(report, filepath, fmt.lower())
                messagebox.showinfo("Success", f"Report exported to {filepath}")
                open_in_file_manager(os.path.dirname(filepath))
            except Exception as e:
                logger.exception("Failed to export report")
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

        tk.Button(controls, text="Export", command=export_any).grid(
            row=4, column=2, padx=6
        )

    def settings_tab(self, parent: Union[tk.Frame, ttk.Frame]) -> None:
        parent.grid_columnconfigure(1, weight=1)

        # Initial balance panel
        balance_frame = tk.LabelFrame(parent, text="Initial balance")
        balance_frame.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
        current_balance = self.repository.load_initial_balance()
        tk.Label(balance_frame, text=f"Current: {current_balance:.2f} KZT").grid(
            row=0, column=0, sticky="w", padx=6, pady=4
        )
        balance_entry = tk.Entry(balance_frame)
        balance_entry.insert(0, str(current_balance))
        balance_entry.grid(row=1, column=0, padx=6, pady=4)

        def save_balance():
            try:
                balance = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid balance amount.")
                return
            self.repository.save_initial_balance(balance)
            messagebox.showinfo("Success", f"Initial balance set to {balance:.2f} KZT.")
            self._refresh_charts()

        tk.Button(balance_frame, text="Save", command=save_balance).grid(
            row=2, column=0, pady=6
        )

        # Mandatory expenses management
        mand_frame = tk.LabelFrame(parent, text="Mandatory expenses")
        mand_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        mand_frame.grid_rowconfigure(0, weight=1)
        mand_frame.grid_columnconfigure(0, weight=1)

        mand_listbox = Listbox(mand_frame)
        mand_listbox.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        mand_scroll = Scrollbar(mand_frame, orient=VERTICAL, command=mand_listbox.yview)
        mand_scroll.grid(row=0, column=1, sticky="ns", pady=6)
        mand_listbox.config(yscrollcommand=mand_scroll.set)

        def refresh_mandatory():
            mand_listbox.delete(0, tk.END)
            expenses = GetMandatoryExpenses(self.repository).execute()
            for i, expense in enumerate(expenses):
                mand_listbox.insert(
                    tk.END,
                    (
                        f"[{i}] {expense.amount_original:.2f} {expense.currency} "
                        f"(={expense.amount_kzt:.2f} KZT) - {expense.category} - "
                        f"{expense.description} ({expense.period})"
                    ),
                )

        current_panel: Dict[str, Optional[tk.Frame]] = {"add": None, "report": None}

        def add_mandatory_inline():
            # Close the previous panel if it is open
            if current_panel["add"] is not None:
                try:
                    current_panel["add"].destroy()
                except Exception:
                    pass
            if current_panel["report"] is not None:
                try:
                    current_panel["report"].destroy()
                except Exception:
                    pass

            add_panel = tk.Frame(mand_frame)
            add_panel.grid(row=2, column=0, columnspan=2, pady=6, sticky="ew")
            current_panel["add"] = add_panel

            tk.Label(add_panel, text="Amount:").grid(row=0, column=0, sticky="w")
            amt = tk.Entry(add_panel)
            amt.grid(row=0, column=1)

            tk.Label(add_panel, text="Currency (default KZT):").grid(
                row=1, column=0, sticky="w"
            )
            currency_entry = tk.Entry(add_panel)
            currency_entry.insert(0, "KZT")
            currency_entry.grid(row=1, column=1)

            tk.Label(add_panel, text="Category (default Mandatory):").grid(
                row=2, column=0, sticky="w"
            )
            category_entry = tk.Entry(add_panel)
            category_entry.insert(0, "Mandatory")
            category_entry.grid(row=2, column=1)

            tk.Label(add_panel, text="Description:").grid(row=3, column=0, sticky="w")
            desc = tk.Entry(add_panel)
            desc.grid(row=3, column=1)

            tk.Label(add_panel, text="Period:").grid(row=4, column=0, sticky="w")
            period_var = tk.StringVar(value="monthly")
            tk.OptionMenu(
                add_panel, period_var, "daily", "weekly", "monthly", "yearly"
            ).grid(row=4, column=1)

            def save():
                try:
                    amount = float(amt.get())
                    description = desc.get()
                    period = period_var.get()
                    if not description:
                        messagebox.showerror("Error", "Description is required.")
                        return
                    CreateMandatoryExpense(self.repository, self.currency).execute(
                        amount=amount,
                        currency=(currency_entry.get() or "KZT").strip(),
                        category=(category_entry.get() or "Mandatory").strip(),
                        description=description,
                        period=period,
                    )
                    messagebox.showinfo("Success", "Mandatory expense added.")
                    add_panel.destroy()
                    current_panel["add"] = None
                    self._refresh_charts()
                    refresh_mandatory()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add expense: {str(e)}")

            def cancel():
                try:
                    add_panel.destroy()
                    current_panel["add"] = None
                except Exception:
                    pass

            tk.Button(add_panel, text="Save", command=save).grid(
                row=5, column=0, padx=6
            )
            tk.Button(add_panel, text="Cancel", command=cancel).grid(
                row=5, column=1, padx=6
            )

        def add_to_report_inline():
            # Close the previous panel if it is open
            if current_panel["add"] is not None:
                try:
                    current_panel["add"].destroy()
                except Exception:
                    pass
            if current_panel["report"] is not None:
                try:
                    current_panel["report"].destroy()
                except Exception:
                    pass

            add_to_report_panel = tk.Frame(mand_frame)
            add_to_report_panel.grid(row=2, column=0, columnspan=2, pady=6, sticky="ew")
            current_panel["report"] = add_to_report_panel

            tk.Label(add_to_report_panel, text="Date (YYYY-MM-DD):").grid(
                row=0, column=0, sticky="w"
            )
            date_entry = tk.Entry(add_to_report_panel)
            date_entry.grid(row=0, column=1)

            selection = mand_listbox.curselection()
            index = selection[0] if selection else -1

            def save():
                try:
                    from domain.validation import parse_ymd, ensure_not_future

                    date = date_entry.get()
                    entered_date = parse_ymd(date)
                    ensure_not_future(entered_date)

                    add_to_report_use_case = AddMandatoryExpenseToReport(
                        self.repository, self.currency
                    )
                    if add_to_report_use_case.execute(index, date):
                        messagebox.showinfo(
                            "Success", f"Mandatory expense added to report for {date}."
                        )
                        add_to_report_panel.destroy()
                        current_panel["report"] = None
                        refresh_mandatory()
                        self._refresh_list()
                        self._refresh_charts()

                    else:
                        messagebox.showerror(
                            "Error",
                            "Please select a mandatory expense to add to report. \nThen click 'Add to Report' and try again.",
                        )
                except ValueError as e:
                    messagebox.showerror(
                        "Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD."
                    )

            def cancel():
                try:
                    add_to_report_panel.destroy()
                    current_panel["report"] = None
                except Exception:
                    pass

            tk.Button(add_to_report_panel, text="Save", command=save).grid(
                row=1, column=0, padx=6
            )
            tk.Button(add_to_report_panel, text="Cancel", command=cancel).grid(
                row=1, column=1, padx=6
            )

        def delete_mandatory():
            sel = mand_listbox.curselection()
            if not sel:
                messagebox.showerror("Error", "Please select an expense to delete.")
                return
            idx = sel[0]
            if DeleteMandatoryExpense(self.repository).execute(idx):
                messagebox.showinfo("Success", "Mandatory expense deleted.")
                refresh_mandatory()
            else:
                messagebox.showerror("Error", "Failed to delete expense.")

        def delete_all_mandatory():
            confirm = messagebox.askyesno("Confirm", "Delete all mandatory expenses?")
            if confirm:
                DeleteAllMandatoryExpenses(self.repository).execute()
                messagebox.showinfo("Success", "All mandatory expenses deleted.")
                refresh_mandatory()
            else:
                messagebox.showerror(
                    "Error", "Failed to delete all mandatory expenses."
                )

        btns = tk.Frame(mand_frame)
        btns.grid(row=1, column=0, columnspan=2, pady=6)

        def import_mand():
            fmt = format_var.get()
            cfg = IMPORT_FORMATS.get(fmt)
            if not cfg:
                messagebox.showerror("Error", f"Unsupported format: {fmt}")
                return

            filepath = filedialog.askopenfilename(
                defaultextension=cfg["ext"],
                filetypes=[
                    (f"{cfg['desc']} files", f"*{cfg['ext']}"),
                    ("All files", "*.*"),
                ],
                title=f"Select {cfg['desc']} file to import mandatory expenses",
            )
            if not filepath:
                return

            if not messagebox.askyesno(
                "Confirm Import",
                f"This will replace all existing mandatory expenses with data from:\n"
                f"{filepath}\n\nContinue?",
            ):
                return

            try:
                imported_count, skipped_count, errors = (
                    self._import_mandatory_by_format(fmt, filepath)
                )
                details = ""
                if skipped_count:
                    details = (
                        f"\nSkipped: {skipped_count} rows."
                        f"\nFirst errors:\n- " + "\n- ".join(errors[:5])
                    )

                messagebox.showinfo(
                    "Success",
                    f"Successfully imported {imported_count} mandatory expenses from "
                    f"{cfg['desc']} file.\nAll existing mandatory expenses have been replaced."
                    + details,
                )
                refresh_mandatory()
                self._refresh_charts()

            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import {fmt}: {str(e)}")

        def export_mand():
            fmt = format_var.get()
            expenses = GetMandatoryExpenses(self.repository).execute()
            if not expenses:
                messagebox.showinfo("No Expenses", "No mandatory expenses to export.")
                return
            filepath = filedialog.asksaveasfilename(
                defaultextension=f".{fmt.lower()}", title="Save Mandatory Expenses"
            )
            if not filepath:
                return
            try:
                from gui.exporters import export_mandatory_expenses

                export_mandatory_expenses(expenses, filepath, fmt.lower())
                messagebox.showinfo(
                    "Success", f"Mandatory expenses exported to {filepath}"
                )
                open_in_file_manager(os.path.dirname(filepath))
            except Exception as e:
                logger.exception("Failed to export mandatory expenses")
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

        tk.Button(btns, text="Add", command=add_mandatory_inline).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btns, text="Delete", command=delete_mandatory).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btns, text="Delete All", command=delete_all_mandatory).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btns, text="Add to Report", command=add_to_report_inline).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btns, text="Refresh", command=refresh_mandatory).pack(
            side=tk.LEFT, padx=6
        )
        format_var = tk.StringVar(value="CSV")
        tk.OptionMenu(btns, format_var, "CSV", "XLSX").pack(side=tk.LEFT, padx=6)

        tk.Button(btns, text="Import", command=import_mand).pack(side=tk.LEFT, padx=6)
        tk.Button(btns, text="Export", command=export_mand).pack(side=tk.LEFT, padx=6)

        backup_frame = tk.LabelFrame(parent, text="Backup (JSON)")
        backup_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        def import_backup():
            filepath = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Full Backup",
            )
            if not filepath:
                return
            if not messagebox.askyesno(
                "Confirm Backup Import",
                "This will replace all records, mandatory expenses and initial balance. Continue?",
            ):
                return
            try:
                imported, skipped, errors = self._import_record_by_format(
                    "JSON", filepath, ImportPolicy.FULL_BACKUP
                )
                details = ""
                if skipped:
                    details = f"\nSkipped: {skipped}\n- " + "\n- ".join(errors[:5])
                messagebox.showinfo(
                    "Success",
                    f"Backup imported. Imported entities: {imported}.{details}",
                )
                balance_entry.delete(0, tk.END)
                balance_entry.insert(0, str(current_balance))
                refresh_mandatory()
                self._refresh_list()
                self._refresh_charts()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import backup: {str(e)}")

        def export_backup():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Full Backup",
            )
            if not filepath:
                return
            try:
                from gui.exporters import export_full_backup

                export_full_backup(
                    filepath,
                    initial_balance=self.repository.load_initial_balance(),
                    records=self.repository.load_all(),
                    mandatory_expenses=self.repository.load_mandatory_expenses(),
                )
                messagebox.showinfo("Success", f"Full backup exported to {filepath}")
                open_in_file_manager(os.path.dirname(filepath))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export backup: {str(e)}")

        tk.Button(backup_frame, text="Export Full Backup", command=export_backup).pack(
            side=tk.LEFT, padx=6, pady=6
        )
        tk.Button(backup_frame, text="Import Full Backup", command=import_backup).pack(
            side=tk.LEFT, padx=6, pady=6
        )

        # Initial refresh
        refresh_mandatory()

    def _import_policy_from_ui(self, mode_label: str) -> ImportPolicy:
        if mode_label == "Full Backup":
            return ImportPolicy.FULL_BACKUP
        if mode_label == "Legacy Import":
            return ImportPolicy.LEGACY
        return ImportPolicy.CURRENT_RATE

    def _import_record_by_format(
        self, fmt: str, filepath: str, policy: ImportPolicy
    ) -> tuple[int, int, list[str]]:
        self.repository.delete_all()

        if fmt == "CSV":
            from gui.importers import import_records_from_csv

            records, initial_balance, summary = import_records_from_csv(
                filepath, policy=policy, currency_service=self.currency
            )
        elif fmt == "XLSX":
            from gui.importers import import_records_from_xlsx

            records, initial_balance, summary = import_records_from_xlsx(
                filepath, policy=policy, currency_service=self.currency
            )
        elif fmt == "JSON":
            from gui.importers import import_full_backup

            # Full backup import replaces both records and mandatory expenses.
            DeleteAllMandatoryExpenses(self.repository).execute()
            (
                initial_balance,
                records,
                mandatory_expenses,
                summary,
            ) = import_full_backup(filepath)
            for expense in mandatory_expenses:
                self.repository.save_mandatory_expense(expense)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        self.repository.save_initial_balance(initial_balance)
        for record in records:
            self.repository.save(record)
        imported, skipped, errors = summary
        return imported, skipped, errors

    def _import_mandatory_by_format(
        self, fmt: str, filepath: str
    ) -> tuple[int, int, list[str]]:
        if fmt == "CSV":
            from gui.importers import import_mandatory_expenses_from_csv

            expenses, summary = import_mandatory_expenses_from_csv(
                filepath,
                policy=ImportPolicy.FULL_BACKUP,
                currency_service=self.currency,
            )

        elif fmt == "XLSX":
            from gui.importers import import_mandatory_expenses_from_xlsx

            expenses, summary = import_mandatory_expenses_from_xlsx(
                filepath,
                policy=ImportPolicy.FULL_BACKUP,
                currency_service=self.currency,
            )

        else:
            raise ValueError(f"Unsupported format: {fmt}")

        # Delete all existing mandatory expenses
        DeleteAllMandatoryExpenses(self.repository).execute()

        create_use_case = CreateMandatoryExpense(self.repository, self.currency)

        for expense in expenses:
            create_use_case.execute(
                amount=expense.amount_original,
                currency=expense.currency,
                category=expense.category,
                description=expense.description,
                period=expense.period,
            )

        imported, skipped, errors = summary
        return imported, skipped, errors

    def _refresh_list(self):
        self.records_listbox.delete(0, tk.END)
        all_records = self.repository.load_all()
        for i, record in enumerate(all_records):
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
            self.records_listbox.insert(
                tk.END,
                (
                    f"[{i}] {record.date} - {record_type} - {record.category} - "
                    f"{record.amount_original:.2f} {record.currency} "
                    f"(={record.amount_kzt:.2f} KZT)"
                ),
            )

    def _refresh_charts(self) -> None:
        records = self.repository.load_all()

        self._chart_refresh_suspended = True
        self._update_month_options(records)
        self._update_pie_month_options(records)
        self._update_year_options(records)
        self._chart_refresh_suspended = False

        self._draw_expense_pie(records)
        self._draw_daily_bars(records)
        self._draw_monthly_bars(records)

    def _on_chart_filter_change(self, *_args) -> None:
        if self._chart_refresh_suspended:
            return
        self._refresh_charts()

    def _update_month_options(self, records) -> None:
        months = extract_months(records)
        current_month = datetime.now().strftime("%Y-%m")
        if current_month not in months:
            months.append(current_month)
        months = sorted(set(months))

        menu = self.chart_month_menu["menu"]
        menu.delete(0, "end")
        for month in months:
            menu.add_command(
                label=month, command=lambda value=month: self.chart_month_var.set(value)
            )
        if not self.chart_month_var.get() or self.chart_month_var.get() not in months:
            self.chart_month_var.set(months[-1])

    def _update_pie_month_options(self, records) -> None:
        months = extract_months(records)
        current_month = datetime.now().strftime("%Y-%m")
        if current_month not in months:
            months.append(current_month)
        months = sorted(set(months))

        menu = self.pie_month_menu["menu"]
        menu.delete(0, "end")
        menu.add_command(
            label="Все время", command=lambda value="all": self.pie_month_var.set(value)
        )
        for month in months:
            menu.add_command(
                label=month, command=lambda value=month: self.pie_month_var.set(value)
            )

        current_value = self.pie_month_var.get()
        if not current_value:
            self.pie_month_var.set("all")
            return
        if current_value != "all" and current_value not in months:
            self.pie_month_var.set(months[-1] if months else "all")

    def _update_year_options(self, records) -> None:
        years = extract_years(records)
        current_year = datetime.now().year
        if current_year not in years:
            years.append(current_year)
        years = sorted(set(years))

        menu = self.chart_year_menu["menu"]
        menu.delete(0, "end")
        for year in years:
            menu.add_command(
                label=str(year),
                command=lambda value=year: self.chart_year_var.set(str(value)),
            )
        if not self.chart_year_var.get() or int(self.chart_year_var.get()) not in years:
            self.chart_year_var.set(str(years[-1]))

    def _draw_expense_pie(self, records) -> None:
        month_value = self.pie_month_var.get()
        filtered = records
        if month_value and month_value != "all":
            filtered = self._filter_records_by_month(records, month_value)
        totals = aggregate_expenses_by_category(filtered)
        data = [(k, v) for k, v in totals.items() if v > 0]
        data.sort(key=lambda item: item[1], reverse=True)
        data = self._group_minor_categories(data, max_slices=10)

        self.expense_pie_canvas.delete("all")
        for child in self.expense_legend_frame.winfo_children():
            child.destroy()

        if not data:
            self.expense_pie_canvas.create_text(
                10,
                10,
                anchor="nw",
                text="No data to display",
                fill="#6b7280",
                font=("Segoe UI", 11),
            )
            return

        width = max(self.expense_pie_canvas.winfo_width(), 240)
        height = max(self.expense_pie_canvas.winfo_height(), 240)
        size = min(width, height) - 30
        x0 = (width - size) / 2
        y0 = (height - size) / 2
        x1 = x0 + size
        y1 = y0 + size

        colors = self._generate_colors(len(data))

        total = sum(value for _, value in data)
        start = 0
        for index, (category, value) in enumerate(data):
            extent = (value / total) * 360
            color = colors[index % len(colors)]
            self.expense_pie_canvas.create_arc(
                x0, y0, x1, y1, start=start, extent=extent, fill=color, outline="white"
            )
            start += extent

            legend_row = tk.Frame(self.expense_legend_frame)
            legend_row.pack(anchor="w", pady=2)
            color_box = tk.Canvas(legend_row, width=12, height=12, highlightthickness=0)
            color_box.create_rectangle(0, 0, 12, 12, fill=color, outline=color)
            color_box.pack(side=tk.LEFT)
            tk.Label(
                legend_row,
                text=f"{category}: {value:.2f} KZT",
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=6)

    def _group_minor_categories(self, data, max_slices: int) -> list[tuple[str, float]]:
        if len(data) <= max_slices:
            return data

        major = data[: max_slices - 1]
        other_total = sum(value for _, value in data[max_slices - 1 :])
        major.append(("Other", other_total))
        return major

    def _filter_records_by_month(self, records, month_value: str):
        try:
            year, month = map(int, month_value.split("-"))
        except Exception:
            return records

        filtered = []
        for record in records:
            try:
                dt = datetime.strptime(record.date, "%Y-%m-%d")
            except Exception:
                continue
            if dt.year == year and dt.month == month:
                filtered.append(record)
        return filtered

    def _generate_colors(self, count: int) -> list[str]:
        if count <= 0:
            return []

        base_palette = [
            "#4f46e5",
            "#06b6d4",
            "#f59e0b",
            "#10b981",
            "#ec4899",
            "#8b5cf6",
            "#14b8a6",
            "#ef4444",
            "#f97316",
            "#22c55e",
            "#0ea5e9",
            "#a855f7",
        ]

        if count <= len(base_palette):
            return base_palette[:count]

        colors = list(base_palette)
        remaining = count - len(colors)
        for i in range(remaining):
            hue = (i * 360 / max(1, remaining)) % 360
            saturation = 70
            lightness = 50
            colors.append(f"#{self._hsl_to_hex(hue, saturation, lightness)}")
        return colors

    def _hsl_to_hex(self, hue: float, saturation: float, lightness: float) -> str:
        saturation /= 100
        lightness /= 100

        c = (1 - abs(2 * lightness - 1)) * saturation
        x = c * (1 - abs((hue / 60) % 2 - 1))
        m = lightness - c / 2

        if 0 <= hue < 60:
            r, g, b = c, x, 0
        elif 60 <= hue < 120:
            r, g, b = x, c, 0
        elif 120 <= hue < 180:
            r, g, b = 0, c, x
        elif 180 <= hue < 240:
            r, g, b = 0, x, c
        elif 240 <= hue < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        r = int((r + m) * 255)
        g = int((g + m) * 255)
        b = int((b + m) * 255)
        return f"{r:02x}{g:02x}{b:02x}"

    def _draw_daily_bars(self, records) -> None:
        month_value = self.chart_month_var.get()
        if not month_value:
            return
        year, month = map(int, month_value.split("-"))
        income, expense = aggregate_daily_cashflow(records, year, month)
        labels = [str(i + 1) for i in range(len(income))]
        self._draw_bar_chart(
            self.daily_bar_canvas, labels, income, expense, max_labels=8
        )

    def _draw_monthly_bars(self, records) -> None:
        year_value = self.chart_year_var.get()
        if not year_value:
            return
        year = int(year_value)
        income, expense = aggregate_monthly_cashflow(records, year)
        labels = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        self._draw_bar_chart(self.monthly_bar_canvas, labels, income, expense, 12)

    def _on_legend_mousewheel(self, event) -> None:
        if not hasattr(self, "expense_legend_canvas"):
            return

        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if widget == self.expense_legend_canvas:
                delta = -1 if event.delta > 0 else 1
                self.expense_legend_canvas.yview_scroll(delta, "units")
                return
            widget = widget.master

    def _draw_bar_chart(
        self,
        canvas: tk.Canvas,
        labels,
        income_values,
        expense_values,
        max_labels: int,
    ) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 220)

        max_income = max(income_values) if income_values else 0
        max_expense = max(expense_values) if expense_values else 0
        max_value = max(max_income, max_expense)

        if max_value <= 0:
            canvas.create_text(
                10,
                10,
                anchor="nw",
                text="No data to display",
                fill="#6b7280",
                font=("Segoe UI", 11),
            )
            return

        padding = {"left": 40, "right": 20, "top": 20, "bottom": 30}
        chart_w = width - padding["left"] - padding["right"]
        chart_h = height - padding["top"] - padding["bottom"]
        zero_y = padding["top"] + chart_h / 2
        scale = (chart_h / 2 - 10) / max_value

        canvas.create_line(
            padding["left"], zero_y, padding["left"] + chart_w, zero_y, fill="#d1d5db"
        )

        group_width = chart_w / max(1, len(labels))
        bar_width = max(6, min(18, group_width * 0.35))

        for idx, label in enumerate(labels):
            x_center = padding["left"] + group_width * idx + group_width / 2
            income_h = income_values[idx] * scale
            expense_h = expense_values[idx] * scale

            canvas.create_rectangle(
                x_center - bar_width - 2,
                zero_y - income_h,
                x_center - 2,
                zero_y,
                fill="#10b981",
                outline="",
            )
            canvas.create_rectangle(
                x_center + 2,
                zero_y,
                x_center + bar_width + 2,
                zero_y + expense_h,
                fill="#ef4444",
                outline="",
            )

            label_step = max(1, len(labels) // max_labels)
            if idx % label_step == 0 or len(labels) <= max_labels:
                canvas.create_text(
                    x_center,
                    padding["top"] + chart_h + 10,
                    text=label,
                    fill="#6b7280",
                    font=("Segoe UI", 9),
                )

        canvas.create_text(
            padding["left"],
            padding["top"] - 6,
            text="Incomes",
            fill="#10b981",
            anchor="sw",
            font=("Segoe UI", 9),
        )
        canvas.create_text(
            padding["left"] + 60,
            padding["top"] - 6,
            text="Expenses",
            fill="#ef4444",
            anchor="sw",
            font=("Segoe UI", 9),
        )


def main() -> None:
    try:
        app = FinancialApp()
        app.mainloop()
    except KeyboardInterrupt:
        messagebox.showinfo("Info", "Application closed by user.")
