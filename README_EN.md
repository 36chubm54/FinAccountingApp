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

# Install runtime dependencies
pip install -r requirements.txt

# Install dev dependencies (tests, coverage)
pip install -r requirements-dev.txt
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
- `Operations` — management of records and transfers (adding, deleting, importing/exporting).
- `Reports` — report generation, export.
- `Settings` — management of mandatory expenses and wallets.

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

### Adding a translation

1. Open the `Operations` tab.
2. In the `Add transfer` block, select the transfer type (`Transfer`).
3. Enter the date in the format `YYYY-MM-DD` (the date cannot be in the future).
4. Enter the amount.
5. Specify the source and recipient of the wallets.
6. Click `Save`.

### Deleting an entry

1. Open the `Operations` tab.
2. Select an entry from the list.
3. Click `Delete Selected`. A deletion message appears with the index of the entry or ID of the transfer.

### Delete all entries

1. Open the `Operations` tab.
2. In the `List of operations` block, select an entry from the list.
3. Click `Delete All Records` and confirm the deletion. The entries will be permanently deleted and the list of entries will be updated.

### Inline amount_kzt edit

1. Open the `Operations` tab.
2. Select a record in the list.
3. Click `Edit Amount KZT`.
4. Enter a new value and click `Save`.

The update is applied through the immutable domain model: a new record instance is created and `rate_at_operation` is recalculated automatically. Transfer-linked records cannot be edited.

### Report generation

1. Open the `Reports` tab.
2. Enter filters (optional):
    - `Period` — period start (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`).
    - `Period end` — period end (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`).
    - `Category` — filter by category.
3. Choose one wallet for generating the report on it or all wallets.
4. Enable options:
    - `Group by category` — grouping by category.
    - `Display as table` — table format.
5. Click `Generate`.

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

### Managing mandatory expenses

In the `Settings` tab, in the `Mandatory Expenses` block, the following operations are available:

- `Add` — add a mandatory expense.
- `Delete` — delete the selected one.
- `Delete All` — delete everything.
- `Add to Records` — add the selected expense to records with the specified date.
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

- `CSV`, `XLSX`.
- All existing entries are replaced with data from the file.

Data format:

- **CSV/XLSX data (import/export):**  
  `date,type,wallet_id,category,amount_original,currency,rate_at_operation,amount_kzt,description,period,transfer_id,from_wallet_id,to_wallet_id`.
- `wallet_id` — identifier of the wallet in which the operation was made.
- `transfer_id` — identifier of the transfer between wallets.
- `from_wallet_id` — identifier of the source wallet in a transfer.
- `to_wallet_id` — identifier of the target wallet in a transfer.
- Legacy import is supported (old files with the `amount` field or the `Amount (KZT)` column).
- All existing entries are replaced with data from the file.

Important:

- `CSV/XLSX report` and `CSV/XLSX data` are different formats.
- Report `CSV/XLSX` is read-only by the user and **should not** be used as a data source for import.

### ImportPolicy

There are 3 modes available for importing records:

- `Full Backup` (`ImportPolicy.FULL_BACKUP`)  
  Used for full import with a fixed transaction rate. Expected string format:
  `date,type,wallet_id,category,amount_original,currency,rate_at_operation,amount_kzt,description,period,transfer_id,from_wallet_id,to_wallet_id`.
- `Current Rate` (`ImportPolicy.CURRENT_RATE`)  
  For each imported line, the rate is taken at the time of import through `CurrencyService.get_rate(currency)`, and `rate_at_operation` and `amount_kzt` are recalculated and fixed again.
- `Legacy Import` (`ImportPolicy.LEGACY`)
  The old `date,type,category,amount` format is automatically migrated to the new one:
  `currency="KZT"`, `rate_at_operation=1.0`, `amount_kzt=amount`.

All modes perform line-by-line validation and generate a report:
`(imported, skipped, errors)`.

### Backup

Full backup is implemented in `JSON` format:

- Fields: `wallets`, `records`, `mandatory_expenses` and `transfers`.
- The `Settings` tab contains the following buttons:
  - `Export Full Backup`
  - `Import Full Backup`

Backup restores:

- wallets with fields `id/name/currency/balance`;
- all records with fields `type/date/wallet_id/transfer_id/category/amount_original/currency/rate_at_operation/amount_kzt/category/description`;
- all mandatory expenses with `description/period`;
- all transfers between wallets.

