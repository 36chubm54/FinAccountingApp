# FinAccountingApp

Desktop and web application for personal finance tracking with multi‑currency support, categories, and reports.

## 📋 Contents

- [Quick start](#-quick-start)
- [Using the application](#️-using-the-application)
- [Web application](#-web-application)
- [Project architecture](#️-project-architecture)
- [Software API](#-software-api)
- [File structure](#-file-structure)
- [Tests](#-tests)
- [Supported currencies](#-supported-currencies)

---

## 🚀 Quick start

### System requirements

- Python 3.10+
- pip

### Installation

```bash
# Go to the project directory
cd "Проект ФУ/project"

# Create a virtual environment
python -m venv .venv

# Activation (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activation (Windows CMD)
.venv\Scripts\activate.bat

# Activation (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### First launch

```bash
python main.py
```

---

## 🖥️ Using the application

### Main window

After running `python main.py`, you will see buttons and an infographic panel.

Buttons and actions:

- `Add Income` — add income.
- `Add Expense` — add expense.
- `Generate Report` — generate a report with filters.
- `Delete Record` — delete a single record.
- `Delete All Records` — delete all records.
- `Set Initial Balance` — set opening balance.
- `Manage Mandatory` — manage mandatory expenses.
- Import format selector (`CSV`, `XLSX`) and `Import` button for records.

Infographics:

- Expense pie chart by category with month filter.
- Daily income/expense bars for a selected month.
- Monthly income/expense bars for a selected year.

Income is green, expenses are red. Small categories are grouped into “Other”. The legend list is scrollable.

### Add income/expense

1. Click `Add Income` or `Add Expense`.
2. Enter date `YYYY-MM-DD` (future dates are not allowed).
3. Enter amount.
4. Choose currency (default `KZT`).
5. Enter category (default `General`).
6. Click `Save`.

Amounts are converted to base currency `KZT`.

### Generate report

1. Click `Generate Report`.
2. Optional filters:

- `Period` — date prefix (`2025` or `2025-01`).
- `Category` — category filter.

1. Options:

- `Group by category`.
- `Display as table`.

1. Click `Generate`.

A monthly income/expense summary table is appended at the bottom.

Export formats:

- `CSV`, `XLSX`, `PDF`.
- `XLSX` includes a `Yearly Report` sheet with a monthly summary.

### Delete record

1. Click `Delete Record`.
2. Select a row and confirm.

### Set initial balance

1. Click `Set Initial Balance`.
2. Enter the amount (can be negative).

### Manage mandatory expenses

Buttons:

- `Add` — add mandatory expense.
- `Delete` — delete selected.
- `Delete All` — delete all.
- `Add to Report` — add selected expense to report with a date.
- `Import` — import mandatory expenses.
- `Export` — export mandatory expenses.

Mandatory expense fields:

- `Amount`, `Currency`, `Category` (default `Mandatory`), `Description` (required), `Period` (`daily`, `weekly`, `monthly`, `yearly`).

Import/Export:

- Import: `CSV`, `XLSX`.
- Export: `CSV`, `XLSX`, `PDF`.

### Import financial records

Use `Import` in the main window.

Formats:

- `CSV`, `XLSX`.
- Existing records are fully replaced by the imported data.

Format rules:

- Columns: `Date,Type,Category,Amount (KZT)`.
- `Type`: `Income`, `Expense`, `Mandatory Expense`.
- Optional `Initial Balance` row with empty date.
- `SUBTOTAL` and `FINAL BALANCE` rows are ignored on import.

### Data storage

Stored in `records.json` in the project root.

```json
{
  "initial_balance": 50000.0,
  "records": [
    {
      "type": "income",
      "date": "2025-01-15",
      "amount": 350000.0,
      "category": "Salary"
    },
    {
      "type": "expense",
      "date": "2025-01-16",
      "amount": 25000.0,
      "category": "Food"
    },
    {
      "type": "mandatory_expense",
      "date": "2025-01-20",
      "amount": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ],
  "mandatory_expenses": [
    {
      "date": "",
      "amount": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ]
}
```

---

## 🌐 Web application

The web version lives in `web/` and runs fully in the browser without a server. Data is stored in `localStorage`.

Highlights:

- Dashboard, income, expenses, reports, settings.
- Built‑in charts and summaries.
- Exchange rates from NBRK RSS (`rates_all.xml`) with daily cache in `localStorage`.
- CSV export (web version).

Launch: open `web/index.html` in a browser.

---

## 🏗️ Project architecture

Layered architecture:

- `domain/` — business models and rules (records, reports, validation, currency).
- `app/` — use cases and currency adapter.
- `infrastructure/` — JSON repository.
- `utils/` — import/export and chart helpers.
- `web/` — standalone web app.

GUI flow:

- UI (Tkinter) → `app/use_cases.py` → `infrastructure/repositories.py` → `records.json`.

---

## 📝 Software API

### Domain

`domain/records.py`

- `Record`, `IncomeRecord`, `ExpenseRecord`, `MandatoryExpenseRecord`.

`domain/currency.py`

- `CurrencyService` — base currency conversion.

`domain/reports.py`

- `Report(records, initial_balance=0.0)`.
- `total()`, `filter_by_period()`, `filter_by_category()`, `grouped_by_category()`.
- `monthly_income_expense_rows()` and `monthly_income_expense_table()`.
- `as_table(summary_mode="full"|"total_only")`.
- `to_csv()` / `from_csv()`.

`domain/validation.py`

- `parse_ymd()`, `ensure_not_future()`, `ensure_valid_period()`.

### Application

`app/services.py`

- `CurrencyService(rates=None, base="KZT", use_online=False)` with NBRK RSS caching to `currency_rates.json`.

`app/use_cases.py`

- `CreateIncome`, `CreateExpense`, `GenerateReport`, `DeleteRecord`, `DeleteAllRecords`.
- `ImportFromCSV`.
- `CreateMandatoryExpense`, `GetMandatoryExpenses`, `DeleteMandatoryExpense`, `DeleteAllMandatoryExpenses`, `AddMandatoryExpenseToReport`.

### Infrastructure

`infrastructure/repositories.py`

- `RecordRepository`, `JsonFileRecordRepository` with methods for records, initial balance, and mandatory expenses.

### Utils

`utils/csv_utils.py`, `utils/excel_utils.py`, `utils/pdf_utils.py`, `utils/charting.py`.

---

## 📁 File structure

```
project/
│
├── main.py                     # Tkinter GUI entry
├── records.json                # Records storage (auto‑created)
├── currency_rates.json         # Rates cache (use_online=True)
├── requirements.txt
├── pytest.ini
├── README.md
├── README_EN.md
├── CHANGELOG.md
├── LICENSE
│
├── app/
│   ├── __init__.py
│   ├── services.py
│   └── use_cases.py
│
├── domain/
│   ├── __init__.py
│   ├── records.py
│   ├── reports.py
│   ├── currency.py
│   └── validation.py
│
├── infrastructure/
│   └── repositories.py
│
├── utils/
│   ├── __init__.py
│   ├── csv_utils.py
│   ├── excel_utils.py
│   ├── pdf_utils.py
│   └── charting.py
│
├── web/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── tests/
    ├── __init__.py
    ├── test_charting.py
    ├── test_csv.py
    ├── test_currency.py
    ├── test_excel.py
    ├── test_pdf.py
    ├── test_records.py
    ├── test_reports.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_use_cases.py
    └── test_validation.py
```

---

## 🧪 Tests

### Running tests

```bash
cd "Проект ФУ/project"
pytest
pytest -v
pytest tests/test_records.py -v
pytest tests/test_reports.py::test_report_total -v
```

### Coverage

```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
pytest --cov=. --cov-report=html
```

Note: tests expect `CurrencyService` default to `use_online=False`.

---

## 💱 Supported currencies

| Currency          | Code | Default rate | Description     |
| ----------------- | ---- | ------------ | --------------- |
| Kazakhstani tenge | KZT  | 1.0          | Base currency   |
| US dollar         | USD  | 500.0        | 1 USD = 500 KZT |
| Euro              | EUR  | 590.0        | 1 EUR = 590 KZT |
| Russian ruble     | RUB  | 6.5          | 1 RUB = 6.5 KZT |

If you create `CurrencyService(use_online=True)`, rates are loaded from NBRK and cached in `currency_rates.json`.

---

## 📄 License

MIT License — free to use, modify, and distribute.
