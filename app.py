import sys
import calendar
import tkinter as tk
from pathlib import Path
from tkinter import (
    messagebox,
    simpledialog,
    Toplevel,
    Listbox,
    Scrollbar,
    VERTICAL,
    filedialog,
)
import os

from infrastructure.repositories import JsonFileRecordRepository
from app.use_cases import (
    CreateIncome,
    CreateExpense,
    GenerateReport,
    DeleteRecord,
    DeleteAllRecords,
)
from domain.records import IncomeRecord
from app.services import CurrencyService

# Ensure project package root is on sys.path so imports work regardless of CWD
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class FinancialApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Financial Accounting")
        self.geometry("400x300")

        self.repository = JsonFileRecordRepository("Проект ФУ/project/records.json")
        self.currency = CurrencyService()

        # Buttons
        button_width = 15  # Set uniform width for all buttons

        self.add_income_btn = tk.Button(
            self, text="Add Income", command=self.add_income, width=button_width
        )
        self.add_income_btn.pack(pady=10)

        self.add_expense_btn = tk.Button(
            self, text="Add Expense", command=self.add_expense, width=button_width
        )
        self.add_expense_btn.pack(pady=10)

        self.report_btn = tk.Button(
            self,
            text="Generate Report",
            command=self.generate_report,
            width=button_width,
        )
        self.report_btn.pack(pady=10)

        self.delete_btn = tk.Button(
            self, text="Delete Record", command=self.delete_record, width=button_width
        )
        self.delete_btn.pack(pady=10)

        self.delete_all_btn = tk.Button(
            self,
            text="Delete All Records",
            command=self.delete_all_records,
            width=button_width,
        )
        self.delete_all_btn.pack(pady=10)

    def add_income(self):
        self._add_record("Income", CreateIncome)

    def add_expense(self):
        self._add_record("Expense", CreateExpense)

    def _add_record(self, record_type, use_case_class):
        date = simpledialog.askstring("Date", "Enter date (YYYY-MM-DD):", parent=self)
        if not date:
            return
        try:
            # Basic validation
            year, month, day = map(int, date.split("-"))
            if not (
                1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]
            ):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
            return

        amount_str = simpledialog.askstring("Amount", "Enter amount:", parent=self)
        if not amount_str:
            return
        try:
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid amount.")
            return

        currency = (
            simpledialog.askstring(
                "Currency", "Enter currency (default KZT):", parent=self
            )
            or "KZT"
        )
        category = (
            simpledialog.askstring(
                "Category", "Enter category (default General):", parent=self
            )
            or "General"
        )

        use_case = use_case_class(self.repository, self.currency)
        use_case.execute(date=date, amount=amount, currency=currency, category=category)
        messagebox.showinfo(
            "Success",
            f"Added {record_type.lower()}: {amount} {currency} on {date} (category: {category})",
        )

    def generate_report(self):
        report_window = Toplevel(self)
        report_window.title("Generate Report")
        report_window.geometry("600x400")

        current_report = None

        # Filters
        tk.Label(report_window, text="Period (e.g., 2025-03):").grid(
            row=0, column=0, sticky="w"
        )
        period_entry = tk.Entry(report_window)
        period_entry.grid(row=0, column=1)

        tk.Label(report_window, text="Category:").grid(row=1, column=0, sticky="w")
        category_entry = tk.Entry(report_window)
        category_entry.grid(row=1, column=1)

        group_var = tk.BooleanVar()
        tk.Checkbutton(
            report_window, text="Group by category", variable=group_var
        ).grid(row=2, column=0, columnspan=2)

        table_var = tk.BooleanVar()
        tk.Checkbutton(report_window, text="Display as table", variable=table_var).grid(
            row=3, column=0, columnspan=2
        )

        def generate():
            nonlocal current_report
            report = GenerateReport(self.repository).execute()
            period = period_entry.get().strip()
            if period:
                report = report.filter_by_period(period)
            cat = category_entry.get().strip()
            if cat:
                report = report.filter_by_category(cat)

            current_report = report  # Store the report

            result_text.delete(1.0, tk.END)
            if group_var.get():
                if table_var.get():
                    groups = report.grouped_by_category()
                    for cat, cat_report in groups.items():
                        result_text.insert(tk.END, f"\nCategory: {cat}\n")
                        result_text.insert(tk.END, cat_report.as_table() + "\n")
                else:
                    groups = report.grouped_by_category()
                    for cat, cat_report in groups.items():
                        total = cat_report.total()
                        result_text.insert(tk.END, f"{cat}: {total:.2f} KZT\n")
            elif table_var.get():
                result_text.insert(tk.END, report.as_table())
            else:
                total = report.total()
                result_text.insert(tk.END, f"Total: {total:.2f} KZT\n")

        def export_csv():
            nonlocal current_report
            if current_report is None:
                messagebox.showerror("Error", "Please generate a report first.")
                return
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save Report as CSV",
            )
            if filepath:
                try:
                    current_report.to_csv(filepath)
                    messagebox.showinfo("Success", f"Report exported to {filepath}")
                    # Open the folder containing the file
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export: {str(e)}")

        generate_btn = tk.Button(report_window, text="Generate", command=generate)
        generate_btn.grid(row=4, column=0, pady=10)

        export_btn = tk.Button(report_window, text="Export to CSV", command=export_csv)
        export_btn.grid(row=4, column=1, pady=10)

        result_text = tk.Text(report_window, wrap="word")
        scrollbar = Scrollbar(report_window, orient=VERTICAL, command=result_text.yview)
        result_text.config(yscrollcommand=scrollbar.set)
        result_text.grid(row=5, column=0, columnspan=2, sticky="nsew")
        scrollbar.grid(row=5, column=2, sticky="ns")

        report_window.grid_rowconfigure(5, weight=1)
        report_window.grid_columnconfigure(1, weight=1)

    def delete_record(self):
        all_records = self.repository.load_all()
        if not all_records:
            messagebox.showinfo("No Records", "No records to delete.")
            return

        delete_window = Toplevel(self)
        delete_window.title("Delete Record")
        delete_window.geometry("500x400")

        listbox = Listbox(delete_window)
        for i, record in enumerate(all_records):
            record_type = "Income" if isinstance(record, IncomeRecord) else "Expense"
            listbox.insert(
                tk.END,
                f"[{i}] {record.date} - {record_type} - {record.category} - {record.amount:.2f} KZT",
            )
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        def delete():
            selection = listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a record to delete.")
                return
            index = selection[0]
            delete_use_case = DeleteRecord(self.repository)
            if delete_use_case.execute(index):
                messagebox.showinfo("Success", f"Deleted record at index {index}.")
                delete_window.destroy()
                self.delete_record()  # Refresh list? But since window closes, maybe not necessary
            else:
                messagebox.showerror("Error", "Failed to delete record.")

        delete_btn = tk.Button(delete_window, text="Delete Selected", command=delete)
        delete_btn.pack(pady=10)

    def delete_all_records(self):
        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Delete All",
            "Are you sure you want to delete ALL records? This action cannot be undone.",
        )
        if confirm:
            delete_all_use_case = DeleteAllRecords(self.repository)
            delete_all_use_case.execute()
            messagebox.showinfo("Success", "All records have been deleted.")


def main() -> None:
    app = FinancialApp()
    app.mainloop()


if __name__ == "__main__":
    main()