### FX Revaluation

`Report` supports:

- `net_worth_fixed()` — net asset value at the time of recording;
- `net_worth_current()` — net asset value at the current rate;
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

Current primary storage is JSON (`data.json`).
To prepare JSON->SQLite migration, a dedicated `storage/` layer was added:

- `storage/base.py` — `Storage` contract (data-access operations only).
- `storage/json_storage.py` — `JsonStorage` adapter over the current JSON implementation.
- `storage/sqlite_storage.py` — `SQLiteStorage` based on standard `sqlite3`.
- `db/schema.sql` — SQL schema for `wallets`, `records`, `transfers`, `mandatory_expenses`.

Domain models and service-layer business logic remain unchanged.

### JSON -> SQLite migration

Use `migrate_json_to_sqlite.py` for safe data migration.

Run examples:

```bash
# Validation only, no write
python migrate_json_to_sqlite.py --dry-run

# Full migration
python migrate_json_to_sqlite.py --json-path data.json --sqlite-path finance.db
```

What the script does:

- loads source data via `JsonStorage`;
- writes to SQLite in one explicit transaction with strict order:
  `wallets -> transfers -> records -> mandatory_expenses`;
- preserves existing `id` values (or builds `old_id -> new_id` mapping when ids are auto-generated);
- validates integrity and compares balances/`net worth`;
- performs `rollback` on any error or mismatch.
- is safe to rerun: if SQLite already has an equivalent dataset, migration is skipped without failure.

### Primary storage configuration

`config.py` controls the storage source:

- `USE_SQLITE = True`
- `SQLITE_PATH = "finance.db"`
- `JSON_PATH = "data.json"`

Paths in `config.py` and default values in `migrate_json_to_sqlite.py`
are resolved relative to the `project` directory, so `finance.db` and `data.json` are created inside `project` even when launched from another folder, and `data_backup_*.json` are created inside `project/backups/` (the folder is created automatically).

Initialization is handled by `bootstrap.py`:

- with `USE_SQLITE=True`, SQLite is selected as primary storage;
- if SQLite is empty, a one-time migration from JSON is executed;
- if SQLite already has data, repeated migration is blocked;
- on each startup a JSON backup is created (`data_backup_YYYYMMDD_HHMMSS.json`);
- startup integrity validation runs (counts + net worth), mismatch triggers emergency mode;
- reverse export SQLite -> JSON is available via `backup.export_to_json`.

Format:

