# FinAccountingApp

Graphical and web application for personal financial accounting with multicurrency, categories and reports.

## 📋 Contents

- [Quick start](#-quick-start)
- [Using the application](#️-using-the-application)
- [Web application](#-web-application)
- [Project architecture](#️-project-architecture)
- [Software API](#-software-api)
- [File structure](#-file-structure)
- [Tests](#-tests)
- [Supported currencies](#-supported-currencies)
- [Wallet Support (Phase 1)](#wallet-support-phase-1)
- [Wallets, Transfers and Commissions (Phase 2)](#wallets-transfers-and-commissions-phase-2)

---

## 🚀 Quick start

### System requirements

- Python 3.10+
- pip

### Installation

```bash
# Go to the project directory
cd "FU Project/project"

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

After launch, the graphical window of the Financial Accounting application will open.

---

## 🖥️ Using the application

### Main window

After running `python main.py`, a window will open with control tabs and an infographic block.

Tabs and actions:

- `Infographics` — displays infographics (pie charts, histograms) with the ability to filter by month/year.
- `Operations` — adding/deleting records, setting the initial balance.
- `Reports` — report generation, export.
- `Settings` — management of mandatory expenses.

Infographics:

- Pie chart of expenses by category with month filter.
- Histogram of income/expenses by day of the month.
- Histogram of income/expenses by month of the year.

Income is displayed in green, expenses in red. For a pie chart, small categories are aggregated into "Other". The list of categories in the legend scrolls.

### Adding income/expense

1. Open the `Operations` tab.
2. In the `Add operation` block, select the type of operation (`Income` or `Expense`).
3. Enter the date in the format `YYYY-MM-DD` (the date cannot be in the future).
4. Enter the amount.
5. Specify the currency (default is `KZT`).
6. Specify a category (default is `General`).
7. Click `Save`.

The amount is converted into the base currency `KZT` at the current rates of the currency service. Once an entry is added, the list is automatically updated.

### Report generation

1. Open the `Reports` tab.
2. Enter filters (optional):
    - `Period` — period start (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`).
    - `Period end` — period end (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`).
    - `Category` — filter by category.
3. Enable options:
    - `Group by category` — grouping by category.
    - `Display as table` — table format.
4. Click `Generate`.

At the bottom, an additional table “Monthly Income/Expense Summary” is displayed for the selected year and months.

Export report:

- Formats: `CSV`, `XLSX`, `PDF`.
- Report title includes the selected range:
  `Transaction statement (<start_date> - <end_date>)`.
- If `Period end` is not provided, current date is used as the period end.
- In addition to the main records, a `Yearly Report` sheet with a monthly summary is added to `XLSX`. A second, intermediate sheet `By Category` is also created with records grouped by categories and subtotals.
- In `PDF` the monthly summary remains, and after the main statement, tables are added broken down by category (each category is a separate table with a subtotal).

### Opening Balance in Filtered Reports

- `Initial balance` is the starting balance of the whole history and does not depend on filters.
- `Opening balance` is the balance at the beginning of the selected period and is calculated dynamically.
- For `YYYY`, period start is `YYYY-01-01`.
- For `YYYY-MM`, period start is `YYYY-MM-01`.
- For `YYYY-MM-DD`, period start is the provided date.
- The period filter cannot point to a future date (for all supported formats).

### Wallet Support (Phase 1)

- Added `Wallet` domain entity (`id`, `name`, `currency`, `initial_balance`, `system`).
- Added a system wallet for compatibility:
  `id=1`, `name="Main wallet"`, `system=True`.
- Legacy migration rules:
  move `global initial_balance` into `wallet.initial_balance`,
  assign `wallet_id=1` to existing records,
  set root JSON `initial_balance` to `0`.
- Transfer is intentionally not implemented in this phase.
- User behavior remains unchanged:
  no wallet selector in the UI yet, and new records are auto-assigned to `wallet_id=1`.

### Wallets, Transfers and Commissions (Phase 2)

- Added `allow_negative` to `Wallet`.
- Added `Transfer` aggregate (stored separately from `Record`).
- Implemented transfer as a double-entry operation:
  - `Expense` in `from_wallet`
  - `Income` in `to_wallet`
  - both records linked by the same `transfer_id`.
- Implemented transfer commission as a separate expense:
  - category `Commission`
  - `wallet_id = from_wallet`
  - reduces net worth and is included in expenses.
- Added dynamic `net worth` calculation:
  - supports both `fixed` and `current` modes.
- Financial invariants:
  - transfer without commission keeps total wallet value unchanged;
  - commission reduces total value exactly by commission amount;
  - global report excludes transfers from net profit while commission remains an expense.
- Formula:
  `opening_balance = initial_balance + sum(signed_amount for date < start_date)`.
- Filtered reports use `opening balance` and the row label `Opening balance`.
- Unfiltered reports use `initial balance` and the row label `Initial balance`.
- `CSV/XLSX/PDF` exports follow the same rule and display the correct balance label.
- Period validation is applied to both start and end values:
  both must match `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`, must not be in the future, and `end >= start`.
- This is required for financial correctness: period totals must start from the real balance at the beginning of that period.

### Deleting an entry

1. Open the `Operations` tab.
2. Select an entry from the list.
3. Click `Delete Selected`. A deletion message appears with the index of the entry.

### Delete all entries

1. Open the `Operations` tab.
2. In the `List of operations` block, select an entry from the list.
3. Click `Delete All Records` and confirm the deletion. The entries will be permanently deleted and the list of entries will be updated.

### Setting the initial balance

1. Open the `Settings` tab.
2. Enter the amount (can be negative).
3. Confirm by clicking `Save`.

The opening balance is taken into account in the final balance sheet.

### Managing mandatory expenses

In the `Settings` tab, in the `Mandatory Expenses` block, the following operations are available:

- `Add` — add a mandatory expense.
- `Delete` — delete the selected one.
- `Delete All` — delete everything.
- `Add to Report` — add the selected expense to the report with the specified date.
- File format selector for import/export.
- `Import` — import of mandatory expenses.
- `Export` — export of mandatory expenses.

Mandatory expense fields:

- `Amount`, `Currency`, `Category` (default `Mandatory`), `Description` (required), `Period` (`daily`, `weekly`, `monthly`, `yearly`).

Import/export of mandatory expenses:

- Import: `CSV`, `XLSX`.
- Export: `CSV`, `XLSX`.

### Importing financial records

Import is performed via `Import` in the `Operations` tab.

Formats:

- `CSV`, `XLSX`, `JSON` (for Full Backup).
- All existing entries are replaced with data from the file.

Data format:

- **CSV/XLSX data (import/export):**  
  `date,type,category,amount_original,currency,rate_at_operation,amount_kzt,description,period`
- Legacy import is supported (old files with the `amount` field or the `Amount (KZT)` column).
- All existing entries are replaced with data from the file.

Important:

- `CSV/XLSX report` and `CSV/XLSX data` are different formats.
- Report `CSV/XLSX` is read-only by the user and **should not** be used as a data source for import.

### ImportPolicy

There are 3 modes available for importing records:

- `Full Backup` (`ImportPolicy.FULL_BACKUP`)  
  Used for full import with a fixed transaction rate. Expected string format:
  `date,type,category,amount_original,currency,rate_at_operation,amount_kzt,description,period`.
- `Import Records (Current Rate)` (`ImportPolicy.CURRENT_RATE`)  
  For each imported line, the rate is taken at the time of import through `CurrencyService.get_rate(currency)`, and `rate_at_operation` and `amount_kzt` are recalculated and fixed again.
- `Legacy Import` (`ImportPolicy.LEGACY`)  
  The old `date,type,category,amount` format is automatically migrated to the new one:
  `currency="KZT"`, `rate_at_operation=1.0`, `amount_kzt=amount`.

All modes perform line-by-line validation and generate a report:
`(imported, skipped, errors)`.

### Backup

Full backup is implemented in `JSON` format:

- Fields: `initial_balance`, `records`, `mandatory_expenses`.
- The `Settings` tab contains the following buttons:
  - `Export Full Backup`
  - `Import Full Backup`

Backup restores:

- initial balance;
- all records with fields `amount_original/currency/rate_at_operation/amount_kzt`;
- all mandatory expenses with `description/period`.

### FX Revaluation

`Report` supports:

- `total_fixed()` — accounting total at the exchange rate on the transaction date;
- `total_current(currency_service)` — total at the current rate;
- `fx_difference(currency_service)` — revaluation (`current - fixed`);
- `total()` — alias for `total_fixed()` (backward compatibility).

### Migration

Rules for migrating old formats:

- legacy `amount` -> `amount_original`;
- missing currency -> `KZT`;
- missing course -> `1.0`;
- missing `amount_kzt` -> calculated according to the import policy;
- invalid lines are skipped and included in the error list.

### Data storage

The data is stored in `records.json` at the root of the project.

Format:

```json
{
  "initial_balance": 50000.0,
  "records": [
    {
      "type": "income",
      "date": "2025-01-15",
      "amount_original": 700.0,
      "currency": "USD",
      "rate_at_operation": 500.0,
      "amount_kzt": 350000.0,
      "category": "Salary"
    },
    {
      "type": "expense",
      "date": "2025-01-16",
      "amount_original": 25000.0,
      "currency": "KZT",
      "rate_at_operation": 1.0,
      "amount_kzt": 25000.0,
      "category": "Products"
    },
    {
      "type": "mandatory_expense",
      "date": "2025-01-20",
      "amount_original": 300.0,
      "currency": "USD",
      "rate_at_operation": 500.0,
      "amount_kzt": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ],
  "mandatory_expenses": [
    {
      "date": "",
      "amount_original": 300.0,
      "currency": "USD",
      "rate_at_operation": 500.0,
      "amount_kzt": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ]
}
```

---

## 🌐 Web application

The web version is located in `web/` and runs entirely on the client (no server). The data is stored in the browser's `localStorage`.

Features:

- Separate sections for income, expenses, reports and settings.
- Built-in charts and dashboard.
- Support for rates of the National Bank of the Republic of Kazakhstan via RSS (`rates_all.xml`) with daily caching in `localStorage`.
- Export report to `CSV` (web version).

To run: Open `web/index.html` in a browser.

---

## 🏗️ Project architecture

The project follows a layered architecture:

- `domain/` — business models and rules (records, reports, validation of dates and periods, currencies).
- `app/` — use cases and currency service adapter.
- `infrastructure/` — data storage (JSON repository).
- `utils/` — import/export and preparation of data for graphs.
- `gui/` — GUI layer (Tkinter).
- `web/` — standalone web application.

Data flow for GUI:

- UI (Tkinter) → `app/use_cases.py` → `infrastructure/repositories.py` → `records.json`.

---

## 📝 Software API

Below are the key classes and functions synchronized with the actual code.

### Domain

`domain/currency.py`

- `CurrencyService` — conversion of currencies to base (`KZT`).

`domain/import_policy.py`

- `ImportPolicy` — import policy (enum).

`domain/records.py`

- `Record` — base record (abstract class).
- `IncomeRecord` — income.
- `ExpenseRecord` — expense.
- `MandatoryExpenseRecord` — mandatory expense with `description` and `period`.

`domain/reports.py`

- `Report(records, initial_balance=0.0)` — report.
- `total_fixed()` — total at the transaction rate (accounting mode).
- `total_current(currency_service)` — total at the current exchange rate.
- `fx_difference(currency_service)` — exchange rate difference.
- `total()` — alias `total_fixed()` for backwards compatibility.
- `opening_balance(start_date)` — computes period start balance: `initial_balance + all records with date < start_date`.
- `filter_by_period(prefix)` — filtering by date prefix.
- `filter_by_period_range(start_prefix, end_prefix)` — filtering by date range.
- `filter_by_category(category)` — filtering by category.
- `grouped_by_category()` — grouping by categories.
- `monthly_income_expense_rows(year=None, up_to_month=None)` — monthly aggregates.
- `monthly_income_expense_table(year=None, up_to_month=None)` — table by month.
- `as_table(summary_mode="full"|"total_only")` — tabular output.
- `to_csv(filepath)` and `from_csv(filepath)` — report export and backward-compatible import.

`domain/validation.py`

- `parse_ymd(value)` — parsing and validating the date `YYYY-MM-DD`.
- `ensure_not_future(date)` — prohibition of future dates.
- `ensure_valid_period(period)` — period validation.
- `parse_report_period_start(value)` — validates report period filter (`YYYY`/`YYYY-MM`/`YYYY-MM-DD`) and returns period start date while rejecting future dates.
- `parse_report_period_end(value)` — validates report period end (`YYYY`/`YYYY-MM`/`YYYY-MM-DD`) and returns period end date while rejecting future dates.

### Application

`app/services.py`

- `CurrencyService(rates=None, base="KZT", use_online=False)` - adapter for domain service.
- When `use_online=True` tries to load the rates of the National Bank of the Republic of Kazakhstan and caches them in `currency_rates.json`.

`app/use_cases.py`

- `CreateIncome.execute(date, amount, currency, category)`.
- `CreateExpense.execute(date, amount, currency, category)`.
- `GenerateReport.execute()` → `Report` taking into account the initial balance.
- `DeleteRecord.execute(index)`.
- `DeleteAllRecords.execute()`.
- `ImportFromCSV.execute(filepath)` — import and complete replacement of records (CSV, `ImportPolicy.FULL_BACKUP`).
- `CreateMandatoryExpense.execute(amount, currency, category, description, period)`.
- `GetMandatoryExpenses.execute()`.
- `DeleteMandatoryExpense.execute(index)`.
- `DeleteAllMandatoryExpenses.execute()`.
- `AddMandatoryExpenseToReport.execute(index, date)`.

### Infrastructure

`infrastructure/repositories.py`

- `RecordRepository` — repository interface.
- `JsonFileRecordRepository(file_path="records.json")` — JSON storage.

Methods:

- `save(record)`.
- `load_all()`.
- `delete_by_index(index)`.
- `delete_all()`.
- `save_initial_balance(balance)`.
- `load_initial_balance()`.
- `save_mandatory_expense(expense)`.
- `load_mandatory_expenses()`.
- `delete_mandatory_expense_by_index(index)`.
- `delete_all_mandatory_expenses()`.

### GUI

`gui/tkinter_gui.py`

- `FinancialApp` is the main application class with Tkinter.
- The `Reports` tab supports 2 summary modes:
  - `According to the course of the operation`
  - `At the current rate`
- The exchange rate difference is displayed as a separate line (`FX Difference`).
- Monthly aggregates and charts are always calculated in fixed mode (`amount_kzt`).

Methods:

- `infographics_tab(parent)`.
- `operations_tab(parent)`:
  - `save_record()`.
  - `delete_selected()`.
  - `delete_all()`.
  - `import_records()`.
  - `import_records_data()`.
  - `export_records_data()`.
- `reports_tab(parent)`.
  - `generate()`.
  - `export_any()`.
- `settings_tab(parent)`.
  - `save_balance()`.
  - `refresh_mandatory()`.
  - `add_mandatory_inline()`.
  - `add_to_report_inline()`.
  - `delete_mandatory()`.
  - `delete_all_mandatory()`.
  - `import_mand()`.
  - `export_mand()`.
  - `import_backup()`.
  - `export_backup()`.

`gui/exporters.py`

- `export_report(report, filepath, fmt)`.
- `export_mandatory_expenses(expenses, filepath, fmt)`.
- `export_records(records, filepath, fmt, initial_balance)`.
- `export_full_backup(filepath, initial_balance, records, mandatory_expenses)`.

`gui/importers.py`

- `import_records_from_csv(filepath, policy, currency_service)` -> `(records, initial_balance, (imported, skipped, errors))`.
- `import_records_from_xlsx(filepath, policy, currency_service)` -> `(records, initial_balance, (imported, skipped, errors))`.
- `import_mandatory_expenses_from_csv(filepath, policy, currency_service)` -> `(expenses, (imported, skipped, errors))`.
- `import_mandatory_expenses_from_xlsx(filepath, policy, currency_service)` -> `(expenses, (imported, skipped, errors))`.
- `import_full_backup(filepath)` -> `(initial_balance, records, mandatory_expenses, (imported, skipped, errors))`.

`gui/helpers.py`

- `open_in_file_manager(path)`.

### Utils

`utils/backup.py`

- `create_full_backup(filepath, initial_balance, records, mandatory_expenses)`.
- `load_full_backup(filepath)`.

`utils/csv_utils.py`

- `report_to_csv(report, filepath)`.
- `report_from_csv(filepath)`.
- `export_records_to_csv(records, filepath, initial_balance)`.
- `import_records_from_csv(filepath, policy, currency_service)`.
- `export_mandatory_expenses_to_csv(expenses, filepath)`.
- `import_mandatory_expenses_from_csv(filepath, policy, currency_service)`.

`utils/excel_utils.py`

- `report_to_xlsx(report, filepath)`.
- `report_from_xlsx(filepath)`.
- `export_records_to_xlsx(records, filepath, initial_balance)`.
- `import_records_from_xlsx(filepath, policy, currency_service)`.
- `export_mandatory_expenses_to_xlsx(expenses, filepath)`.
- `import_mandatory_expenses_from_xlsx(filepath, policy, currency_service)`.

`utils/pdf_utils.py`

- `report_to_pdf(report, filepath)`.

`utils/charting.py`

- `aggregate_expenses_by_category(records)`.
- `aggregate_daily_cashflow(records, year, month)`.
- `aggregate_monthly_cashflow(records, year)`.
- `extract_years(records)`.
- `extract_months(records)`.

---

## 📁 File structure

```
project/
│
├── main.py                     # Application entry point
├── records.json                # Record storage (created automatically)
├── currency_rates.json         # Currency rate cache (use_online=True)
├── requirements.txt            # Python dependencies
├── pytest.ini                  # pytest settings
├── pyproject.toml              # Project configuration
├── README.md                   # This documentation
├── README_EN.md                # Documentation in English
├── CHANGELOG.md                # History of changes
├── LICENSE                     # License
│
├── app/                        # Application layer
│   ├── __init__.py
│   ├── services.py             # CurrencyService adapter
│   └── use_cases.py            # Use cases
│
├── domain/                     # Domain layer
│   ├── __init__.py
│   ├── records.py              # Records
│   ├── reports.py              # Reports
│   ├── currency.py             # Domain CurrencyService
│   ├── wallets.py              # Wallets
│   ├── transfers.py            # Transfers
│   └── validation.py           # Validation of dates and periods
│
├── infrastructure/             # Infrastructure layer
│   └── repositories.py         # JSON repository
│
├── utils/                      # Import/export and graphs
│   ├── __init__.py
│   ├── backup_utils.py         # Backup of data
│   ├── import_core.py          # Import validator
│   ├── charting.py             # Graphs and Aggregations
│   ├── csv_utils.py
│   ├── excel_utils.py
│   └── pdf_utils.py
│
├── gui/                        # GUI layer (Tkinter)
│   ├── __init__.py
│   ├── tkinter_gui.py          # Main GUI application
│   ├── helpers.py              # Helpers for GUI
│   ├── controllers.py          # GUI controllers
│   ├── importers.py            # Import mandatory expenses, records and full backup
│   └── exporters.py            # Export reports, mandatory expenses and backup
│
├── web/                        # Web application
│   ├── __init__.py
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── tests/                      # Tests
    ├── __init__.py
    ├── test_charting.py
    ├── test_csv.py
    ├── test_currency.py
    ├── test_excel.py
    ├── test_gui_exporters_importers.py
    ├── test_import_policy_and_backup.py
    ├── test_pdf.py
    ├── test_records.py
    ├── test_reports.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_use_cases.py
    ├── test_validation.py
    ├── test_wallet_phase1.py
    └── test_wallet_phase2.py
```

---

## 🧪 Tests

### Launch

```bash
# Go to project directory
cd "FU Project/project"

# Run all tests
pytest

# With verbose output
pytest -v

# Specific file
pytest tests/test_records.py -v

# Specific test
pytest tests/test_reports.py::test_report_total -v
```

### Coverage

```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
pytest --cov=. --cov-report=html
```

> **Note:** The tests expect the `CurrencyService` to use local courses by default (parameter `use_online=False`).

---

## 💱 Supported currencies

Default application rates:

| Currency          | Code | Default rate | Description     |
| ----------------- | ---- | ------------ | --------------- |
| Kazakhstani tenge | KZT  | 1.0          | Base currency   |
| US dollar         | USD  | 500.0        | 1 USD = 500 KZT |
| Euro              | EUR  | 590.0        | 1 EUR = 590 KZT |
| Russian ruble     | RUB  | 6.5          | 1 RUB = 6.5 KZT |

If you create `CurrencyService(use_online=True)`, then the rates will be downloaded from the National Bank of the Republic of Kazakhstan and saved in `currency_rates.json`.

---

## 📄 License

MIT License — free to use, modify and distribute.
