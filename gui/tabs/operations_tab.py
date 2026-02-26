from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from tkinter import VERTICAL, Listbox, filedialog, messagebox, ttk
from typing import Any, Protocol

from domain.import_policy import ImportPolicy
from gui.helpers import open_in_file_manager


class OperationsTabContext(Protocol):
    controller: Any
    repository: Any
    _list_index_to_record_id: dict[int, str]
    _record_id_to_repo_index: dict[str, int]

    def _refresh_list(self) -> None: ...

    def _refresh_charts(self) -> None: ...

    def _run_background(
        self,
        task: Callable[[], Any],
        *,
        on_success: Callable[[Any], None],
        on_error: Callable[[BaseException], None] | None = None,
        busy_message: str = "Processing...",
    ) -> None: ...

    def _import_policy_from_ui(self, mode_label: str) -> ImportPolicy: ...


@dataclass(slots=True)
class OperationsTabBindings:
    records_listbox: Listbox
    refresh_operation_wallet_menu: Callable[[], None]
    refresh_transfer_wallet_menus: Callable[[], None]


def build_operations_tab(
    parent: tk.Frame | ttk.Frame,
    context: OperationsTabContext,
    import_formats: dict[str, dict[str, str]],
) -> OperationsTabBindings:
    parent.grid_columnconfigure(0, weight=0)
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    left_frame = tk.Frame(parent)
    left_frame.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)

    form_frame = ttk.LabelFrame(left_frame, text="Add operation")
    form_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    form_frame.grid_columnconfigure(1, weight=1)

    ttk.Label(form_frame, text="Type:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
    type_var = tk.StringVar(value="Income")
    ttk.OptionMenu(form_frame, type_var, "Income", "Income", "Expense").grid(
        row=0, column=1, sticky="ew", padx=6, pady=4
    )

    ttk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(
        row=1, column=0, sticky="w", padx=6, pady=4
    )
    date_entry = ttk.Entry(form_frame)
    date_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=4)

    ttk.Label(form_frame, text="Amount:").grid(row=2, column=0, sticky="w", padx=6, pady=4)
    amount_entry = ttk.Entry(form_frame)
    amount_entry.grid(row=2, column=1, sticky="ew", padx=6, pady=4)

    ttk.Label(form_frame, text="Currency:").grid(row=3, column=0, sticky="w", padx=6, pady=4)
    currency_entry = ttk.Entry(form_frame)
    currency_entry.insert(0, "KZT")
    currency_entry.grid(row=3, column=1, sticky="ew", padx=6, pady=4)

    ttk.Label(form_frame, text="Category:").grid(row=4, column=0, sticky="w", padx=6, pady=4)
    category_entry = ttk.Entry(form_frame)
    category_entry.insert(0, "General")
    category_entry.grid(row=4, column=1, sticky="ew", padx=6, pady=4)

    ttk.Label(form_frame, text="Wallet:").grid(row=5, column=0, sticky="w", padx=6, pady=4)
    operation_wallet_var = tk.StringVar(value="")
    operation_wallet_menu = ttk.OptionMenu(form_frame, operation_wallet_var, "")
    operation_wallet_menu.grid(row=5, column=1, sticky="ew", padx=6, pady=4)
    operation_wallet_map: dict[str, int] = {}

    def refresh_operation_wallet_menu() -> None:
        nonlocal operation_wallet_map
        wallets = context.controller.load_active_wallets()
        operation_wallet_map = {
            f"[{wallet.id}] {wallet.name} ({wallet.currency})": wallet.id for wallet in wallets
        }
        labels = list(operation_wallet_map.keys()) or [""]
        menu = operation_wallet_menu["menu"]
        menu.delete(0, "end")
        for label in labels:
            menu.add_command(
                label=label, command=lambda value=label: operation_wallet_var.set(value)
            )
        if operation_wallet_var.get() not in operation_wallet_map:
            operation_wallet_var.set(labels[0])

    refresh_operation_wallet_menu()

    list_frame = ttk.LabelFrame(parent, text="List of operations")
    list_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    list_frame.grid_rowconfigure(0, weight=1)
    list_frame.grid_columnconfigure(0, weight=1)

    records_listbox = Listbox(list_frame)
    records_listbox.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

    scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=records_listbox.yview)
    scrollbar.grid(row=0, column=1, sticky="ns", pady=6)
    records_listbox.config(yscrollcommand=scrollbar.set)

    def save_record() -> None:
        date_str = date_entry.get().strip()
        if not date_str:
            messagebox.showerror("Error", "Date is required.")
            return
        try:
            from domain.validation import ensure_not_future, parse_ymd

            entered_date = parse_ymd(date_str)
            ensure_not_future(entered_date)
        except ValueError as error:
            messagebox.showerror("Error", f"Invalid date: {str(error)}. Use YYYY-MM-DD.")
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
        wallet_id = operation_wallet_map.get(operation_wallet_var.get())
        if wallet_id is None:
            messagebox.showerror("Error", "Wallet is required.")
            return

        try:
            if type_var.get() == "Income":
                context.controller.create_income(
                    date=date_str,
                    wallet_id=wallet_id,
                    amount=amount,
                    currency=currency,
                    category=category,
                )
                messagebox.showinfo("Success", "Income record added.")
            else:
                context.controller.create_expense(
                    date=date_str,
                    wallet_id=wallet_id,
                    amount=amount,
                    currency=currency,
                    category=category,
                )
                messagebox.showinfo("Success", "Expense record added.")

            date_entry.delete(0, tk.END)
            amount_entry.delete(0, tk.END)
            category_entry.delete(0, tk.END)
            context._refresh_list()
            context._refresh_charts()
            refresh_operation_wallet_menu()
        except Exception as error:
            messagebox.showerror("Error", f"Failed to add record: {str(error)}")

    ttk.Button(form_frame, text="Save", command=save_record).grid(
        row=6, column=0, columnspan=2, pady=8
    )

    def delete_selected() -> None:
        selection = records_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a record to delete.")
            return
        list_index = selection[0]
        record_id = context._list_index_to_record_id.get(list_index)
        repository_index = context._record_id_to_repo_index.get(record_id) if record_id else None
        if repository_index is None:
            messagebox.showerror("Error", "Selected record is no longer available.")
            context._refresh_list()
            return
        try:
            transfer_id = context.controller.transfer_id_by_repository_index(repository_index)
            if transfer_id is not None:
                context.controller.delete_transfer(transfer_id)
                messagebox.showinfo("Success", f"Deleted transfer #{transfer_id}.")
            elif context.controller.delete_record(repository_index):
                messagebox.showinfo("Success", f"Deleted record at index {repository_index}.")
            else:
                messagebox.showerror("Error", "Failed to delete record.")
                return
            context._refresh_list()
            context._refresh_charts()
        except Exception as error:
            messagebox.showerror("Error", f"Failed to delete: {str(error)}")

    def delete_all() -> None:
        confirm = messagebox.askyesno(
            "Confirm Delete All",
            "Are you sure you want to delete ALL records? This action cannot be undone.",
        )
        if confirm:
            context.controller.delete_all_records()
            messagebox.showinfo("Success", "All records have been deleted.")
            context._refresh_list()
            context._refresh_charts()

    wallet_id_map: dict[str, int] = {}

    transfer_frame = ttk.LabelFrame(left_frame, text="Transfer")
    transfer_frame.grid(row=1, column=0, sticky="ew")
    transfer_frame.grid_columnconfigure(1, weight=1)

    ttk.Label(transfer_frame, text="From wallet:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    transfer_from_var = tk.StringVar(value="")
    transfer_from_menu = ttk.OptionMenu(transfer_frame, transfer_from_var, "")
    transfer_from_menu.grid(row=0, column=1, sticky="ew", padx=4, pady=2)

    ttk.Label(transfer_frame, text="To wallet:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    transfer_to_var = tk.StringVar(value="")
    transfer_to_menu = ttk.OptionMenu(transfer_frame, transfer_to_var, "")
    transfer_to_menu.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

    ttk.Label(transfer_frame, text="Date:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    transfer_date_entry = ttk.Entry(transfer_frame)
    transfer_date_entry.grid(row=2, column=1, sticky="ew", padx=4, pady=2)
    transfer_date_entry.insert(0, date.today().isoformat())

    ttk.Label(transfer_frame, text="Amount:").grid(row=3, column=0, sticky="w", padx=4, pady=2)
    transfer_amount_entry = ttk.Entry(transfer_frame)
    transfer_amount_entry.grid(row=3, column=1, sticky="ew", padx=4, pady=2)

    ttk.Label(transfer_frame, text="Currency:").grid(row=4, column=0, sticky="w", padx=4, pady=2)
    transfer_currency_entry = ttk.Entry(transfer_frame)
    transfer_currency_entry.insert(0, "KZT")
    transfer_currency_entry.grid(row=4, column=1, sticky="ew", padx=4, pady=2)

    ttk.Label(transfer_frame, text="Commission:").grid(row=5, column=0, sticky="w", padx=4, pady=2)
    transfer_commission_entry = ttk.Entry(transfer_frame)
    transfer_commission_entry.insert(0, "0")
    transfer_commission_entry.grid(row=5, column=1, sticky="ew", padx=4, pady=2)

    ttk.Label(transfer_frame, text="Commission currency:").grid(
        row=6, column=0, sticky="w", padx=4, pady=2
    )
    transfer_commission_currency_entry = ttk.Entry(transfer_frame)
    transfer_commission_currency_entry.insert(0, "KZT")
    transfer_commission_currency_entry.grid(row=6, column=1, sticky="ew", padx=4, pady=2)

    ttk.Label(transfer_frame, text="Description:").grid(row=7, column=0, sticky="w", padx=4, pady=2)
    transfer_description_entry = ttk.Entry(transfer_frame)
    transfer_description_entry.grid(row=7, column=1, sticky="ew", padx=4, pady=2)

    def refresh_transfer_wallet_menus() -> None:
        nonlocal wallet_id_map
        wallets = context.controller.load_active_wallets()
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
        from_wallet_id = wallet_id_map.get(transfer_from_var.get())
        to_wallet_id = wallet_id_map.get(transfer_to_var.get())
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
        except ValueError as error:
            messagebox.showerror("Error", f"Invalid date: {str(error)}. Use YYYY-MM-DD.")
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
            transfer_id = context.controller.create_transfer(
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
            context._refresh_list()
            context._refresh_charts()
        except Exception as error:
            messagebox.showerror("Error", f"Failed to create transfer: {str(error)}")

    ttk.Button(transfer_frame, text="Create transfer", command=create_transfer).grid(
        row=8, column=0, columnspan=2, pady=6
    )
    refresh_transfer_wallet_menus()

    import_mode_var = tk.StringVar(value="Full Backup")
    import_format_var = tk.StringVar(value="CSV")

    def import_records_data() -> None:
        policy = context._import_policy_from_ui(import_mode_var.get())
        fmt = import_format_var.get()
        cfg = import_formats.get(fmt)
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

        def task() -> tuple[int, int, list[str]]:
            return context.controller.import_records(fmt, filepath, policy)

        def on_success(result: tuple[int, int, list[str]]) -> None:
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
            context._refresh_list()
            context._refresh_charts()

        def on_error(exc: BaseException) -> None:
            if isinstance(exc, FileNotFoundError):
                messagebox.showerror("Error", f"File not found: {filepath}")
                return
            messagebox.showerror("Error", f"Failed to import {cfg['desc']}: {str(exc)}")

        context._run_background(
            task,
            on_success=on_success,
            on_error=on_error,
            busy_message=f"Importing {cfg['desc']}...",
        )

    def export_records_data() -> None:
        fmt = import_format_var.get()
        cfg = import_formats.get(fmt)
        if not cfg or fmt == "JSON":
            messagebox.showerror("Error", "Unsupported export format for records.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=cfg["ext"],
            filetypes=[(f"{cfg['desc']} files", f"*{cfg['ext']}"), ("All files", "*.*")],
            title=f"Save records as {cfg['desc']}",
        )
        if not filepath:
            return

        records = context.repository.load_all()
        transfers = context.repository.load_transfers()

        def task() -> None:
            from gui.exporters import export_records

            export_records(records, filepath, fmt.lower(), transfers=transfers)

        def on_success(_: Any) -> None:
            messagebox.showinfo("Success", f"Records exported to {filepath}")
            open_in_file_manager(os.path.dirname(filepath))

        context._run_background(
            task,
            on_success=on_success,
            busy_message=f"Exporting {cfg['desc']}...",
        )

    btn_frame = tk.Frame(list_frame)
    btn_frame.grid(row=1, column=0, columnspan=2, pady=6)

    ttk.Button(btn_frame, text="Delete Selected", command=delete_selected).pack(
        side=tk.LEFT, padx=6
    )
    ttk.Button(btn_frame, text="Delete All", command=delete_all).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Refresh", command=context._refresh_list).pack(side=tk.LEFT, padx=6)

    ttk.OptionMenu(
        btn_frame,
        import_mode_var,
        "Full Backup",
        "Full Backup",
        "Current Rate",
        "Legacy Import",
    ).pack(side=tk.LEFT, padx=6)
    ttk.OptionMenu(btn_frame, import_format_var, "CSV", "CSV", "XLSX").pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Import", command=import_records_data).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Export Data", command=export_records_data).pack(
        side=tk.LEFT, padx=6
    )

    context._refresh_list()

    return OperationsTabBindings(
        records_listbox=records_listbox,
        refresh_operation_wallet_menu=refresh_operation_wallet_menu,
        refresh_transfer_wallet_menus=refresh_transfer_wallet_menus,
    )