```json
{
  "records": [
    {
      "id": 1,
      "type": "income",
      "date": "2025-01-15",
      "amount_original": 700.0,
      "currency": "USD",
      "rate_at_operation": 500.0,
      "amount_kzt": 350000.0,
      "category": "Salary"
    },
    {
      "id": 2,
      "type": "expense",
      "date": "2025-01-16",
      "amount_original": 25000.0,
      "currency": "KZT",
      "rate_at_operation": 1.0,
      "amount_kzt": 25000.0,
      "category": "Products"
    },
    {
      "id": 3,
      "type": "mandatory_expense",
      "date": "2025-01-20",
      "amount_original": 300.0,
      "currency": "USD",
      "rate_at_operation": 500.0,
      "amount_kzt": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    },
    {
      "id": 4,
      "type": "expense",
      "date": "2026-02-20",
      "wallet_id": 1,
      "transfer_id": 1,
      "amount_original": 5000.0,
      "currency": "KZT",
      "rate_at_operation": 1.0,
      "amount_kzt": 5000.0,
      "category": "Transfer"
    },
    {
      "id": 5,
      "type": "income",
      "date": "2026-02-20",
      "wallet_id": 2,
      "transfer_id": 1,
      "amount_original": 5000.0,
      "currency": "KZT",
      "rate_at_operation": 1.0,
      "amount_kzt": 5000.0,
      "category": "Transfer"
    }
  ],
  "mandatory_expenses": [
    {
      "id": 1,
      "date": "",
      "amount_original": 300.0,
      "currency": "USD",
      "rate_at_operation": 500.0,
      "amount_kzt": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ],
  "transfers": [
    {
      "id": 1,
      "from_wallet_id": 1,
      "to_wallet_id": 2,
      "date": "2026-02-20",
      "amount_original": 5000.0,
      "currency": "KZT",
      "rate_at_operation": 1.0,
      "amount_kzt": 5000.0,
      "description": ""
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

- `domain/` — business models and rules (records, reports, date/period validation, currencies, wallets, transfers).
- `app/` — use cases and currency service adapter.
- `infrastructure/` — data storage (JSON repository).
- `infrastructure/` — JSON and SQLite `RecordRepository` implementations.
- `storage/` — storage abstraction and JSON/SQLite adapters.
- `db/` — SQLite SQL schema.
- `bootstrap.py` — storage selection, migration and startup validation.
- `backup.py` — JSON backup and SQLite -> JSON export.
- `config.py` — storage flag and paths.
- `utils/` — import/export and preparation of data for graphs.
- `gui/` — GUI layer (Tkinter).
- `web/` — standalone web application.

Data flow for GUI:

- UI (Tkinter) → `gui/controllers.py` → `app/use_cases.py` → `infrastructure/repositories.py` → `data.json`.

Domain relationships:

- `Record` belongs to `Wallet` through `record.wallet_id`.
- `Transfer` links two records (`expense`/`income`) through `transfer_id`.
- Transfer commission is stored as a separate `Expense` (`Commission` category) and is not part of the linked transfer record pair.

### Immutable Domain Model

- `Record` is immutable (`@dataclass(frozen=True)`), including the `id` field.
- Any record update creates a new object instead of mutating the existing one.
- Amount edits use `with_updated_amount_kzt(new_amount_kzt)`.
- This protects financial data integrity and prepares the architecture for SQLite migration.

---

## 📝 Software API

Below are the key classes and functions synchronized with the actual code.

### Domain

`domain/currency.py`

- `CurrencyService` — conversion of currencies to base (`KZT`).

`domain/errors.py`

- `DomainError` — domain error (thrown when domain invariants are violated).

`domain/import_policy.py`

- `ImportPolicy` — import policy (enum).

`domain/records.py`

- `Record` — base record (abstract class). It includes mandatory `wallet_id` and optional `transfer_id`.
- `Record.id` — mandatory record identifier.
- `Record.with_updated_amount_kzt(new_amount_kzt)` — returns a new record instance with recalculated `rate_at_operation`.
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
- `sorted_by_date()` — sorting by date.
- `net_profit_fixed()` — net profit at fixed exchange rates.
- `monthly_income_expense_rows(year=None, up_to_month=None)` — monthly aggregates.
- `monthly_income_expense_table(year=None, up_to_month=None)` — table by month.
- `as_table(summary_mode="full"|"total_only")` — tabular output.
- `to_csv(filepath)` and `from_csv(filepath)` — report export and backward-compatible import.

`domain/wallets.py`

- `Wallet` — wallet (`allow_negative`, `is_active`).

`domain/transfers.py`

- `Transfer` — wallet-to-wallet transfer aggregate.

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

- `CreateIncome.execute(date, wallet_id, amount, currency, category)`.
- `CreateExpense.execute(date, wallet_id, amount, currency, category)`.
- `GenerateReport.execute(wallet_id=None)` → `Report` taking into account the initial balance.
- `CreateWallet.execute(name, currency, initial_balance, allow_negative=False)` — creating a new wallet.
- `GetWallets.execute()` — all wallets.
- `GetActiveWallets.execute()` — active wallets only.
- `SoftDeleteWallet.execute(wallet_id)` — safe wallet soft delete.
- `CalculateWalletBalance.execute(wallet_id)` — calculating wallet balance.
- `CalculateNetWorth.execute_fixed()` — calculating net worth at fixed exchange rates.
- `CalculateNetWorth.execute_current()` — calculating net worth at current exchange rates.
- `CreateTransfer.execute(from_wallet_id, to_wallet_id, transfer_date, amount_original, currency, description, comission_amount, comission_currency)` — creating a transfer between wallets.
- `DeleteTransfer.execute(transfer_id)` — atomic cascade deletion of a transfer aggregate.
- `DeleteRecord.execute(index)`.
- `DeleteAllRecords.execute()`.
- `ImportFromCSV.execute(filepath)` — import and complete replacement of records (CSV, `ImportPolicy.FULL_BACKUP`).
- `CreateMandatoryExpense.execute(amount, currency, category, description, period)`.
- `GetMandatoryExpenses.execute()`.
- `DeleteMandatoryExpense.execute(index)`.
- `DeleteAllMandatoryExpenses.execute()`.
- `AddMandatoryExpenseToReport.execute(index, date)`.

`app/record_service.py`

- `RecordService.update_amount_kzt(record_id, new_amount_kzt)` — safe amount update via immutable domain objects and repository replace.

### Infrastructure

`infrastructure/repositories.py`

- `RecordRepository` — repository interface.
- `JsonFileRecordRepository(file_path="data.json")` — JSON storage.

`infrastructure/sqlite_repository.py`

- `SQLiteRecordRepository(db_path="finance.db")` — SQLite `RecordRepository` implementation used by service layer.

`storage/base.py`

- `Storage` — minimal storage contract (`get/save` for wallets/records/transfers and `get` for mandatory expenses).

`storage/json_storage.py`

- `JsonStorage(file_path="data.json")` — wrapper over the existing JSON implementation, compatible with the current codebase.

`storage/sqlite_storage.py`

- `SQLiteStorage(db_path="records.db")` — SQLite adapter based on `sqlite3`, including:
  - `PRAGMA foreign_keys = ON`;
  - `PRAGMA journal_mode = WAL`;
  - domain object read/write mapping without business-logic duplication.

`db/schema.sql`

- Database schema with tables `wallets`, `records`, `transfers`, `mandatory_expenses`, constraints, and indexes.

### GUI

`gui/tkinter_gui.py`

- `FinancialApp` is the main application class with Tkinter.

`gui/tabs/infographics_tab.py`

- `InfographicsTabBindings` — class for binding events to interface elements of the `Infographics` tab.
- `build_infographics_tab(parent, on_chart_filter_change, on_refresh_charts, on_legend_mousewheel, bind_all, after, after_cancel)` — method for building the interface of the `Infographics` tab. This tab displays charts and summaries of financial data.

`gui/tabs/operations_tab.py`

- `OperationsTabContext` — the context of the operations tab.
- `OperationsTabBindings` — class for binding events to interface elements of the `Operations` tab.
- `build_operations_tab(parent, context, import_formats)` — method for building the interface of the `Operations` tab. This tab supports adding and deleting records, as well as editing currency values ​​with mathematical conversion of the exchange rate. Also supports the creation of translations import/export records.

`gui/tabs/reports_tab.py`

- `ReportTabContext` — report tab context.
- `build_reports_tab(parent, context)` — method for building the interface of the `Reports` tab. This tab supports 2 summary modes:
  - `According to the course of the operation`
  - `At the current rate`
- The exchange rate difference is displayed as a separate line (`FX Difference`).
- Monthly aggregates and charts are always calculated in fixed mode (`amount_kzt`).

`gui/tabs/settings_tab.py`

- `SettingsTabContext` — context of the settings tab.
- `build_settings_tab(parent, context, import_formats)` — method for building the interface of the `Settings` tab. This tab allows you to manage wallets and mandatory expenses.

`gui/controllers`

- `FinanceController` — class for managing the business logic of the application.

`gui/exporters.py`

- `export_report(report, filepath, fmt)`.
- `export_mandatory_expenses(expenses, filepath, fmt)`.
- `export_records(records, filepath, fmt, initial_balance=0.0, transfers=None)`.
- `export_full_backup(filepath, wallets, records, mandatory_expenses, transfers, initial_balance=0.0)`.

`gui/importers.py`

- `import_records_from_csv(filepath, policy, currency_service, wallet_ids)` -> `(records, initial_balance, (imported, skipped, errors))`.
- `import_records_from_xlsx(filepath, policy, currency_service, wallet_ids)` -> `(records, initial_balance, (imported, skipped, errors))`.
- `import_mandatory_expenses_from_csv(filepath, policy, currency_service)` -> `(expenses, (imported, skipped, errors))`.
- `import_mandatory_expenses_from_xlsx(filepath, policy, currency_service)` -> `(expenses, (imported, skipped, errors))`.
- `import_full_backup(filepath)` -> `(wallets, records, mandatory_expenses, transfers, (imported, skipped, errors))`.

`gui/helpers.py`

- `open_in_file_manager(path)`.

### Utils

`utils/backup.py`

- `export_full_backup_to_json(filepath, wallets, records, mandatory_expenses, transfers, initial_balance=0.0)`.
- `import_full_backup_from_json(filepath)`.

`utils/csv_utils.py`

- `report_to_csv(report, filepath)`.
- `report_from_csv(filepath)`.
- `export_records_to_csv(records, filepath, initial_balance=0.0, transfers=None)`.
- `import_records_from_csv(filepath, policy, currency_service, wallet_ids=None)`.
- `export_mandatory_expenses_to_csv(expenses, filepath)`.
- `import_mandatory_expenses_from_csv(filepath, policy, currency_service)`.

`utils/excel_utils.py`

- `report_to_xlsx(report, filepath)`.
- `report_from_xlsx(filepath)`.
- `export_records_to_xlsx(records, filepath, initial_balance=0.0, transfers=None)`.
- `import_records_from_xlsx(filepath, policy, currency_service, wallet_ids=None)`.
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

`utils/import_core.py`

- `norm_key(value)`.
- `as_float(value, default=None)`.
- `safe_type(value)`.
- `record_type_name(record)`.
- `parse_import_row(row, row_label, policy, get_rate, mandatory_only)`.

---

## 📁 File structure

```text
project/
│
├── main.py                     # Application entry point
├── config.py                   # Storage configuration (SQLite/JSON)
├── bootstrap.py                # Storage selection + startup migration/validation
├── backup.py                   # JSON backup and SQLite -> JSON export
├── migrate_json_to_sqlite.py   # Data migration from JSON to SQLite
├── data.json                # Record storage (created automatically)
├── currency_rates.json         # Currency rate cache (use_online=True)
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Dev dependencies (tests, coverage)
├── pytest.ini                  # pytest settings
├── pyproject.toml              # Project configuration
├── README.md                   # This documentation
├── README_EN.md                # Documentation in English
├── CHANGELOG.md                # History of changes
├── LICENSE                     # License
│
├── app/                        # Application layer
│   ├── __init__.py
│   ├── record_service.py       # Service for records
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
│   ├── validation.py           # Validation of dates and periods
│   ├── errors.py               # Application errors 
│   └── import_policy.py        # Import policies
│
├── infrastructure/             # Infrastructure layer
│   ├── repositories.py         # JSON repository
│   └── sqlite_repository.py    # SQLite repository
│
├── storage/                    # Storage abstraction and JSON/SQLite adapters
│   ├── __init__.py
│   ├── base.py
│   ├── json_storage.py
│   └── sqlite_storage.py
│
├── db/                         # SQL schema for SQLite
│   └── schema.sql
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
│   ├── tabs/
│   │   ├── infographics_tab.py # Tab with infographics
│   │   ├── operations_tab.py   # Tab with operations and transfers
│   │   ├── reports_tab.py      # Tab with reports
│   │   └── settings_tab.py     # Tab with wallets and mandatory expenses
│   │
│   ├── __init__.py
│   ├── tkinter_gui.py          # Main GUI application
│   ├── helpers.py              # Helpers for GUI
│   ├── controllers.py          # GUI controllers
│   ├── importers.py            # Import mandatory expenses, records and full backup
│   └── exporters.py            # Export reports, mandatory expenses and backup
│
├── web/                        # Web application
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
    ├── test_import_balance_contract.py
    ├── test_bootstrap_backup.py
    ├── test_migrate_json_to_sqlite.py
    ├── test_import_core.py
    ├── test_import_policy_and_backup.py
    ├── test_import_security.py
    ├── test_pdf.py
    ├── test_records.py
    ├── test_reports.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_use_cases.py
    ├── test_validation.py
    ├── test_transfer_integrity.py
    ├── test_wallet_phase1.py
    ├── test_wallet_phase2.py
    ├── test_wallet_phase3.py
    ├── test_phase33_immutable_repo_service.py
    └── test_phase4_import_export.py
```

---

## 🧪 Tests

### Launch

```bash
# Go to project directory
cd "FU Project/project"

# Install dev dependencies (if not installed yet)
pip install -r requirements-dev.txt

# Run all tests (inside activated venv)
python -m pytest

# With verbose output
python -m pytest -v

# Specific file
python -m pytest tests/test_records.py -v

# Specific test
python -m pytest tests/test_reports.py::test_report_total -v
```

### Coverage

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=. --cov-report=term-missing
python -m pytest --cov=. --cov-report=html
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
