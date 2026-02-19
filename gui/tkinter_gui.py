import logging
import os
import sys
import tkinter as tk
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from tkinter import (
    VERTICAL,
    Listbox,
    Scrollbar,
    filedialog,
    messagebox,
    ttk,
)
from typing import Any

from app.services import CurrencyService
from domain.import_policy import ImportPolicy
from domain.reports import Report
from gui.controllers import FinancialController
from gui.helpers import open_in_file_manager
from infrastructure.repositories import JsonFileRecordRepository
from utils.charting import (
    aggregate_daily_cashflow,
    aggregate_expenses_by_category,
    aggregate_monthly_cashflow,
    extract_months,
    extract_years,
)

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
        self.controller = FinancialController(self.repository, self.currency)
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._busy = False
        self._list_index_to_record_id: dict[int, str] = {}
        self._record_id_to_repo_index: dict[str, int] = {}

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

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.progress.pack_forget()

        # Initial data refresh
        self._refresh_charts()

    def destroy(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        super().destroy()

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        try:
            self.attributes("-disabled", busy)
        except Exception:
            pass
        if busy:
            self.progress.pack(fill=tk.X, padx=8, pady=(0, 8))
            self.progress.start(12)
            self.title(f"Financial Accounting - {message}" if message else "Financial Accounting")
            self.config(cursor="watch")
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.title("Financial Accounting")
            self.config(cursor="")

    def _run_background(
        self,
        task: Callable[[], Any],
        *,
        on_success: Callable[[Any], None],
        on_error: Callable[[BaseException], None] | None = None,
        busy_message: str = "Processing...",
    ) -> None:
        if self._busy:
            messagebox.showinfo("Please wait", "Operation is already running.")
            return
        self._set_busy(True, busy_message)
        future: Future[Any] = self._executor.submit(task)

        def _poll() -> None:
            if not future.done():
                self.after(100, _poll)
                return
            self._set_busy(False)
            error = future.exception()
            if error is not None:
                if on_error is not None:
                    on_error(error)
                else:
                    logger.exception("Background operation failed", exc_info=error)
                    messagebox.showerror("Error", str(error))
                return
            on_success(future.result())

        self.after(100, _poll)

    def infographics_tab(self, parent: tk.Frame | ttk.Frame) -> None:
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
        monthly_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        self.expense_pie_canvas = tk.Canvas(pie_frame, height=240, bg="white", highlightthickness=0)
        self.expense_pie_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 6))

        legend_container = tk.Frame(pie_frame)
        legend_container.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.expense_legend_canvas = tk.Canvas(legend_container, height=110, highlightthickness=0)
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

        self.daily_bar_canvas = tk.Canvas(daily_frame, height=220, bg="white", highlightthickness=0)
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

    def operations_tab(self, parent: tk.Frame | ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=0)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # -------------------------
        # LEFT COLUMN CONTAINER
        # -------------------------
        left_frame = tk.Frame(parent)
        left_frame.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)

        # -------------------------
        # Add operation
        # -------------------------
        form_frame = tk.LabelFrame(left_frame, text="Add operation")
        form_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        form_frame.grid_columnconfigure(1, weight=1)

        tk.Label(form_frame, text="Type:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        type_var = tk.StringVar(value="Income")
        tk.OptionMenu(form_frame, type_var, "Income", "Expense").grid(
            row=0, column=1, sticky="ew", padx=6, pady=4
        )

        tk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(
            row=1, column=0, sticky="w", padx=6, pady=4
        )
        date_entry = tk.Entry(form_frame)
        date_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        tk.Label(form_frame, text="Amount:").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        amount_entry = tk.Entry(form_frame)
        amount_entry.grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        tk.Label(form_frame, text="Currency:").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        currency_entry = tk.Entry(form_frame)
        currency_entry.insert(0, "KZT")
        currency_entry.grid(row=3, column=1, sticky="ew", padx=6, pady=4)

        tk.Label(form_frame, text="Category:").grid(row=4, column=0, sticky="w", padx=6, pady=4)
        category_entry = tk.Entry(form_frame)
        category_entry.insert(0, "General")
        category_entry.grid(row=4, column=1, sticky="ew", padx=6, pady=4)

        tk.Label(form_frame, text="Wallet:").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        operation_wallet_var = tk.StringVar(value="")
        operation_wallet_menu = tk.OptionMenu(form_frame, operation_wallet_var, "")
        operation_wallet_menu.grid(row=5, column=1, sticky="ew", padx=6, pady=4)
        operation_wallet_map: dict[str, int] = {}

        def _refresh_operation_wallet_menu() -> None:
            nonlocal operation_wallet_map
            wallets = self.controller.load_active_wallets()
            operation_wallet_map = {
                f"[{wallet.id}] {wallet.name} ({wallet.currency})": wallet.id for wallet in wallets
            }
            labels = list(operation_wallet_map.keys()) or [""]
            menu = operation_wallet_menu["menu"]
            menu.delete(0, "end")
            for label in labels:
                menu.add_command(
                    label=label,
                    command=lambda value=label: operation_wallet_var.set(value),
                )
            if operation_wallet_var.get() not in operation_wallet_map:
                operation_wallet_var.set(labels[0])

        _refresh_operation_wallet_menu()

        def save_record():
            date_str = date_entry.get().strip()
            if not date_str:
                messagebox.showerror("Error", "Date is required.")
                return
            try:
                from domain.validation import ensure_not_future, parse_ymd

                entered_date = parse_ymd(date_str)
                ensure_not_future(entered_date)
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD.")
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
            wallet_label = operation_wallet_var.get()
            wallet_id = operation_wallet_map.get(wallet_label)
            if wallet_id is None:
                messagebox.showerror("Error", "Wallet is required.")
                return

            try:
                if type_var.get() == "Income":
                    self.controller.create_income(
                        date=date_str,
                        wallet_id=wallet_id,
                        amount=amount,
                        currency=currency,
                        category=category,
                    )
                else:
                    self.controller.create_expense(
                        date=date_str,
                        wallet_id=wallet_id,
                        amount=amount,
                        currency=currency,
                        category=category,
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
                _refresh_operation_wallet_menu()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add record: {str(e)}")

        tk.Button(form_frame, text="Save", command=save_record).grid(
            row=6, column=0, columnspan=2, pady=8
        )

        # -------------------------
        # Transfer (now separate)
        # -------------------------
        transfer_frame = tk.LabelFrame(left_frame, text="Transfer")
        transfer_frame.grid(row=1, column=0, sticky="ew")
        transfer_frame.grid_columnconfigure(1, weight=1)

        tk.Label(transfer_frame, text="From wallet:").grid(
            row=0, column=0, sticky="w", padx=4, pady=2
        )
        transfer_from_var = tk.StringVar(value="")
        transfer_from_menu = tk.OptionMenu(transfer_frame, transfer_from_var, "")
        transfer_from_menu.grid(row=0, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(transfer_frame, text="To wallet:").grid(
            row=1, column=0, sticky="w", padx=4, pady=2
        )
        transfer_to_var = tk.StringVar(value="")
        transfer_to_menu = tk.OptionMenu(transfer_frame, transfer_to_var, "")
        transfer_to_menu.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(transfer_frame, text="Date:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        transfer_date_entry = tk.Entry(transfer_frame)
        transfer_date_entry.grid(row=2, column=1, sticky="ew", padx=4, pady=2)
        transfer_date_entry.insert(0, date.today().isoformat())

        tk.Label(transfer_frame, text="Amount:").grid(row=3, column=0, sticky="w", padx=4, pady=2)
        transfer_amount_entry = tk.Entry(transfer_frame)
        transfer_amount_entry.grid(row=3, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(transfer_frame, text="Currency:").grid(row=4, column=0, sticky="w", padx=4, pady=2)
        transfer_currency_entry = tk.Entry(transfer_frame)
        transfer_currency_entry.insert(0, "KZT")
        transfer_currency_entry.grid(row=4, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(transfer_frame, text="Commission:").grid(
            row=5, column=0, sticky="w", padx=4, pady=2
        )
        transfer_commission_entry = tk.Entry(transfer_frame)
        transfer_commission_entry.insert(0, "0")
        transfer_commission_entry.grid(row=5, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(transfer_frame, text="Commission currency:").grid(
            row=6, column=0, sticky="w", padx=4, pady=2
        )
        transfer_commission_currency_entry = tk.Entry(transfer_frame)
        transfer_commission_currency_entry.insert(0, "KZT")
        transfer_commission_currency_entry.grid(row=6, column=1, sticky="ew", padx=4, pady=2)

        tk.Label(transfer_frame, text="Description:").grid(
            row=7, column=0, sticky="w", padx=4, pady=2
        )
        transfer_description_entry = tk.Entry(transfer_frame)
        transfer_description_entry.grid(row=7, column=1, sticky="ew", padx=4, pady=2)

        wallet_id_map: dict[str, int] = {}

        def _refresh_transfer_wallet_menus() -> None:
            nonlocal wallet_id_map
            wallets = self.controller.load_active_wallets()
            wallet_id_map = {
                f"[{wallet.id}] {wallet.name} ({wallet.currency})": wallet.id for wallet in wallets
            }
            labels = list(wallet_id_map.keys()) or [""]

            for menu_widget, var in (
                (transfer_from_menu, transfer_from_var),
                (transfer_to_menu, transfer_to_var),
            ):
                menu = menu_widget["menu"]
                menu.delete(0, "end")
                for label in labels:
                    menu.add_command(label=label, command=lambda value=label, v=var: v.set(value))
                if not var.get() or var.get() not in wallet_id_map:
                    var.set(labels[0])
            if len(labels) > 1 and transfer_to_var.get() == transfer_from_var.get():
                transfer_to_var.set(labels[1])

        def create_transfer() -> None:
            from_label = transfer_from_var.get()
            to_label = transfer_to_var.get()
            from_wallet_id = wallet_id_map.get(from_label)
            to_wallet_id = wallet_id_map.get(to_label)
            if from_wallet_id is None or to_wallet_id is None:
                messagebox.showerror("Error", "Please select source and destination wallets.")
                return

            date_str = transfer_date_entry.get().strip()
            if not date_str:
                messagebox.showerror("Error", "Transfer date is required.")
                return
            try:
                from domain.validation import ensure_not_future, parse_ymd

                entered_date = parse_ymd(date_str)
                ensure_not_future(entered_date)
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD.")
                return

            amount_str = transfer_amount_entry.get().strip()
            if not amount_str:
                messagebox.showerror("Error", "Transfer amount is required.")
                return

            try:
                transfer_amount = float(amount_str)
                commission_amount = float((transfer_commission_entry.get() or "0").strip())
            except ValueError:
                messagebox.showerror("Error", "Transfer amount/commission must be numeric.")
                return

            try:
                transfer_id = self.controller.create_transfer(
                    from_wallet_id=from_wallet_id,
                    to_wallet_id=to_wallet_id,
                    transfer_date=date_str,
                    amount=transfer_amount,
                    currency=(transfer_currency_entry.get() or "KZT").strip(),
                    description=transfer_description_entry.get().strip(),
                    commission_amount=commission_amount,
                    commission_currency=(transfer_commission_currency_entry.get() or "").strip(),
                )
                messagebox.showinfo("Success", f"Transfer created (id={transfer_id}).")
                transfer_amount_entry.delete(0, tk.END)
                transfer_description_entry.delete(0, tk.END)
                transfer_commission_entry.delete(0, tk.END)
                transfer_commission_entry.insert(0, "0")
                self._refresh_list()
                self._refresh_charts()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create transfer: {str(e)}")

        tk.Button(transfer_frame, text="Create transfer", command=create_transfer).grid(
            row=8, column=0, columnspan=2, pady=6
        )
        self._refresh_transfer_wallet_menus = _refresh_transfer_wallet_menus
        self._refresh_operation_wallet_menu = _refresh_operation_wallet_menu
        _refresh_transfer_wallet_menus()

        # Right: Records list
        list_frame = tk.LabelFrame(parent, text="List of operations")
        list_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.records_listbox = Listbox(list_frame)
        self.records_listbox.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        scrollbar = Scrollbar(list_frame, orient=VERTICAL, command=self.records_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=6)
        self.records_listbox.config(yscrollcommand=scrollbar.set)

        def delete_selected():
            selection = self.records_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a record to delete.")
                return
            list_index = selection[0]
            record_id = self._list_index_to_record_id.get(list_index)
            repository_index = self._record_id_to_repo_index.get(record_id) if record_id else None
            if repository_index is None:
                messagebox.showerror("Error", "Selected record is no longer available.")
                self._refresh_list()
                return
            if self.controller.delete_record(repository_index):
                messagebox.showinfo("Success", f"Deleted record at index {repository_index}.")
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
                self.controller.delete_all_records()
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
                f"Are you sure you want to import from file '{filepath}'?"
                "\nThis will replace all existing records.",
            ):
                return

            def _task() -> tuple[int, int, list[str]]:
                return self.controller.import_records(fmt, filepath, policy)

            def _on_success(result: tuple[int, int, list[str]]) -> None:
                imported_count, skipped_count, errors = result
                details = ""
                if skipped_count:
                    details = f"\nSkipped: {skipped_count} rows.\nFirst errors:\n- " + "\n- ".join(
                        errors[:5]
                    )
                messagebox.showinfo(
                    "Success",
                    f"Successfully imported {imported_count} records from {cfg['desc']} file."
                    "\nAll existing records have been replaced." + details,
                )
                self._refresh_list()
                self._refresh_charts()

            def _on_error(exc: BaseException) -> None:
                if isinstance(exc, FileNotFoundError):
                    logger.error("%s import file not found: %s", cfg["desc"], filepath)
                    messagebox.showerror("Error", f"File not found: {filepath}")
                    return
                logger.error("Failed to import %s from %s: %s", cfg["desc"], filepath, exc)
                messagebox.showerror("Error", f"Failed to import {cfg['desc']}: {str(exc)}")

            self._run_background(
                _task,
                on_success=_on_success,
                on_error=_on_error,
                busy_message=f"Importing {cfg['desc']}...",
            )

        def export_records_data():
            fmt = import_format_var.get()
            cfg = IMPORT_FORMATS.get(fmt)
            if not cfg or fmt == "JSON":
                messagebox.showerror("Error", "Unsupported export format for records.")
                return
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
            records = self.repository.load_all()
            initial_balance = self.repository.load_initial_balance()

            def _task() -> None:
                from gui.exporters import export_records

                export_records(
                    records,
                    filepath,
                    fmt.lower(),
                    initial_balance=initial_balance,
                )

            def _on_success(_: Any) -> None:
                messagebox.showinfo("Success", f"Records exported to {filepath}")
                open_in_file_manager(os.path.dirname(filepath))

            self._run_background(
                _task,
                on_success=_on_success,
                busy_message=f"Exporting {cfg['desc']}...",
            )

        btn_frame = tk.Frame(list_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=6)

        tk.Button(btn_frame, text="Delete Selected", command=delete_selected).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(btn_frame, text="Delete All", command=delete_all).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Refresh", command=self._refresh_list).pack(side=tk.LEFT, padx=6)

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
        tk.OptionMenu(btn_frame, import_format_var, "CSV", "XLSX").pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Import", command=import_records_data).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Export Data", command=export_records_data).pack(
            side=tk.LEFT, padx=6
        )

        # Initial refresh
        self._refresh_list()

    def reports_tab(self, parent: tk.Frame | ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(parent)
        controls.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

        tk.Label(controls, text="Period (e.g., 2025-03):").grid(row=0, column=0, sticky="w")
        period_start_entry = tk.Entry(controls)
        period_start_entry.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(controls, text="Period end (e.g., 2025-03-31):").grid(row=1, column=0, sticky="w")
        period_end_entry = tk.Entry(controls)
        period_end_entry.grid(row=1, column=1, padx=6, pady=4)

        tk.Label(controls, text="Category:").grid(row=2, column=0, sticky="w")
        category_entry = tk.Entry(controls)
        category_entry.grid(row=2, column=1, padx=6, pady=4)

        tk.Label(controls, text="Wallet:").grid(row=3, column=0, sticky="w")
        report_wallet_var = tk.StringVar(value="All wallets")
        report_wallet_menu = tk.OptionMenu(controls, report_wallet_var, "All wallets")
        report_wallet_menu.grid(row=3, column=1, padx=6, pady=4, sticky="ew")

        wallet_label_to_id: dict[str, int | None] = {"All wallets": None}

        def _refresh_report_wallet_menu() -> None:
            nonlocal wallet_label_to_id
            wallet_label_to_id = {"All wallets": None}
            for wallet in self.controller.load_active_wallets():
                wallet_label_to_id[f"[{wallet.id}] {wallet.name} ({wallet.currency})"] = wallet.id
            labels = list(wallet_label_to_id.keys())
            menu = report_wallet_menu["menu"]
            menu.delete(0, "end")
            for label in labels:
                menu.add_command(
                    label=label, command=lambda value=label: report_wallet_var.set(value)
                )
            if report_wallet_var.get() not in wallet_label_to_id:
                report_wallet_var.set("All wallets")

        _refresh_report_wallet_menu()

        group_var = tk.BooleanVar()
        tk.Checkbutton(controls, text="Group by category", variable=group_var).grid(
            row=4, column=0, columnspan=2, sticky="w"
        )

        table_var = tk.BooleanVar()
        tk.Checkbutton(controls, text="Display as table", variable=table_var).grid(
            row=5, column=0, columnspan=2, sticky="w"
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

        current_report: dict[str, Report | None] = {"report": None}
        report_mode_var = tk.StringVar(value="fixed")

        tk.Label(controls, text="Totals mode:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Radiobutton(
            controls, text="On fixed rate", variable=report_mode_var, value="fixed"
        ).grid(row=1, column=2, sticky="w", padx=(12, 0))
        ttk.Radiobutton(
            controls, text="On current rate", variable=report_mode_var, value="current"
        ).grid(row=2, column=2, sticky="w", padx=(12, 0))

        def generate():
            _refresh_report_wallet_menu()
            selected_wallet = wallet_label_to_id.get(report_wallet_var.get(), None)
            report = self.controller.generate_report_for_wallet(selected_wallet)
            period_start = period_start_entry.get().strip()
            period_end = period_end_entry.get().strip()
            if period_start:
                try:
                    report = report.filter_by_period_range(
                        period_start, period_end or date.today().isoformat()
                    )
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
                    return
            elif period_end:
                messagebox.showerror(
                    "Error", "Period start is required when period end is provided."
                )
                return
            cat = category_entry.get().strip()
            if cat:
                report = report.filter_by_category(cat)

            current_report["report"] = report

            result_text.delete(1.0, tk.END)
            summary_year = None
            summary_up_to_month = None
            if period_start:
                try:
                    parts = period_start.split("-")
                    if parts and parts[0].isdigit():
                        summary_year = int(parts[0])
                    if len(parts) > 1 and parts[1].isdigit():
                        summary_up_to_month = int(parts[1])
                except Exception:
                    summary_year = None
                    summary_up_to_month = None

            result_text.insert(tk.END, report.statement_title + "\n\n")
            result_text.insert(
                tk.END,
                f"Net Worth (fixed): {self.controller.net_worth_fixed():.2f} KZT\n"
                f"Net Worth (current): {self.controller.net_worth_current():.2f} KZT\n\n",
            )

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
                records_total_fixed = report.net_profit_fixed()
                final_balance_fixed = report.total_fixed()
                final_balance_current = report.total_current(self.currency)
                fx_diff = report.fx_difference(self.currency)
                result_text.insert(tk.END, f"{balance_label}: {balance_value:.2f} KZT\n")
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
        generate_btn.grid(row=6, column=0, pady=8)

        export_format_var = tk.StringVar(value="CSV")
        tk.OptionMenu(controls, export_format_var, "CSV", "XLSX", "PDF").grid(
            row=6, column=1, padx=6
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

        tk.Button(controls, text="Export", command=export_any).grid(row=6, column=2, padx=6)

    def settings_tab(self, parent: tk.Frame | ttk.Frame) -> None:
        PAD_X = 8
        PAD_Y = 6

        # =========================================================
        # Root layout (2 columns: left / right)
        # =========================================================
        parent.grid_columnconfigure(0, weight=0)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        left_panel = ttk.Frame(parent)
        left_panel.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        right_panel = ttk.Frame(parent)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # =========================================================
        # INITIAL BALANCE
        # =========================================================
        balance_frame = tk.LabelFrame(left_panel, text="Initial balance")
        balance_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        current_balance = self.controller.get_system_initial_balance()

        tk.Label(balance_frame, text=f"Current: {current_balance:.2f} KZT").grid(
            row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y
        )

        balance_entry = tk.Entry(balance_frame)
        balance_entry.insert(0, str(current_balance))
        balance_entry.grid(row=1, column=0, sticky="ew", padx=PAD_X, pady=PAD_Y)

        def save_balance():
            try:
                balance = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid balance amount.")
                return
            self.controller.set_system_initial_balance(balance)
            messagebox.showinfo("Success", f"Initial balance set to {balance:.2f} KZT.")
            self._refresh_charts()

        tk.Button(balance_frame, text="Save", command=save_balance).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=PAD_X, pady=PAD_Y
        )

        # =========================================================
        # WALLETS
        # =========================================================
        wallets_frame = tk.LabelFrame(left_panel, text="Wallets")
        wallets_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        wallets_frame.grid_columnconfigure(0, weight=1)
        wallets_frame.grid_rowconfigure(1, weight=1)

        # ---- Wallet Form ----
        form = ttk.Frame(wallets_frame)
        form.grid(row=0, column=0, sticky="ew", padx=PAD_X, pady=PAD_Y)
        form.grid_columnconfigure(1, weight=1)

        tk.Label(form, text="Name:").grid(row=0, column=0, sticky="w")
        wallet_name_entry = tk.Entry(form)
        wallet_name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        tk.Label(form, text="Currency:").grid(row=1, column=0, sticky="w")
        wallet_currency_entry = tk.Entry(form, width=8)
        wallet_currency_entry.insert(0, "KZT")
        wallet_currency_entry.grid(row=1, column=1, sticky="ew", pady=2)

        tk.Label(form, text="Initial balance:").grid(row=2, column=0, sticky="w")
        wallet_initial_entry = tk.Entry(form)
        wallet_initial_entry.insert(0, "0")
        wallet_initial_entry.grid(row=2, column=1, sticky="ew", pady=2)

        wallet_allow_negative_var = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Allow negative", variable=wallet_allow_negative_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=2
        )

        def create_wallet() -> None:
            try:
                initial_balance = float(wallet_initial_entry.get().strip() or "0")
            except ValueError:
                messagebox.showerror("Error", "Invalid wallet initial balance.")
                return
            try:
                wallet = self.controller.create_wallet(
                    name=wallet_name_entry.get().strip(),
                    currency=(wallet_currency_entry.get() or "KZT").strip(),
                    initial_balance=initial_balance,
                    allow_negative=wallet_allow_negative_var.get(),
                )
                messagebox.showinfo("Success", f"Wallet created: [{wallet.id}] {wallet.name}")
                wallet_name_entry.delete(0, tk.END)
                wallet_initial_entry.delete(0, tk.END)
                wallet_initial_entry.insert(0, "0")
                refresh_wallets()
                self._refresh_charts()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create wallet: {str(e)}")

        tk.Button(form, text="Create wallet", command=create_wallet).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )

        # ---- Wallet List ----
        list_frame = ttk.Frame(wallets_frame)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=PAD_X)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        wallet_listbox = Listbox(list_frame, height=8)
        wallet_listbox.grid(row=0, column=0, sticky="nsew")

        wallet_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=wallet_listbox.yview)
        wallet_scroll.grid(row=0, column=1, sticky="ns")
        wallet_listbox.config(yscrollcommand=wallet_scroll.set)

        def refresh_wallets() -> None:
            wallet_listbox.delete(0, tk.END)
            for wallet in self.controller.load_wallets():
                try:
                    balance = self.controller.wallet_balance(wallet.id)
                except Exception:
                    balance = wallet.initial_balance
                wallet_listbox.insert(
                    tk.END,
                    f"[{wallet.id}] {wallet.name} | {wallet.currency} | "
                    f"Initial={wallet.initial_balance:.2f} | Balance={balance:.2f} | "
                    f"allow_negative={wallet.allow_negative} | active={wallet.is_active}",
                )
            if hasattr(self, "_refresh_transfer_wallet_menus"):
                try:
                    self._refresh_transfer_wallet_menus()
                except Exception:
                    pass
            if hasattr(self, "_refresh_operation_wallet_menu"):
                try:
                    self._refresh_operation_wallet_menu()
                except Exception:
                    pass

        def delete_wallet() -> None:
            selection = wallet_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Select wallet to delete.")
                return
            row = wallet_listbox.get(selection[0])
            try:
                wallet_id = int(row.split("]")[0].strip().lstrip("["))
            except Exception:
                messagebox.showerror("Error", "Failed to parse selected wallet id.")
                return
            try:
                self.controller.soft_delete_wallet(wallet_id)
                messagebox.showinfo("Success", "Wallet was soft-deleted.")
                refresh_wallets()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        wallet_actions = ttk.Frame(wallets_frame)
        wallet_actions.grid(row=2, column=0, sticky="ew", padx=PAD_X, pady=PAD_Y)
        wallet_actions.grid_columnconfigure(0, weight=1)
        wallet_actions.grid_columnconfigure(1, weight=1)
        tk.Button(wallet_actions, text="Delete wallet", command=delete_wallet).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        tk.Button(wallet_actions, text="Refresh", command=refresh_wallets).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

        refresh_wallets()

        # =========================================================
        # MANDATORY EXPENSES (RIGHT PANEL)
        # =========================================================
        mand_frame = tk.LabelFrame(right_panel, text="Mandatory expenses")
        mand_frame.grid(row=0, column=0, sticky="nsew")
        mand_frame.grid_rowconfigure(0, weight=1)
        mand_frame.grid_columnconfigure(0, weight=1)

        mand_listbox = tk.Listbox(mand_frame)
        mand_listbox.grid(row=0, column=0, sticky="nsew", padx=PAD_X, pady=PAD_Y)

        mand_scroll = ttk.Scrollbar(mand_frame, orient="vertical", command=mand_listbox.yview)
        mand_scroll.grid(row=0, column=1, sticky="ns", pady=PAD_Y)

        mand_listbox.config(yscrollcommand=mand_scroll.set)

        def refresh_mandatory():
            mand_listbox.delete(0, tk.END)
            expenses = self.controller.load_mandatory_expenses()
            for i, expense in enumerate(expenses):
                mand_listbox.insert(
                    tk.END,
                    (
                        f"[{i}] {expense.amount_original:.2f} {expense.currency} "
                        f"(={expense.amount_kzt:.2f} KZT) - {expense.category} - "
                        f"{expense.description} ({expense.period})"
                    ),
                )

        current_panel: dict[str, tk.Frame | None] = {"add": None, "report": None}

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

            tk.Label(add_panel, text="Currency (default KZT):").grid(row=1, column=0, sticky="w")
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
            tk.OptionMenu(add_panel, period_var, "daily", "weekly", "monthly", "yearly").grid(
                row=4, column=1
            )

            def save():
                try:
                    amount = float(amt.get())
                    description = desc.get()
                    period = period_var.get()
                    if not description:
                        messagebox.showerror("Error", "Description is required.")
                        return
                    self.controller.create_mandatory_expense(
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

            tk.Button(add_panel, text="Save", command=save).grid(row=5, column=0, padx=6)
            tk.Button(add_panel, text="Cancel", command=cancel).grid(row=5, column=1, padx=6)

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
                    from domain.validation import ensure_not_future, parse_ymd

                    date = date_entry.get()
                    entered_date = parse_ymd(date)
                    ensure_not_future(entered_date)

                    if self.controller.add_mandatory_to_report(index, date):
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
                            "Please select a mandatory expense to add to report."
                            "\nThen click 'Add to Report' and try again.",
                        )
                except ValueError as e:
                    messagebox.showerror("Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD.")

            def cancel():
                try:
                    add_to_report_panel.destroy()
                    current_panel["report"] = None
                except Exception:
                    pass

            tk.Button(add_to_report_panel, text="Save", command=save).grid(row=1, column=0, padx=6)
            tk.Button(add_to_report_panel, text="Cancel", command=cancel).grid(
                row=1, column=1, padx=6
            )

        def delete_mandatory():
            sel = mand_listbox.curselection()
            if not sel:
                messagebox.showerror("Error", "Please select an expense to delete.")
                return
            idx = sel[0]
            if self.controller.delete_mandatory_expense(idx):
                messagebox.showinfo("Success", "Mandatory expense deleted.")
                refresh_mandatory()
            else:
                messagebox.showerror("Error", "Failed to delete expense.")

        def delete_all_mandatory():
            confirm = messagebox.askyesno("Confirm", "Delete all mandatory expenses?")
            if confirm:
                self.controller.delete_all_mandatory_expenses()
                messagebox.showinfo("Success", "All mandatory expenses deleted.")
                refresh_mandatory()
            else:
                messagebox.showerror("Error", "Failed to delete all mandatory expenses.")

        # ---- Buttons row ----
        btns = ttk.Frame(mand_frame)
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", padx=PAD_X, pady=PAD_Y)
        for i in range(8):
            btns.grid_columnconfigure(i, weight=1)

        tk.Button(btns, text="Add", command=add_mandatory_inline).grid(row=0, column=0)
        tk.Button(btns, text="Delete", command=delete_mandatory).grid(row=0, column=1)
        tk.Button(btns, text="Delete All", command=delete_all_mandatory).grid(row=0, column=2)
        tk.Button(btns, text="Add to Report", command=add_to_report_inline).grid(row=0, column=3)
        tk.Button(btns, text="Refresh", command=refresh_mandatory).grid(row=0, column=4)
        format_var = tk.StringVar(value="CSV")
        tk.OptionMenu(btns, format_var, "CSV", "XLSX").grid(row=0, column=5)

        refresh_mandatory()

        # =========================================================
        # BACKUP
        # =========================================================
        backup_frame = tk.LabelFrame(left_panel, text="Backup (JSON)")
        backup_frame.grid(row=2, column=0, sticky="ew")

        backup_frame.grid_columnconfigure(0, weight=1)
        backup_frame.grid_columnconfigure(1, weight=1)

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

            def _task() -> tuple[int, int, list[str]]:
                return self.controller.import_mandatory(fmt, filepath)

            def _on_success(result: tuple[int, int, list[str]]) -> None:
                imported_count, skipped_count, errors = result
                details = ""
                if skipped_count:
                    details = f"\nSkipped: {skipped_count} rows.\nFirst errors:\n- " + "\n- ".join(
                        errors[:5]
                    )

                messagebox.showinfo(
                    "Success",
                    f"Successfully imported {imported_count} mandatory expenses from "
                    f"{cfg['desc']} file.\nAll existing mandatory expenses have been replaced."
                    + details,
                )
                refresh_mandatory()
                self._refresh_charts()

            def _on_error(exc: BaseException) -> None:
                if isinstance(exc, FileNotFoundError):
                    messagebox.showerror("Error", f"File not found: {filepath}")
                    return
                messagebox.showerror("Error", f"Failed to import {fmt}: {str(exc)}")

            self._run_background(
                _task,
                on_success=_on_success,
                on_error=_on_error,
                busy_message=f"Importing {cfg['desc']} mandatory expenses...",
            )

        def export_mand():
            fmt = format_var.get()
            expenses = self.controller.load_mandatory_expenses()
            if not expenses:
                messagebox.showinfo("No Expenses", "No mandatory expenses to export.")
                return
            filepath = filedialog.asksaveasfilename(
                defaultextension=f".{fmt.lower()}", title="Save Mandatory Expenses"
            )
            if not filepath:
                return

            def _task() -> None:
                from gui.exporters import export_mandatory_expenses

                export_mandatory_expenses(expenses, filepath, fmt.lower())

            def _on_success(_: Any) -> None:
                messagebox.showinfo("Success", f"Mandatory expenses exported to {filepath}")
                open_in_file_manager(os.path.dirname(filepath))

            self._run_background(
                _task,
                on_success=_on_success,
                busy_message=f"Exporting {fmt} mandatory expenses...",
            )

        tk.Button(btns, text="Import", command=import_mand).grid(row=0, column=6)
        tk.Button(btns, text="Export", command=export_mand).grid(row=0, column=7)

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

            def _task() -> tuple[int, int, list[str]]:
                return self.controller.import_records("JSON", filepath, ImportPolicy.FULL_BACKUP)

            def _on_success(result: tuple[int, int, list[str]]) -> None:
                imported, skipped, errors = result
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

            self._run_background(
                _task,
                on_success=_on_success,
                busy_message="Importing full backup...",
            )

        def export_backup():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Full Backup",
            )
            if not filepath:
                return
            initial_balance = self.repository.load_initial_balance()
            records = self.repository.load_all()
            mandatory_expenses = self.repository.load_mandatory_expenses()

            def _task() -> None:
                from gui.exporters import export_full_backup

                export_full_backup(
                    filepath,
                    initial_balance=initial_balance,
                    records=records,
                    mandatory_expenses=mandatory_expenses,
                )

            def _on_success(_: Any) -> None:
                messagebox.showinfo("Success", f"Full backup exported to {filepath}")
                open_in_file_manager(os.path.dirname(filepath))

            self._run_background(
                _task,
                on_success=_on_success,
                busy_message="Exporting full backup...",
            )

        tk.Button(backup_frame, text="Export Full Backup", command=export_backup).grid(
            row=0, column=0, sticky="ew", padx=PAD_X, pady=PAD_Y
        )

        tk.Button(backup_frame, text="Import Full Backup", command=import_backup).grid(
            row=0, column=1, sticky="ew", padx=PAD_X, pady=PAD_Y
        )

        # Initial refresh
        refresh_mandatory()

    def _import_policy_from_ui(self, mode_label: str) -> ImportPolicy:
        if mode_label == "Full Backup":
            return ImportPolicy.FULL_BACKUP
        if mode_label == "Legacy Import":
            return ImportPolicy.LEGACY
        return ImportPolicy.CURRENT_RATE

    def _refresh_list(self):
        self.records_listbox.delete(0, tk.END)
        self._list_index_to_record_id = {}
        self._record_id_to_repo_index = {}
        for list_index, item in enumerate(self.controller.build_record_list_items()):
            self._list_index_to_record_id[list_index] = item.record_id
            self._record_id_to_repo_index[item.record_id] = item.repository_index
            self.records_listbox.insert(tk.END, item.label)

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
            menu.add_command(label=month, command=lambda value=month: self.pie_month_var.set(value))

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
                if isinstance(record.date, date):
                    dt = datetime.combine(record.date, datetime.min.time())
                else:
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
        self._draw_bar_chart(self.daily_bar_canvas, labels, income, expense, max_labels=8)

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
