import sys
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
from datetime import datetime

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
from domain.records import IncomeRecord, MandatoryExpenseRecord
from app.services import CurrencyService
from utils.charting import (
    aggregate_expenses_by_category,
    aggregate_daily_cashflow,
    aggregate_monthly_cashflow,
    extract_months,
    extract_years,
)

# Ensure project package root is on sys.path so imports work regardless of CWD
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class FinancialApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Financial Accounting")
        self.geometry("1000x700")
        self.minsize(900, 600)

        # Track open windows so repeated button presses focus them instead of creating new ones
        self.add_record_window = None
        self.add_mandatory_window = None
        self.report_window = None
        self.delete_window = None
        self.manage_window = None

        self.repository = JsonFileRecordRepository(
            str(Path(__file__).parent / "records.json")
        )
        self.currency = CurrencyService()

        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Buttons
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.grid(row=0, column=0, sticky="ns", padx=20, pady=20)

        # Right: Charts
        charts_frame = tk.Frame(main_frame)
        charts_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=20)

        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Buttons
        button_width = 15  # Set uniform width for all buttons
        padding = 10

        self.add_income_btn = tk.Button(
            buttons_frame,
            text="Add Income",
            command=self.add_income,
            width=button_width,
        )
        self.add_income_btn.pack(pady=padding)

        self.add_expense_btn = tk.Button(
            buttons_frame,
            text="Add Expense",
            command=self.add_expense,
            width=button_width,
        )
        self.add_expense_btn.pack(pady=padding)

        self.report_btn = tk.Button(
            buttons_frame,
            text="Generate Report",
            command=self.generate_report,
            width=button_width,
        )
        self.report_btn.pack(pady=padding)

        self.delete_btn = tk.Button(
            buttons_frame,
            text="Delete Record",
            command=self.delete_record,
            width=button_width,
        )
        self.delete_btn.pack(pady=padding)

        self.delete_all_btn = tk.Button(
            buttons_frame,
            text="Delete All Records",
            command=self.delete_all_records,
            width=button_width,
        )
        self.delete_all_btn.pack(pady=padding)

        self.set_initial_balance_btn = tk.Button(
            buttons_frame,
            text="Set Initial Balance",
            command=self.set_initial_balance,
            width=button_width,
        )
        self.set_initial_balance_btn.pack(pady=padding)

        self.manage_mandatory_btn = tk.Button(
            buttons_frame,
            text="Manage Mandatory",
            command=self.manage_mandatory_expenses,
            width=button_width,
        )
        self.manage_mandatory_btn.pack(pady=padding)

        # Import format selector and single Import button
        self.import_format_var = tk.StringVar(value="CSV")
        self.import_format_menu = tk.OptionMenu(
            buttons_frame, self.import_format_var, "CSV", "XLSX"
        )
        self.import_format_menu.config(width=button_width - 3)
        self.import_format_menu.pack(pady=padding)

        self.import_btn = tk.Button(
            buttons_frame,
            text="Import",
            command=self._import_handler,
            width=button_width,
        )
        self.import_btn.pack(pady=padding)

        self._build_charts(charts_frame)
        self.refresh_charts()

    def add_income(self):
        self._add_record("Income", CreateIncome)

    def add_expense(self):
        self._add_record("Expense", CreateExpense)

    def _add_record(self, record_type, use_case_class):
        # If add window already exists, bring it to front and focus it
        if self.add_record_window and self.add_record_window.winfo_exists():
            try:
                self.add_record_window.deiconify()
                self.add_record_window.lift()
                self.add_record_window.focus_force()
            except Exception:
                pass
            return

        # Create add record window
        add_record_window = Toplevel(self)
        self.add_record_window = add_record_window
        add_record_window.title(f"Add {record_type}")
        add_record_window.geometry("400x300")

        def _on_add_record_close():
            try:
                add_record_window.destroy()
            except Exception:
                pass
            self.add_record_window = None

        add_record_window.protocol("WM_DELETE_WINDOW", _on_add_record_close)

        tk.Label(self.add_record_window, text="Date (YYYY-MM-DD):").grid(
            row=0, column=0, sticky="w", padx=10, pady=5
        )
        date_entry = tk.Entry(self.add_record_window)
        date_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self.add_record_window, text="Amount:").grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        amount_entry = tk.Entry(self.add_record_window)
        amount_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self.add_record_window, text="Currency (default KZT):").grid(
            row=2, column=0, sticky="w", padx=10, pady=5
        )
        currency_entry = tk.Entry(self.add_record_window)
        currency_entry.insert(0, "KZT")
        currency_entry.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(self.add_record_window, text="Category (default General):").grid(
            row=3, column=0, sticky="w", padx=10, pady=5
        )
        category_entry = tk.Entry(self.add_record_window)
        category_entry.insert(0, "General")
        category_entry.grid(row=3, column=1, padx=10, pady=5)

        def save_and_close():
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
                use_case = use_case_class(self.repository, self.currency)
                use_case.execute(
                    date=date_str, amount=amount, currency=currency, category=category
                )
                messagebox.showinfo(
                    "Success",
                    f"Added {record_type.lower()}: {amount} {currency} on {date_str} (category: {category})",
                )
                self.refresh_charts()
                add_record_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add record: {str(e)}")

        save_btn = tk.Button(self.add_record_window, text="Save", command=save_and_close)
        save_btn.grid(row=4, column=0, padx=10, pady=15)

        cancel_btn = tk.Button(
            self.add_record_window, text="Cancel", command=self.add_record_window.destroy
        )
        cancel_btn.grid(row=4, column=1, padx=10, pady=15)

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
                            tk.END, cat_report.as_table(summary_mode="total_only") + "\n"
                        )
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

            summary_table = report.monthly_income_expense_table(
                year=summary_year, up_to_month=summary_up_to_month
            )
            result_text.insert(
                tk.END, "\n\nMonthly Income/Expense Summary (Past & Current Months)\n"
            )
            result_text.insert(tk.END, summary_table + "\n")

        generate_btn = tk.Button(report_window, text="Generate", command=generate)
        generate_btn.grid(row=4, column=0, pady=10)

        # Export format selector + single Export button
        export_format_var = tk.StringVar(value="CSV")
        export_menu = tk.OptionMenu(
            report_window, export_format_var, "CSV", "XLSX", "PDF"
        )
        export_menu.grid(row=4, column=1, pady=10)

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

        def export_excel():
            nonlocal current_report
            if current_report is None:
                messagebox.showerror("Error", "Please generate a report first.")
                return
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Save Report as Excel",
            )
            if filepath:
                try:
                    from utils.excel_utils import report_to_xlsx

                    report_to_xlsx(current_report, filepath)
                    messagebox.showinfo("Success", f"Report exported to {filepath}")
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export Excel: {str(e)}")

        def export_pdf():
            nonlocal current_report
            if current_report is None:
                messagebox.showerror("Error", "Please generate a report first.")
                return
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Save Report as PDF",
            )
            if filepath:
                try:
                    from utils.pdf_utils import report_to_pdf

                    report_to_pdf(current_report, filepath)
                    messagebox.showinfo("Success", f"Report exported to {filepath}")
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

        def export_any():
            fmt = export_format_var.get()
            if fmt == "CSV":
                export_csv()
            elif fmt == "XLSX":
                export_excel()
            else:  # PDF
                export_pdf()

        export_btn = tk.Button(report_window, text="Export", command=export_any)
        export_btn.grid(row=4, column=2, pady=10)

        result_text = tk.Text(report_window, wrap="word")
        scrollbar = Scrollbar(report_window, orient=VERTICAL, command=result_text.yview)
        result_text.config(yscrollcommand=scrollbar.set)
        result_text.grid(row=5, column=0, columnspan=2, sticky="nsew")
        scrollbar.grid(row=5, column=2, sticky="ns")

        report_window.grid_rowconfigure(5, weight=1)
        report_window.grid_columnconfigure(1, weight=1)

    def _build_charts(self, parent: tk.Frame) -> None:
        title = tk.Label(parent, text="Инфографика", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        pie_frame = tk.LabelFrame(parent, text="Расходы по категориям")
        pie_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        daily_frame = tk.LabelFrame(parent, text="Доходы/расходы по дням месяца")
        daily_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        monthly_frame = tk.LabelFrame(parent, text="Доходы/расходы по месяцам года")
        monthly_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        self.expense_pie_canvas = tk.Canvas(
            pie_frame, height=240, bg="white", highlightthickness=0
        )
        self.expense_pie_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.expense_legend_frame = tk.Frame(pie_frame)
        self.expense_legend_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        daily_controls = tk.Frame(daily_frame)
        daily_controls.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(daily_controls, text="Месяц:").pack(side=tk.LEFT)

        self.chart_month_var = tk.StringVar()
        self.chart_month_menu = tk.OptionMenu(
            daily_controls, self.chart_month_var, ""
        )
        self.chart_month_menu.pack(side=tk.LEFT, padx=6)
        self.chart_month_var.trace_add("write", self._on_chart_filter_change)

        self.daily_bar_canvas = tk.Canvas(
            daily_frame, height=220, bg="white", highlightthickness=0
        )
        self.daily_bar_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        monthly_controls = tk.Frame(monthly_frame)
        monthly_controls.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(monthly_controls, text="Год:").pack(side=tk.LEFT)

        self.chart_year_var = tk.StringVar()
        self.chart_year_menu = tk.OptionMenu(
            monthly_controls, self.chart_year_var, ""
        )
        self.chart_year_menu.pack(side=tk.LEFT, padx=6)
        self.chart_year_var.trace_add("write", self._on_chart_filter_change)

        self.monthly_bar_canvas = tk.Canvas(
            monthly_frame, height=220, bg="white", highlightthickness=0
        )
        self.monthly_bar_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._chart_refresh_suspended = False

        def _redraw(_event=None):
            self.refresh_charts()

        self.expense_pie_canvas.bind("<Configure>", _redraw)
        self.daily_bar_canvas.bind("<Configure>", _redraw)
        self.monthly_bar_canvas.bind("<Configure>", _redraw)

    def _on_chart_filter_change(self, *_args) -> None:
        if self._chart_refresh_suspended:
            return
        self.refresh_charts()

    def refresh_charts(self) -> None:
        records = self.repository.load_all()

        self._chart_refresh_suspended = True
        self._update_month_options(records)
        self._update_year_options(records)
        self._chart_refresh_suspended = False

        self._draw_expense_pie(records)
        self._draw_daily_bars(records)
        self._draw_monthly_bars(records)

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
        totals = aggregate_expenses_by_category(records)
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
                text="Нет расходов для отображения",
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
            color_box = tk.Canvas(
                legend_row, width=12, height=12, highlightthickness=0
            )
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
        major.append(("Прочее", other_total))
        return major

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
            "Янв",
            "Фев",
            "Мар",
            "Апр",
            "Май",
            "Июн",
            "Июл",
            "Авг",
            "Сен",
            "Окт",
            "Ноя",
            "Дек",
        ]
        self._draw_bar_chart(self.monthly_bar_canvas, labels, income, expense, 12)

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
                text="Нет данных для отображения",
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
            text="Доходы",
            fill="#10b981",
            anchor="sw",
            font=("Segoe UI", 9),
        )
        canvas.create_text(
            padding["left"] + 60,
            padding["top"] - 6,
            text="Расходы",
            fill="#ef4444",
            anchor="sw",
            font=("Segoe UI", 9),
        )

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
                self.refresh_charts()
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
            self.refresh_charts()

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
            self.refresh_charts()

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

            from utils.excel_utils import report_from_xlsx

            report = report_from_xlsx(filepath)

            # Replace repository data
            self.repository.delete_all()
            self.repository.save_initial_balance(report.initial_balance)
            imported_count = 0
            for record in report.records():
                self.repository.save(record)
                imported_count += 1

            messagebox.showinfo(
                "Success",
                f"Successfully imported {imported_count} records from Excel file.\nAll existing records have been replaced.",
            )
            self.refresh_charts()

        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import Excel: {str(e)}")

    def _import_handler(self):
        fmt = self.import_format_var.get()
        if fmt == "CSV":
            self.import_from_csv()
        else:  # XLSX
            self.import_from_excel()

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
            # If manage window already exists, bring it to front and focus it
            if self.add_mandatory_window and self.add_mandatory_window.winfo_exists():
                try:
                    self.add_mandatory_window.deiconify()
                    self.add_mandatory_window.lift()
                    self.add_mandatory_window.focus_force()
                except Exception:
                    pass
                return

            # Create add expense window
            add_mandatory_window = Toplevel(self)
            self.add_mandatory_window = add_mandatory_window
            add_mandatory_window.title("Add Mandatory Expense")
            add_mandatory_window.geometry("400x300")

            def _on_add_close():
                try:
                    add_mandatory_window.destroy()
                except Exception:
                    pass
                self.add_mandatory_window = None

            add_mandatory_window.protocol("WM_DELETE_WINDOW", _on_add_close)

            tk.Label(add_mandatory_window, text="Amount:").grid(
                row=0, column=0, sticky="w", padx=10, pady=5
            )
            amount_entry = tk.Entry(add_mandatory_window)
            amount_entry.grid(row=0, column=1, padx=10, pady=5)

            tk.Label(add_mandatory_window, text="Currency (default KZT):").grid(
                row=1, column=0, sticky="w", padx=10, pady=5
            )
            currency_entry = tk.Entry(add_mandatory_window)
            currency_entry.insert(0, "KZT")
            currency_entry.grid(row=1, column=1, padx=10, pady=5)

            tk.Label(add_mandatory_window, text="Category (default Mandatory):").grid(
                row=2, column=0, sticky="w", padx=10, pady=5
            )
            category_entry = tk.Entry(add_mandatory_window)
            category_entry.insert(0, "Mandatory")
            category_entry.grid(row=2, column=1, padx=10, pady=5)

            tk.Label(add_mandatory_window, text="Description:").grid(
                row=3, column=0, sticky="w", padx=10, pady=5
            )
            description_entry = tk.Entry(add_mandatory_window)
            description_entry.grid(row=3, column=1, padx=10, pady=5)

            tk.Label(add_mandatory_window, text="Period:").grid(
                row=4, column=0, sticky="w", padx=10, pady=5
            )
            period_var = tk.StringVar(value="monthly")
            period_menu = tk.OptionMenu(
                add_mandatory_window, period_var, "daily", "weekly", "monthly", "yearly"
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
                    self.refresh_charts()
                    add_mandatory_window.destroy()
                    refresh_list()
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add expense: {str(e)}")

            save_btn = tk.Button(add_mandatory_window, text="Save", command=save_expense)
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
                    self.refresh_charts()
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
                self.refresh_charts()
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
                from domain.validation import parse_ymd

                parse_ymd(date)

                add_to_report_use_case = AddMandatoryExpenseToReport(
                    self.repository, self.currency
                )
                if add_to_report_use_case.execute(index, date):
                    messagebox.showinfo(
                        "Success", f"Mandatory expense added to report for {date}."
                    )
                    self.refresh_charts()
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
                    from utils.csv_utils import export_mandatory_expenses_to_csv

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
                    from utils.excel_utils import export_mandatory_expenses_to_xlsx

                    export_mandatory_expenses_to_xlsx(expenses, filepath)
                    messagebox.showinfo(
                        "Success", f"Mandatory expenses exported to {filepath}"
                    )
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export XLSX: {str(e)}")

        def export_expenses_pdf():
            get_expenses = GetMandatoryExpenses(self.repository)
            expenses = get_expenses.execute()
            if not expenses:
                messagebox.showinfo("No Expenses", "No mandatory expenses to export.")
                return
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Export Mandatory Expenses to PDF",
            )
            if filepath:
                try:
                    from utils.pdf_utils import export_mandatory_expenses_to_pdf

                    export_mandatory_expenses_to_pdf(expenses, filepath)
                    messagebox.showinfo(
                        "Success", f"Mandatory expenses exported to {filepath}"
                    )
                    os.startfile(os.path.dirname(filepath))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

        def export_any():
            fmt = mandatory_format_var.get()
            if fmt == "CSV":
                export_expenses_csv()
            elif fmt == "XLSX":
                export_expenses_excel()
            else:  # PDF
                export_expenses_pdf()

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
                from utils.csv_utils import import_mandatory_expenses_from_csv

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
                self.refresh_charts()

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

                from utils.excel_utils import import_mandatory_expenses_from_xlsx

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
                self.refresh_charts()

            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import XLSX: {str(e)}")

        def import_any():
            fmt = mandatory_format_var.get()
            if fmt == "CSV":
                import_expenses_csv()
            elif fmt == "XLSX":
                import_expenses_xlsx()
            else:  # PDF
                messagebox.showinfo(
                    "Not Supported",
                    "Importing mandatory expenses from PDF is not supported.",
                )

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
    try:
        main()
    except KeyboardInterrupt:
        messagebox.showinfo("Info", "Application closed by user.")
