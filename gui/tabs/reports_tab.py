from __future__ import annotations

import os
import tkinter as tk
from datetime import date
from tkinter import VERTICAL, filedialog, messagebox, ttk
from typing import Any, Protocol

from domain.reports import Report
from gui.helpers import open_in_file_manager


class ReportsTabContext(Protocol):
    controller: Any
    currency: Any


def build_reports_tab(parent: tk.Frame | ttk.Frame, context: ReportsTabContext) -> None:
    parent.grid_rowconfigure(1, weight=1)
    parent.grid_columnconfigure(0, weight=1)

    controls = tk.Frame(parent)
    controls.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

    ttk.Label(controls, text="Period (e.g., 2025-03):").grid(row=0, column=0, sticky="w")
    period_start_entry = ttk.Entry(controls)
    period_start_entry.grid(row=0, column=1, padx=6, pady=4)

    ttk.Label(controls, text="Period end (e.g., 2025-03-31):").grid(row=1, column=0, sticky="w")
    period_end_entry = ttk.Entry(controls)
    period_end_entry.grid(row=1, column=1, padx=6, pady=4)

    ttk.Label(controls, text="Category:").grid(row=2, column=0, sticky="w")
    category_entry = ttk.Entry(controls)
    category_entry.grid(row=2, column=1, padx=6, pady=4)

    ttk.Label(controls, text="Wallet:").grid(row=3, column=0, sticky="w")
    report_wallet_var = tk.StringVar(value="All wallets")
    report_wallet_menu = ttk.OptionMenu(controls, report_wallet_var, "All wallets")
    report_wallet_menu.grid(row=3, column=1, padx=6, pady=4, sticky="ew")

    wallet_label_to_id: dict[str, int | None] = {"All wallets": None}

    def refresh_report_wallet_menu() -> None:
        nonlocal wallet_label_to_id
        wallet_label_to_id = {"All wallets": None}
        for wallet in context.controller.load_active_wallets():
            wallet_label_to_id[f"[{wallet.id}] {wallet.name} ({wallet.currency})"] = wallet.id
        labels = list(wallet_label_to_id.keys())
        menu = report_wallet_menu["menu"]
        menu.delete(0, "end")
        for label in labels:
            menu.add_command(label=label, command=lambda value=label: report_wallet_var.set(value))
        if report_wallet_var.get() not in wallet_label_to_id:
            report_wallet_var.set("All wallets")

    refresh_report_wallet_menu()

    group_var = tk.BooleanVar()
    ttk.Checkbutton(controls, text="Group by category", variable=group_var).grid(
        row=4, column=0, columnspan=2, sticky="w"
    )

    table_var = tk.BooleanVar()
    ttk.Checkbutton(controls, text="Display as table", variable=table_var).grid(
        row=5, column=0, columnspan=2, sticky="w"
    )

    result_frame = tk.Frame(parent)
    result_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=6)
    result_frame.grid_rowconfigure(0, weight=1)
    result_frame.grid_columnconfigure(0, weight=1)

    result_text = tk.Text(result_frame, wrap="word")
    result_text.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(result_frame, orient=VERTICAL, command=result_text.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    result_text.config(yscrollcommand=scrollbar.set)

    current_report: dict[str, Report | None] = {"report": None}
    report_mode_var = tk.StringVar(value="fixed")

    ttk.Label(controls, text="Totals mode:").grid(row=0, column=2, sticky="w", padx=(12, 0))
    ttk.Radiobutton(controls, text="On fixed rate", variable=report_mode_var, value="fixed").grid(
        row=1, column=2, sticky="w", padx=(12, 0)
    )
    ttk.Radiobutton(
        controls, text="On current rate", variable=report_mode_var, value="current"
    ).grid(row=2, column=2, sticky="w", padx=(12, 0))

    def generate() -> None:
        refresh_report_wallet_menu()
        selected_wallet = wallet_label_to_id.get(report_wallet_var.get(), None)
        report = context.controller.generate_report_for_wallet(selected_wallet)
        period_start = period_start_entry.get().strip()
        period_end = period_end_entry.get().strip()
        if period_start:
            try:
                report = report.filter_by_period_range(
                    period_start, period_end or date.today().isoformat()
                )
            except ValueError as error:
                messagebox.showerror("Error", str(error))
                return
        elif period_end:
            messagebox.showerror("Error", "Period start is required when period end is provided.")
            return

        category_value = category_entry.get().strip()
        if category_value:
            report = report.filter_by_category(category_value)

        current_report["report"] = report

        result_text.delete(1.0, tk.END)
        summary_year: int | None = None
        summary_up_to_month: int | None = None
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
            f"Net Worth (fixed): {context.controller.net_worth_fixed():.2f} KZT\n"
            f"Net Worth (current): {context.controller.net_worth_current():.2f} KZT\n\n",
        )

        if group_var.get():
            groups = report.grouped_by_category()
            if table_var.get():
                for cat, cat_report in groups.items():
                    result_text.insert(tk.END, f"\nCategory: {cat}\n")
                    result_text.insert(
                        tk.END, cat_report.as_table(summary_mode="total_only") + "\n"
                    )
            else:
                for cat, cat_report in groups.items():
                    if report_mode_var.get() == "current":
                        total = cat_report.total_current(context.currency)
                    else:
                        total = cat_report.total_fixed()
                    result_text.insert(tk.END, f"{cat}: {total:.2f} KZT\n")
        elif table_var.get():
            result_text.insert(tk.END, report.as_table())
        else:
            balance_value = report.initial_balance
            balance_label = "Opening balance" if report.is_opening_balance else "Initial balance"
            records_total_fixed = report.net_profit_fixed()
            final_balance_fixed = report.total_fixed()
            final_balance_current = report.total_current(context.currency)
            fx_diff = report.fx_difference(context.currency)
            result_text.insert(tk.END, f"{balance_label}: {balance_value:.2f} KZT\n")
            if report_mode_var.get() == "current":
                result_text.insert(
                    tk.END, f"Records Total (fixed): {records_total_fixed:.2f} KZT\n"
                )
                result_text.insert(
                    tk.END,
                    f"Final Balance (current rate): {final_balance_current:.2f} KZT\n",
                )
            else:
                result_text.insert(
                    tk.END, f"Records Total (fixed): {records_total_fixed:.2f} KZT\n"
                )
                result_text.insert(
                    tk.END,
                    f"Final Balance (operation rate): {final_balance_fixed:.2f} KZT\n",
                )
            result_text.insert(tk.END, f"FX Difference: {fx_diff:.2f} KZT\n")

        summary_table = report.monthly_income_expense_table(
            year=summary_year,
            up_to_month=summary_up_to_month,
        )
        result_text.insert(tk.END, "\n\nMonthly Income/Expense Summary (Past & Current Months)\n")
        result_text.insert(tk.END, summary_table + "\n")

    ttk.Button(controls, text="Generate", command=generate).grid(row=6, column=0, pady=8)

    export_format_var = tk.StringVar(value="CSV")
    ttk.OptionMenu(controls, export_format_var, "CSV", "CSV", "XLSX", "PDF").grid(
        row=6, column=1, padx=6
    )

    def export_any() -> None:
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
        except Exception as error:
            messagebox.showerror("Error", f"Failed to export: {str(error)}")

    ttk.Button(controls, text="Export", command=export_any).grid(row=6, column=2, padx=6)
