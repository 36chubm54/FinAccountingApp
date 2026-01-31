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
    ImportFromCSV,
    CreateMandatoryExpense,
    GetMandatoryExpenses,
    DeleteMandatoryExpense,
    DeleteAllMandatoryExpenses,
    AddMandatoryExpenseToReport,
)
from utils.csv_utils import (
    export_mandatory_expenses_to_csv,
    import_mandatory_expenses_from_csv,
)
from utils.excel_utils import (
    report_from_xlsx,
    report_to_xlsx,
    export_mandatory_expenses_to_xlsx,
    import_mandatory_expenses_from_xlsx,
)
from utils.pdf_utils import (
    report_from_pdf,
    report_to_pdf,
    export_mandatory_expenses_to_pdf,
    import_mandatory_expenses_from_pdf,
)
from domain.records import IncomeRecord, MandatoryExpenseRecord
from app.services import CurrencyService

# Ensure project package root is on sys.path so imports work regardless of CWD
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class FinancialApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Financial Accounting")
        self.geometry("300x450")

        # Track open windows so repeated button presses focus them instead of creating new ones
        self.report_window = None
        self.delete_window = None
        self.manage_window = None

        self.repository = JsonFileRecordRepository(
            str(Path(__file__).parent / "records.json")
        )
        self.currency = CurrencyService()

        # Buttons
        button_width = 15  # Set uniform width for all buttons
        padding = 10

        self.add_income_btn = tk.Button(
            self,
            text="Add Income",
            command=self.add_income,
            width=button_width,
        )
        self.add_income_btn.pack(pady=padding)

        self.add_expense_btn = tk.Button(
            self,
            text="Add Expense",
            command=self.add_expense,
            width=button_width,
        )
        self.add_expense_btn.pack(pady=padding)

        self.report_btn = tk.Button(
            self,
            text="Generate Report",
            command=self.generate_report,
            width=button_width,
        )
        self.report_btn.pack(pady=padding)

        self.delete_btn = tk.Button(
            self,
            text="Delete Record",
            command=self.delete_record,
            width=button_width,
        )
        self.delete_btn.pack(pady=padding)

        self.delete_all_btn = tk.Button(
            self,
            text="Delete All Records",
            command=self.delete_all_records,
            width=button_width,
        )
        self.delete_all_btn.pack(pady=padding)

        self.set_initial_balance_btn = tk.Button(
            self,
            text="Set Initial Balance",
            command=self.set_initial_balance,
            width=button_width,
        )
        self.set_initial_balance_btn.pack(pady=padding)
        self.manage_mandatory_btn = tk.Button(
            self,
            text="Manage Mandatory",
            command=self.manage_mandatory_expenses,
            width=button_width,
        )
        self.manage_mandatory_btn.pack(pady=padding)

        # Import format selector and single Import button
        self.import_format_var = tk.StringVar(value="CSV")
        self.import_format_menu = tk.OptionMenu(
            self, self.import_format_var, "CSV", "XLSX", "PDF"
        )
        self.import_format_menu.config(width=button_width - 3)
        self.import_format_menu.pack(pady=padding)
        self.import_btn = tk.Button(
            self,
            text="Import",
            command=self._import_handler,
            width=button_width,
        )
        self.import_btn.pack(pady=padding)

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
                raise ValueError("Invalid date components")
            # Check if date is not in the future
            from datetime import datetime

            entered_date = datetime(year, month, day).date()
            today = datetime.now().date()
            if entered_date > today:
                raise ValueError("Date cannot be in the future")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD.")
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
        # If report window already exists, bring it to front and focus it
        if self.report_window and self.report_window.winfo_exists():
            try:
                self.report_window.deiconify()
                self.report_window.lift()
                self.report_window.focus_force()
            except Exception:
                pass
            return

        report_window = Toplevel(self)
        self.report_window = report_window
        report_window.title("Generate Report")
        report_window.geometry("800x400")

        def _on_report_close():
            try:
                report_window.destroy()
            except Exception:
                pass
            self.report_window = None

        report_window.protocol("WM_DELETE_WINDOW", _on_report_close)

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
                initial_balance = self.repository.load_initial_balance()
                records_total = sum(r.signed_amount() for r in report.records())
                final_balance = report.total()
                result_text.insert(
                    tk.END, f"Initial Balance: {initial_balance:.2f} KZT\n"
                )
                result_text.insert(tk.END, f"Records Total: {records_total:.2f} KZT\n")
                result_text.insert(tk.END, f"Final Balance: {final_balance:.2f} KZT\n")

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

        # Export format selector + single Export button
        export_format_var = tk.StringVar(value="CSV")
        export_menu = tk.OptionMenu(
            report_window, export_format_var, "CSV", "XLSX", "PDF"
        )
        export_menu.grid(row=4, column=1, pady=10)

        def export_any():
            nonlocal current_report
            if current_report is None:
                messagebox.showerror("Error", "Please generate a report first.")
                return
            fmt = export_format_var.get()
            if fmt == "CSV":
                export_csv()
            elif fmt == "XLSX":
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    title="Save Report as Excel",
                )
                if filepath:
                    try:
                        report_to_xlsx(current_report, filepath)
                        messagebox.showinfo("Success", f"Report exported to {filepath}")
                        os.startfile(os.path.dirname(filepath))
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Failed to export Excel: {str(e)}"
                        )
            else:  # PDF
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    title="Save Report as PDF",
                )
                if filepath:
                    try:
                        report_to_pdf(current_report, filepath)
                        messagebox.showinfo("Success", f"Report exported to {filepath}")
                        os.startfile(os.path.dirname(filepath))
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

        export_btn = tk.Button(report_window, text="Export", command=export_any)
        export_btn.grid(row=4, column=2, pady=10)

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

        # If delete window already exists, bring it to front and focus it
        if self.delete_window and self.delete_window.winfo_exists():
            try:
                self.delete_window.deiconify()
                self.delete_window.lift()
                self.delete_window.focus_force()
            except Exception:
                pass
            return

        delete_window = Toplevel(self)
        self.delete_window = delete_window
        delete_window.title("Delete Record")
        delete_window.geometry("500x400")

        def _on_delete_close():
            try:
                delete_window.destroy()
            except Exception:
                pass
            self.delete_window = None

        delete_window.protocol("WM_DELETE_WINDOW", _on_delete_close)

        listbox = Listbox(delete_window)
        for i, record in enumerate(all_records):
            if isinstance(record, IncomeRecord):
                record_type = "Income"
            elif isinstance(record, MandatoryExpenseRecord):
                record_type = "Mandatory Expense"
            else:
                record_type = "Expense"
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
                # Close and clear tracked window reference, then reopen to refresh list
                try:
                    delete_window.destroy()
                except Exception:
                    pass
                self.delete_window = None
                self.delete_record()
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

    def import_from_csv(self):
        # File selection dialog
        filepath = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Select CSV file to import",
        )
        if not filepath:
            return

        try:
            # Confirmation dialog
            confirm = messagebox.askyesno(
                "Confirm Import",
                f"This will replace all existing records with data from:\n{filepath}\n\nContinue?",
            )
            if not confirm:
                return

            # Import records
            import_use_case = ImportFromCSV(self.repository)
            imported_count = import_use_case.execute(filepath)

            messagebox.showinfo(
                "Success",
                f"Successfully imported {imported_count} records from CSV file.\nAll existing records have been replaced.",
            )

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import CSV: {str(e)}")

    def import_from_excel(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Select XLSX file to import",
        )
        if not filepath:
            return

        try:
            confirm = messagebox.askyesno(
                "Confirm Import",
                f"This will replace all existing records with data from:\n{filepath}\n\nContinue?",
            )
            if not confirm:
                return

            report = report_from_xlsx(filepath)

            # Replace repository data
            self.repository.delete_all()
            imported_count = 0
            for record in report.records():
                self.repository.save(record)
                imported_count += 1

            messagebox.showinfo(
                "Success",
                f"Successfully imported {imported_count} records from Excel file.\nAll existing records have been replaced.",
            )

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import Excel: {str(e)}")

    def import_from_pdf(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Select PDF file to import",
        )
        if not filepath:
            return

        try:
            confirm = messagebox.askyesno(
                "Confirm Import",
                f"This will replace all existing records with data from:\n{filepath}\n\nContinue?",
            )
            if not confirm:
                return

            report = report_from_pdf(filepath)

            # Replace repository data
            self.repository.delete_all()
            imported_count = 0
            for record in report.records():
                self.repository.save(record)
                imported_count += 1

            messagebox.showinfo(
                "Success",
                f"Successfully imported {imported_count} records from PDF file.\nAll existing records have been replaced.",
            )

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import PDF: {str(e)}")

    def _import_handler(self):
        fmt = self.import_format_var.get()
        if fmt == "CSV":
            self.import_from_csv()
        elif fmt == "XLSX":
            self.import_from_excel()
        else:
            self.import_from_pdf()

    def set_initial_balance(self):
        current_balance = self.repository.load_initial_balance()
        balance_str = simpledialog.askstring(
            "Initial Balance",
            f"Enter initial balance (current: {current_balance:.2f} KZT):",
            parent=self,
            initialvalue=str(current_balance),
        )
        if balance_str is None:
            return
        try:
            balance = float(balance_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid balance amount.")
            return

        self.repository.save_initial_balance(balance)
        messagebox.showinfo("Success", f"Initial balance set to {balance:.2f} KZT.")

    def manage_mandatory_expenses(self):
        # If manage window already exists, bring it to front and focus it
        if self.manage_window and self.manage_window.winfo_exists():
            try:
                self.manage_window.deiconify()
                self.manage_window.lift()
                self.manage_window.focus_force()
            except Exception:
                pass
            return

        manage_window = Toplevel(self)
        self.manage_window = manage_window
        manage_window.title("Manage Mandatory Expenses")
        manage_window.geometry("650x400")

        def _on_manage_close():
            try:
                manage_window.destroy()
            except Exception:
                pass
            self.manage_window = None

        manage_window.protocol("WM_DELETE_WINDOW", _on_manage_close)

        # Listbox for mandatory expenses
        listbox = Listbox(manage_window, width=80, height=15)
        scrollbar = Scrollbar(manage_window, orient=VERTICAL, command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # Buttons frame
        buttons_frame = tk.Frame(manage_window)
        buttons_frame.pack(pady=10)

        def refresh_list():
            listbox.delete(0, tk.END)
            get_expenses = GetMandatoryExpenses(self.repository)
            expenses = get_expenses.execute()
            for i, expense in enumerate(expenses):
                listbox.insert(
                    tk.END,
                    f"[{i}] {expense.amount:.2f} KZT - {expense.category} - {expense.description} ({expense.period})",
                )

        def add_expense():
            # Create add expense window
            add_window = Toplevel(manage_window)
            add_window.title("Add Mandatory Expense")
            add_window.geometry("400x300")

            tk.Label(add_window, text="Amount:").grid(
                row=0, column=0, sticky="w", padx=10, pady=5
            )
            amount_entry = tk.Entry(add_window)
            amount_entry.grid(row=0, column=1, padx=10, pady=5)

            tk.Label(add_window, text="Currency (default KZT):").grid(
                row=1, column=0, sticky="w", padx=10, pady=5
            )
            currency_entry = tk.Entry(add_window)
            currency_entry.insert(0, "KZT")
            currency_entry.grid(row=1, column=1, padx=10, pady=5)

            tk.Label(add_window, text="Category (default Mandatory):").grid(
                row=2, column=0, sticky="w", padx=10, pady=5
            )
            category_entry = tk.Entry(add_window)
            category_entry.insert(0, "Mandatory")
            category_entry.grid(row=2, column=1, padx=10, pady=5)

            tk.Label(add_window, text="Description:").grid(
                row=3, column=0, sticky="w", padx=10, pady=5
            )
            description_entry = tk.Entry(add_window)
            description_entry.grid(row=3, column=1, padx=10, pady=5)

            tk.Label(add_window, text="Period:").grid(
                row=4, column=0, sticky="w", padx=10, pady=5
            )
            period_var = tk.StringVar(value="monthly")
            period_menu = tk.OptionMenu(
                add_window, period_var, "daily", "weekly", "monthly", "yearly"
            )
            period_menu.grid(row=4, column=1, padx=10, pady=5)

            def save_expense():
                try:
                    amount = float(amount_entry.get())
                    currency = currency_entry.get() or "KZT"
                    category = category_entry.get() or "Mandatory"
                    description = description_entry.get()
                    period = period_var.get()

                    if not description:
                        messagebox.showerror("Error", "Description is required.")
                        return

                    create_expense = CreateMandatoryExpense(
                        self.repository, self.currency
                    )
                    create_expense.execute(
                        amount=amount,
                        currency=currency,
                        category=category,
                        description=description,
                        period=period,
                    )
                    messagebox.showinfo("Success", "Mandatory expense added.")
                    add_window.destroy()
                    refresh_list()
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add expense: {str(e)}")

            save_btn = tk.Button(add_window, text="Save", command=save_expense)
            save_btn.grid(row=5, column=0, columnspan=2, pady=20)

        def delete_expense():
            selection = listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select an expense to delete.")
                return

            index = selection[0]
            confirm = messagebox.askyesno(
                "Confirm Delete", "Delete this mandatory expense?"
            )
            if confirm:
                delete_use_case = DeleteMandatoryExpense(self.repository)
                if delete_use_case.execute(index):
                    messagebox.showinfo("Success", "Mandatory expense deleted.")
                    refresh_list()
                else:
                    messagebox.showerror("Error", "Failed to delete expense.")

        def delete_all_expenses():
            confirm = messagebox.askyesno(
                "Confirm Delete All", "Delete ALL mandatory expenses?"
            )
            if confirm:
                delete_all_use_case = DeleteAllMandatoryExpenses(self.repository)
                delete_all_use_case.execute()
                messagebox.showinfo("Success", "All mandatory expenses deleted.")
                refresh_list()

        def add_to_report():
            selection = listbox.curselection()
            if not selection:
                messagebox.showerror(
                    "Error", "Please select an expense to add to report."
                )
                return

            index = selection[0]
            date = simpledialog.askstring(
                "Date", "Enter date (YYYY-MM-DD):", parent=manage_window
            )
            if not date:
                return

            try:
                # Basic date validation
                year, month, day = map(int, date.split("-"))
                if not (
                    1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]
                ):
                    raise ValueError("Invalid date")

                add_to_report_use_case = AddMandatoryExpenseToReport(
                    self.repository, self.currency
                )
                if add_to_report_use_case.execute(index, date):
                    messagebox.showinfo(
                        "Success", f"Mandatory expense added to report for {date}."
                    )
                else:
                    messagebox.showerror("Error", "Failed to add expense to report.")
            except ValueError as e:
                messagebox.showerror(
                    "Error", f"Invalid date: {str(e)}. Use YYYY-MM-DD."
                )

        # Format selector for mandatory expenses export/import
        mandatory_format_var = tk.StringVar(value="CSV")
        mandatory_format_menu = tk.OptionMenu(
            buttons_frame, mandatory_format_var, "CSV", "XLSX", "PDF"
        )
        mandatory_format_menu.config(width=11)
        mandatory_format_menu.pack(pady=10)

        def export_expenses_csv():
            get_expenses = GetMandatoryExpenses(self.repository)
            expenses = get_expenses.execute()
            if not expenses:
                messagebox.showinfo("No Expenses", "No mandatory expenses to export.")
                return

            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Mandatory Expenses to CSV",
            )
            if filepath:
                try:
                    export_mandatory_expenses_to_csv(expenses, filepath)
                    messagebox.showinfo(
                        "Success", f"Mandatory expenses exported to {filepath}"
                    )
                    # Open the folder containing the file
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export: {str(e)}")

        def export_expenses_excel():
            get_expenses = GetMandatoryExpenses(self.repository)
            expenses = get_expenses.execute()
            if not expenses:
                messagebox.showinfo("No Expenses", "No mandatory expenses to export.")
                return

            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Export Mandatory Expenses to XLSX",
            )
            if filepath:
                try:
                    export_mandatory_expenses_to_xlsx(expenses, filepath)
                    messagebox.showinfo(
                        "Success", f"Mandatory expenses exported to {filepath}"
                    )
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export XLSX: {str(e)}")

        def import_expenses_csv():
            # File selection dialog
            filepath = filedialog.askopenfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Select CSV file to import mandatory expenses",
            )
            if not filepath:
                return

            try:
                # Confirmation dialog
                confirm = messagebox.askyesno(
                    "Confirm Import",
                    f"This will replace all existing mandatory expenses with data from:\n{filepath}\n\nContinue?",
                )
                if not confirm:
                    return

                # Import mandatory expenses
                expenses = import_mandatory_expenses_from_csv(filepath)

                # Delete all existing mandatory expenses first
                delete_all_use_case = DeleteAllMandatoryExpenses(self.repository)
                delete_all_use_case.execute()

                # Save imported expenses
                for expense in expenses:
                    create_expense = CreateMandatoryExpense(
                        self.repository, self.currency
                    )
                    create_expense.execute(
                        amount=expense.amount,
                        currency="KZT",  # Assume KZT for imported expenses
                        category=expense.category,
                        description=expense.description,
                        period=expense.period,
                    )

                messagebox.showinfo(
                    "Success",
                    f"Successfully imported {len(expenses)} mandatory expenses from CSV file.\nAll existing mandatory expenses have been replaced.",
                )
                refresh_list()

            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import CSV: {str(e)}")

        def import_expenses_xlsx():
            filepath = filedialog.askopenfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Select XLSX file to import mandatory expenses",
            )
            if not filepath:
                return

            try:
                confirm = messagebox.askyesno(
                    "Confirm Import",
                    f"This will replace all existing mandatory expenses with data from:\n{filepath}\n\nContinue?",
                )
                if not confirm:
                    return

                expenses = import_mandatory_expenses_from_xlsx(filepath)

                # Delete all existing mandatory expenses first
                delete_all_use_case = DeleteAllMandatoryExpenses(self.repository)
                delete_all_use_case.execute()

                # Save imported expenses
                for expense in expenses:
                    create_expense = CreateMandatoryExpense(
                        self.repository, self.currency
                    )
                    create_expense.execute(
                        amount=expense.amount,
                        currency="KZT",
                        category=expense.category,
                        description=expense.description,
                        period=expense.period,
                    )

                messagebox.showinfo(
                    "Success",
                    f"Successfully imported {len(expenses)} mandatory expenses from XLSX file.\nAll existing mandatory expenses have been replaced.",
                )
                refresh_list()

            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import XLSX: {str(e)}")

        # Buttons
        button_width = 14  # Set uniform width for all buttons

        add_btn = tk.Button(
            buttons_frame, text="Add", command=add_expense, width=button_width
        )
        add_btn.pack(pady=10)

        delete_btn = tk.Button(
            buttons_frame, text="Delete", command=delete_expense, width=button_width
        )
        delete_btn.pack(pady=10)

        delete_all_btn = tk.Button(
            buttons_frame,
            text="Delete All",
            command=delete_all_expenses,
            width=button_width,
        )
        delete_all_btn.pack(pady=10)

        add_to_report_btn = tk.Button(
            buttons_frame,
            text="Add to Report",
            command=add_to_report,
            width=button_width,
        )
        add_to_report_btn.pack(pady=10)

        def import_any():
            fmt = mandatory_format_var.get()
            if fmt == "CSV":
                import_expenses_csv()
            elif fmt == "XLSX":
                import_expenses_xlsx()
            else:
                # PDF import
                filepath = filedialog.askopenfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    title="Select PDF file to import mandatory expenses",
                )
                if not filepath:
                    return
                try:
                    confirm = messagebox.askyesno(
                        "Confirm Import",
                        f"This will replace all existing mandatory expenses with data from:\n{filepath}\n\nContinue?",
                    )
                    if not confirm:
                        return
                    expenses = import_mandatory_expenses_from_pdf(filepath)
                    delete_all_use_case = DeleteAllMandatoryExpenses(self.repository)
                    delete_all_use_case.execute()
                    for expense in expenses:
                        create_expense = CreateMandatoryExpense(
                            self.repository, self.currency
                        )
                        create_expense.execute(
                            amount=expense.amount,
                            currency="KZT",
                            category=expense.category,
                            description=expense.description,
                            period=expense.period,
                        )
                    messagebox.showinfo(
                        "Success",
                        f"Successfully imported {len(expenses)} mandatory expenses from PDF file.\nAll existing mandatory expenses have been replaced.",
                    )
                    refresh_list()
                except FileNotFoundError:
                    messagebox.showerror("Error", f"File not found: {filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to import PDF: {str(e)}")

        def export_any():
            fmt = mandatory_format_var.get()
            if fmt == "CSV":
                export_expenses_csv()
            elif fmt == "XLSX":
                export_expenses_excel()
            else:  # PDF
                get_expenses = GetMandatoryExpenses(self.repository)
                expenses = get_expenses.execute()
                if not expenses:
                    messagebox.showinfo(
                        "No Expenses", "No mandatory expenses to export."
                    )
                    return
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    title="Export Mandatory Expenses to PDF",
                )
                if filepath:
                    try:
                        export_mandatory_expenses_to_pdf(expenses, filepath)
                        messagebox.showinfo(
                            "Success", f"Mandatory expenses exported to {filepath}"
                        )
                        os.startfile(os.path.dirname(filepath))
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

        import_btn = tk.Button(
            buttons_frame,
            text="Import",
            command=import_any,
            width=button_width,
        )
        import_btn.pack(pady=10)

        export_btn = tk.Button(
            buttons_frame,
            text="Export",
            command=export_any,
            width=button_width,
        )
        export_btn.pack(pady=10)

        close_btn = tk.Button(
            buttons_frame,
            text="Close",
            command=manage_window.destroy,
            width=button_width,
        )
        close_btn.pack(pady=10)

        # Initial refresh
        refresh_list()


def main() -> None:
    app = FinancialApp()
    app.mainloop()


if __name__ == "__main__":
    main()
