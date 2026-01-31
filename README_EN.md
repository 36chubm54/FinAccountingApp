# FinAccountingApp

A graphical application for personal financial accounting with support for multi-currency, categorization and analytical reports.

## 📋 Contents

- [Quick start](#-quick-start)
- [Using the application](#️-using-the-application)
- [Web application](#-web-application)
- [Project architecture](#️-project-architecture)
- [Software API](#-software-api)
- [File structure](#-file-structure)
- [Tests](#-tests)

---

## 🚀 Quick start

### System requirements

- Python 3.10 or higher
- pip (package manager)

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

After launch, the graphical window of the Financial Accounting application will open. Use buttons to add income and expenses, generate reports, and delete entries.

---

## 🖥️ Using the application

### Main window

After running `python main.py`, a window with nine buttons will open:

- **Add Income** - Adding income
- **Add Expense** - Adding an expense
- **Generate Report** — Report generation
- **Delete Record** - Delete a record
- **Delete All Records** - Delete all records
- **Set Initial Balance** — Setting the initial balance
- **Manage Mandatory** - Management of mandatory expenses
- Format selector for import/export (CSV, XLSX, PDF)
- **Import** — Import data from a file of the selected format (CSV, XLSX, PDF)

### Adding income/expense

1. Click "Add Income" or "Add Expense".
2. Enter the date in YYYY-MM-DD format (for example, 2025-01-15).
3. Enter the amount (floating point number).
4. Enter the currency (default KZT). Supported any currency (USD, EUR, RUB, etc.).
5. Enter a category (default is "General").
6. Click OK.

The amount is automatically converted into the base currency (KZT) at the current rate.

### Report generation

1. Click "Generate Report".
2. In the new window, enter filters (optional):
   - **Period**: Filter by period (for example, 2025-01 for January 2025).
   - **Category**: Filter by category.
3. Set checkboxes:
   - **Group by category**: Grouping totals by category.
   - **Display as table**: Output in table format.
4. Click "Generate".

The result will be displayed in the text field. For tables, a formatted table with a total is used.

Additionally: in the report generation window, the **Export** button is available to save the report in any available format. The file contains the `Report` sheet with the `Date, Type, Category, Amount (KZT)` columns. If an initial balance is specified, it is written on a separate line with `Type = Initial Balance`.

### Deleting an entry

1. Click "Delete Record".
2. In the list, select the entry to be deleted (by clicking the mouse).
3. Click "Delete Selected".
4. Confirm the deletion in the dialog box.

### Setting the initial balance

1. Click "Set Initial Balance".
2. Enter the amount of the initial balance (floating point number, can be negative).
3. Click OK.
4. The opening balance will be saved and will be taken into account in balance calculations.

The opening balance is the balance at the beginning of the accounting period. It is added to the final balance of all entries.

### Managing mandatory expenses

1. Click "Manage Mandatory".
2. A list of existing mandatory expenses will be displayed in a new window.
3. Use the buttons:
   - Format selector for import/export (CSV, XLSX, PDF)
   - **Add** — Add a new mandatory expense
   - **Delete** — Delete the selected mandatory expense
   - **Delete All** - Delete all mandatory expenses
   - **Add to Report** — Add the selected expense to the report indicating the date
   - **Import** — Import mandatory expenses from a file of the selected format (CSV, XLSX)
   - **Export** — Export mandatory expenses to a file of the selected format (CSV, XLSX, PDF)
   - **Close** — Close the window

**Adding mandatory expense:**

1. Click "Add" in the control window.
2. Fill in the fields:
   - **Amount** — Amount (floating point number)
   - **Currency** — Currency (default KZT)
   - **Category** — Category (default "Mandatory")
   - **Description** — Description of consumption (required)
   - **Period** — Periodicity (daily/weekly/monthly/yearly)
3. Click "Save".

**Add to report:**

1. Select a required expense from the list.
2. Click "Add to Report".
3. Enter the date in YYYY-MM-DD format.
4. Click OK.

Mandatory expenses are recurring expenses (rent, utilities, etc.). They are stored separately and can be added to the report at any time.

### Delete all entries

1. Click "Delete All Records".
2. Confirm deletion in the dialog box (this action is irreversible).
3. All financial records will be removed from the `records.json` file. The opening balance will remain unchanged.

### Import from CSV

1. Select "CSV" from the import format drop-down list in the main window.
2. Click "Import".
3. Select the CSV file in the open file dialog box.
4. Confirm the import in the dialog box (all existing entries will be replaced).
5. The application will show the number of successfully imported records.

**CSV file format:**

```csv
Date,Type,Category,Amount (KZT)
,Initial Balance,,50000.00
2025-01-01,Income,Salary,100000.00
2025-01-02,Expense,Food,15000.00
2025-01-03,Income,Bonus,50000.00
SUBTOTAL,,,135000.00
FINAL BALANCE,,,185000.00
```

### Import from XLSX

1. Select "XLSX" from the import format drop-down list in the main window.
2. Click "Import".
3. Select the `.xlsx` file in the open file dialog box.
4. Confirm the import (all existing entries will be replaced).
5. The application will show the number of imported records.

XLSX file format:

- Sheet: `Report`
- Columns: `Date`, `Type`, `Category`, `Amount (KZT)` (first row as headers)
- Initial balance can be specified as a row with empty `Date` and `Type = Initial Balance`.

Import rules follow CSV rules: invalid rows are skipped; supported types are `Income`, `Expense`, and `Mandatory Expense`.

**Import rules:**

- The first line should contain the headings: `Date,Type,Category,Amount (KZT)`
- The second line may contain the initial balance `Initial Balance` with empty fields `Type` and `Category`
- Dates must be in the format `YYYY-MM-DD`
- All delimiters are commas
- Supported types: `Income` (income) and `Expense` (expense)
- Amounts can be either positive or negative (in brackets for expenses)
- Lines with `SUBTOTAL` and `FINAL BALANCE` in the date field are ignored
- All existing data will be replaced with new data from the file

### Import/Export of mandatory expenses

#### Export mandatory expenses

1. Click "Manage Mandatory" to open the window for managing mandatory expenses.
2. Select the format you need (CSV, XLSX or PDF) and click "Export".
3. Select a save location and file name in the dialog box.
4. The application exports all mandatory expenses in the selected format.
5. The folder with the saved file will open automatically.

**XLSX format for mandatory expenses:**

- Sheet: `Mandatory`
- Columns: `Amount (KZT)`, `Category`, `Description`, `Period` (first line - headings)

**CSV file format for mandatory expenses:**

```csv
Amount (KZT),Category,Description,Period
150000.00,Rent,Monthly rent payment,monthly
50000.00,Utilities,Electricity and water,monthly
20000.00,Internet,Home internet connection,monthly
```

> **Note:** The PDF format for mandatory expenses is similar to CSV.

#### Import mandatory expenses

1. Click "Manage Mandatory" to open the window for managing mandatory expenses.
2. Select the desired format (CSV or XLSX) and click "Import".
3. Select a file of the selected format with mandatory expenses in the dialog box.
4. Confirm import (all existing mandatory charges will be replaced).
5. The application will import the data and update the list of required expenses.

**Rules for importing mandatory expenses:**

- The first line should contain the headings: `Amount (KZT),Category,Description,Period`
- Supported periods: `daily`, `weekly`, `monthly`, `yearly`
- Amounts must be numeric values
- Description is a required field
- Incorrectly formatted lines will be skipped
- All existing mandatory expenses will be replaced with imported data

#### Import CSV for mandatory expenses

1. Select `CSV` format from the import format drop-down list in the Mandatory Expense Management window.
2. Click "Import".
3. Select the `.csv` file and confirm the import (all existing mandatory expenses will be replaced).
4. The file must contain the columns `Amount (KZT), Category, Description, Period`.
5. Supported periods: `daily`, `weekly`, `monthly`, `yearly`.

#### Import XLSX for mandatory expenses

1. Select `XLSX` format from the import format drop-down list in the Mandatory Expense Management window.
2. Click "Import".
3. Select the `.xlsx` file and confirm the import (all existing mandatory expenses will be replaced).
4. The file must contain the `Mandatory` sheet and the `Amount (KZT), Category, Description, Period` columns.
5. Supported periods: `daily`, `weekly`, `monthly`, `yearly`.

Invalid rows will be skipped; valid rows will replace the current mandatory expenses list.

### Additions: PDF and unified Import/Export UI

- The application now supports exporting reports and mandatory expenses in `PDF` format. PDF files created by the application contain tables, with corresponding columns and headings.
- The UI replaces separate import/export buttons with a format dropdown (`CSV`, `XLSX`, `PDF`) and a single `Import` / `Export` button in the main window, the Generate Report window, and the Manage Mandatory window.

**Usage example:**

```csv
Amount (KZT),Category,Description,Period
100000.00,Mandatory,Apartment rent,monthly
30000.00,Mandatory,Electricity bill,monthly
15000.00,Mandatory,Internet subscription,monthly
5000.00,Mandatory,Mobile phone plan,monthly
```

> **Note:** Import/export of statutory expenses works independently of the main import/export of financial records. This allows you to manage mandatory expenses separately from your main financial transactions.

### Data storage

All records are saved in the `records.json` file in the project directory. The file is created automatically upon first launch.

**File format:**

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
      "category": "Products"
    }
  ],
  "mandatory_expenses": [
      {
      "date": "2025-01-01",
      "amount": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent payment",
      "period": "monthly"
      }
  ]
}
```

The `initial_balance` field stores the initial balance (balance at the beginning of the accounting period). If not set, equals 0.0.

---

## 🌐 Web application

The project includes a web version of an application for managing finances in a browser.

### 🚀 Launching a web application

```bash
# Go to the web application directory
cd "FU Project/project/web"

# Start a local server (e.g. using Python)
python -m http.server 8000

# Or use any other web server
# Open your browser and go to: http://localhost:8000
```

### 🎯 Main features

#### 📊 Review (Dashboard)

- Statistics of income, expenses and balance
- Display of recent transactions
- Switching display currency (KZT, USD, EUR, RUB)
- Automatic downloading of current exchange rates from the National Bank of the Republic of Kazakhstan

#### 💵 Revenue management

- Adding income with date, amount, currency and category
- Table of all incomes with the ability to delete
- Sort by date (newest on top)

#### 💸 Expense management

- Similar to income, but for expenses
- Visual highlighting of negative amounts

#### 📈 Reports

- Filtering by period (month/year)
- Filter by category
- Grouping data by category
- Export reports to CSV, XLSX, PDF formats
- Tables with totals

#### ⚙️Settings

- Select a theme (light/dark)
- Set default currency
- Clear all data

### 🛠️ Technical features

#### Storing data in a web application

- All data is stored in the browser's **localStorage**
- No need for a database or server
- Data is saved between sessions

#### Exchange rates

- Automatic download from the API of the National Bank of Kazakhstan
- Caching courses for 24 hours
- Manual update of courses
- Support for currencies: KZT, USD, EUR, RUB

#### Responsive design

- Works on desktop and mobile devices
- Collapsible sidebar on mobile
- Dark and light themes

#### Interface

- Modern Single Page Application (SPA)
- Smooth transition animations
- Modal windows for forms
- Notification system (toast)
- Icons and visual indicators

### 📁 Web application structure

```
web/
│
├── index.html # HTML application structure
├── styles.css # Styles and themes
└── app.js # Application logic in JavaScript
```

### 🌍 Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ JavaScript support
- Works without the Internet (except for downloading exchange rates)

---

## 🏗️ Project architecture

The project follows the principles of **Clean Architecture**:

```
┌────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                         │
│                        main.py (GUI)                           │
│             Graphical user interface on Tkinter                │
├────────────────────────────────────────────────────────────────┤
│                      APPLICATION LAYER                         │
│                      app/use_cases.py                          │
│    CreateIncome, CreateExpense, GenerateReport, DeleteRecord   │
│                      ImportFromCSV etc.                        │
│                       app/services.py                          │
│         CurrencyService (adapter with course caching)          │
├────────────────────────────────────────────────────────────────┤
│                        DOMAIN LAYER                            │
│    domain/records.py - Record, IncomeRecord, ExpenseRecord     │
│        domain/reports.py - Report (filtering, grouping)        │
│       domain/currency.py - CurrencyService (conversion)        │
├────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE LAYER                        │
│              infrastructure/repositories.py                    │
│   RecordRepository (abstraction), JsonFileRecordRepository     │
├────────────────────────────────────────────────────────────────┤
│                         UTILITIES                              │
│           utils/csv_utils.py   (import/export CSV)             │
│           utils/excel_utils.py (import/export XLSX)            │
│           utils/pdf_utils.py   (import/export PDF)             │
└────────────────────────────────────────────────────────────────┘
```

### Principles

1. **Dependency Inversion** - the upper layers depend on abstractions, not on concrete implementations
2. **Single Responsibility** - each class is responsible for one task
3. **Immutability** - Records are immutable (`frozen=True`)

## 📝 Software API

### Domain models

#### Record, IncomeRecord, ExpenseRecord, MandatoryExpenseRecord

File: [`domain/records.py`](domain/records.py)

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Literal


@dataclass(frozen=True)
class Record(ABC):
    """Base class of financial record (immutable)."""
    date: str # Format: "YYYY-MM-DD"
    amount: float # Amount in base currency (KZT)
    category: str # Custom category

    @abstractmethod
    def signed_amount(self) -> float:
        """Amount with the sign: + for income, - for expenses."""
        pass


class IncomeRecord(Record):
    """Record of income."""
    def signed_amount(self) -> float:
        return self.amount


class ExpenseRecord(Record):
    """Record of expense."""
    def signed_amount(self) -> float:
        return -abs(self.amount)


@dataclass(frozen=True)
class MandatoryExpenseRecord(Record):
    description: str
    period: Literal["daily", "weekly", "monthly", "yearly"]

    def signed_amount(self) -> float:
        return -abs(self.amount)
```

**Usage:**

```python
from domain.records import IncomeRecord, ExpenseRecord, MandatoryExpenseRecord

# Create entries
salary = IncomeRecord(
    date="2025-01-15",
    amount=350000.0,
    category="Salary"
)

groceries = ExpenseRecord(
    date="2025-01-16",
    amount=25000.0,
    category="Products"
)

rent = MandatoryExpenseRecord(
    date="2025-01-01",
    amount=150000.0,
    category="Mandatory",
    description="Monthly rent payment",
    period="monthly"
)

# Get signed sum
print(salary.signed_amount()) # 350000.0
print(groceries.signed_amount()) # -25000.0
print(rent.signed_amount()) # -150000.0

# Entries are immutable (frozen=True)
# salary.amount = 400000 # Error: FrozenInstanceError
```

---

### Currency conversion

#### CurrencyService (Domain)

File: [`domain/currency.py`](domain/currency.py)

```python
class CurrencyService:
    """Service for converting currencies into base (KZT)."""
    
    def __init__(self, rates: dict[str, float], base: str = "KZT"):
        """
        Args:
            rates: Dictionary of rates {currency_code: rate_to_base}
            base: Base currency code
        """
        self._rates = rates
        self._base = base

    def convert(self, amount: float, currency: str) -> float:
        """Converts the amount to the base currency."""
        if currency == self._base:
            return amount
        return amount * self._rates[currency]
```

**Usage:**

```python
from domain.currency import CurrencyService

# Initialization with courses
rates = {
    "USD": 500.0,   # 1 USD = 500 KZT
    "EUR": 600.0,   # 1 EUR = 600 KZT
    "RUB": 5.6      # 1 RUB = 5.6 KZT
}
converter = CurrencyService(rates=rates, base="KZT")

# Conversion
usd_amount = converter.convert(100, "USD")
print(f"100 USD = {usd_amount} KZT") # 100 USD = 50000.0 KZT

eur_amount = converter.convert(50, "EUR")
print(f"50 EUR = {eur_amount} KZT") # 50 EUR = 30000.0 KZT

# Base currency is not convertible
kzt_amount = converter.convert(10000, "KZT")
print(f"10000 KZT = {kzt_amount} KZT") # 10000 KZT = 10000 KZT
```

#### CurrencyService (Application)

File: [`app/services.py`](app/services.py)

Extended version with support for online courses and caching:

```python
from app.services import CurrencyService

# Mode 1: Default rates (for tests)
currency = CurrencyService()
print(currency.convert(100, "USD")) # 50000.0 (rate 500)

# Mode 2: Online courses from the NBRK website
currency_online = CurrencyService(use_online=True)
# Rates are downloaded from nationalbank.kz and cached in currency_rates.json

# Mode 3: Custom courses
my_rates = {"USD": 480.0, "EUR": 520.0, "RUB": 5.5}
currency_custom = CurrencyService(rates=my_rates)
print(currency_custom.convert(200, "EUR")) # 104000.0
```

---

### Reports

#### Report

File: [`domain/reports.py`](domain/reports.py)

```python
from typing import Iterable, Dict
from prettytable import PrettyTable
from domain.records import Record, IncomeRecord


class Report:
    """Report on financial records with filtering and grouping."""
    
    def __init__(self, records: Iterable[Record]):
        self._records = list(records)

    def total(self) -> float:
        """Total balance (income minus expenses)."""
        return sum(r.signed_amount() for r in self._records)

    def filter_by_period(self, prefix: str) -> "Report":
        """Filter by date (prefix: '2025' or '2025-01')."""
        filtered = [r for r in self._records if r.date.startswith(prefix)]
        return Report(filtered)

    def filter_by_category(self, category: str) -> "Report":
        """Filter by category."""
        filtered = [r for r in self._records if r.category == category]
        return Report(filtered)

    def grouped_by_category(self) -> Dict[str, "Report"]:
        """Grouping records by category."""
        groups = {}
        for record in self._records:
            if record.category not in groups:
                groups[record.category] = []
            groups[record.category].append(record)
        return {cat: Report(recs) for cat, recs in groups.items()}

    def as_table(self) -> str:
        """Formatted table with totals."""
        # ...implementation with PrettyTable
```

**Usage:**

```python
from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord

# Data preparation
records = [
    IncomeRecord(date="2025-01-15", amount=350000.0, category="Salary"),
    IncomeRecord(date="2025-02-15", amount=350000.0, category="Salary"),
    ExpenseRecord(date="2025-01-16", amount=25000.0, category="Products"),
    ExpenseRecord(date="2025-01-20", amount=8000.0, category="Transport"),
    ExpenseRecord(date="2025-02-05", amount=30000.0, category="Products"),
]

report = Report(records)

# Overall balance
print(f"Balance: {report.total():,.2f} KZT")
# Balance: 637,000.00 KZT

# Filter by January
january = report.filter_by_period("2025-01")
print(f"January: {january.total():,.2f} KZT")
# January: 317,000.00 KZT

# Filter by category
food = report.filter_by_category("Products")
print(f"Products: {food.total():,.2f} KZT")
# Products: -55,000.00 KZT

# Grouping
for cat, cat_report in report.grouped_by_category().items():
    print(f" {cat}: {cat_report.total():,.2f} KZT")
# Salary: 700,000.00 KZT
# Products: -55,000.00 KZT
# Transport: -8,000.00 KZT

# Table
print(report.as_table())
```

---

### Repository

#### JsonFileRecordRepository

File: [`infrastructure/repositories.py`](infrastructure/repositories.py)

```python
from abc import ABC, abstractmethod
from domain.records import Record, IncomeRecord, ExpenseRecord
import json


class RecordRepository(ABC):
    """Abstract record repository."""
    
    @abstractmethod
    def save(self, record: Record) -> None:
        """Save entry."""
        pass

    @abstractmethod
    def load_all(self) -> list[Record]:
        """Load all entries."""
        pass

    @abstractmethod
    def delete_by_index(self, index: int) -> bool:
        """Delete an entry by index."""
        pass


class JsonFileRecordRepository(RecordRepository):
    """Implementation of a repository with storage in a JSON file."""
    
    def __init__(self, file_path: str = "records.json"):
        self._file_path = file_path
    
    # ...implementation of methods
```

**Usage:**

```python
from infrastructure.repositories import JsonFileRecordRepository
from domain.records import IncomeRecord, ExpenseRecord

# Creating a repository (the file is created automatically)
repo = JsonFileRecordRepository("my_finances.json")

# Saving entries
repo.save(IncomeRecord(
    date="2025-01-15",
    amount=350000.0,
    category="Salary"
))

repo.save(ExpenseRecord(
    date="2025-01-16",
    amount=25000.0,
    category="Products"
))

# Load all entries
all_records = repo.load_all()
for i, rec in enumerate(all_records):
    rec_type = "Income" if isinstance(rec, IncomeRecord) else "Expense"
    print(f"[{i}] {rec.date} | {rec_type} | {rec.category} | {rec.amount:,.0f} KZT")

# [0] 2025-01-15 | Income | Salary | 350,000 KZT
# [1] 2025-01-16 | Consumption | Products | 25,000 KZT

# Delete by index
deleted = repo.delete_by_index(1)
print(f"Deleted: {deleted}") # True
```

**File format `records.json`:**

```json
[
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
    "category": "Products"
  }
]
```

---

### Use Cases

File: [`app/use_cases.py`](app/use_cases.py)

```python
from domain.records import IncomeRecord, ExpenseRecord
from domain.reports import Report
from infrastructure.repositories import RecordRepository
from app.services import CurrencyService


class CreateIncome:
    """Scenario: Creating an income record."""
    
    def __init__(self, repository: RecordRepository, currency: CurrencyService):
        self._repository = repository
        self._currency = currency

    def execute(self, *, date: str, amount: float, currency: str, category: str = "General"):
        # Convert to base currency
        normalized = self._currency.convert(amount, currency)
        record = IncomeRecord(date=date, amount=normalized, category=category)
        self._repository.save(record)


class CreateExpense:
    """Scenario: Create an expense record."""
    # Same as CreateIncome


class GenerateReport:
    """Scenario: report generation."""
    
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self) -> Report:
        return Report(self._repository.load_all())


class DeleteRecord:
    """Scenario: deleting an entry by index."""
    
    def __init__(self, repository: RecordRepository):
        self._repository = repository

    def execute(self, index: int) -> bool:
        return self._repository.delete_by_index(index)
```

**Usage:**

```python
from infrastructure.repositories import JsonFileRecordRepository
from app.services import CurrencyService
from app.use_cases import CreateIncome, CreateExpense, GenerateReport, DeleteRecord

# Initialization
repo = JsonFileRecordRepository()
currency = CurrencyService()

# Adding income in USD
create_income = CreateIncome(repo, currency)
create_income.execute(
    date="2025-01-20",
    amount=1000,
    currency="USD",
    category="Freelancing"
)
# Will be saved as 500000.0 KZT (1000 * 500)

# Adding an expense in EUR
create_expense = CreateExpense(repo, currency)
create_expense.execute(
    date="2025-01-21",
    amount=50,
    currency="EUR",
    category="Entertainment"
)
# Will be saved as 29500.0 KZT (50 * 590)

# Report generation
report = GenerateReport(repo).execute()
print(f"Balance: {report.total():,.2f} KZT")

# Filtering
january_report = report.filter_by_period("2025-01")
print(january_report.as_table())

# Delete
delete = DeleteRecord(repo)
success = delete.execute(0)
print(f"Deleted: {success}")
```

---

## 📁 File structure

```
project/
│
├── main.py                     # GUI entry point
├── records.json                # Record storage (created automatically)
├── currency_rates.json         # Currency rate cache (if use_online=True)
├── requirements.txt            # Python dependencies
├── README.md                   # This documentation
├── README_EN.md                # English documentation
├── CHANGELOG.md                # Project changelog
├── LICENSE.md                  # License information
│
├── app/                        # APPLICATION LAYER
│ ├── __init__.py
│ ├── services.py               # CurrencyService (adapter with online courses)
│ └── use_cases.py              # CreateIncome, CreateExpense, GenerateReport, DeleteRecord
│
├── domain/                     # DOMAIN LAYER
│ ├── __init__.py
│ ├── records.py                # Record, IncomeRecord, ExpenseRecord, MandatoryExpenseRecord
│ ├── reports.py                # Report
│ └── currency.py               # CurrencyService (base)
│
├── infrastructure/             # INFRASTRUCTURE LAYER
│ └── repositories.py           # RecordRepository, JsonFileRecordRepository
│
├── web/                        # Web application
│ ├── index.html                # HTML structure of the web application
│ ├── styles.css                # Styles and themes
│ └── app.js                    # Web application logic
│
├── tests/                      # Unit tests
│   ├── __init__.py
│   ├── test_csv.py             # CSV import/export tests
│   ├── test_currency.py        # CurrencyService tests
│   ├── test_excel.py           # XLSX import/export tests
│   ├── test_pdf.py             # PDF import/export tests
│   ├── test_records.py         # Record tests
│   ├── test_reports.py         # Report tests
│   ├── test_repositories.py    # Repository tests
│   ├── test_services.py        # Service tests
│   └── test_use_cases.py       # Tests use cases
│
└── utils/                      # UTILITIES
    ├── __init__.py
    ├── csv_utils.py            # Import/export CSV
    ├── excel_utils.py          # Import/export XLSX
    └── pdf_utils.py            # Import/export PDF
```

---

## 🧪 Tests

To run tests correctly, set the default value of the `use_online` parameter in the `__init__` method of the `CurrencyService` class (file `app/services.py`) to `False`.

### Running tests

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

### Code coverage

```bash
# Install pytest-cov
pip install pytest-cov

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# HTML report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in the browser
```

### Test examples

```python
# tests/test_records.py
from domain.records import IncomeRecord, ExpenseRecord

def test_income_signed_amount():
    income = IncomeRecord(date="2025-01-15", amount=100000.0, category="Test")
    assert income.signed_amount() == 100000.0

def test_expense_signed_amount():
    expense = ExpenseRecord(date="2025-01-16", amount=50000.0, category="Test")
    assert expense.signed_amount() == -50000.0


# tests/test_reports.py
from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord

def test_report_total():
    records = [
        IncomeRecord(date="2025-01-15", amount=100000.0, category="A"),
        ExpenseRecord(date="2025-01-16", amount=30000.0, category="B"),
    ]
    report = Report(records)
    assert report.total() == 70000.0

def test_filter_by_period():
    records = [
        IncomeRecord(date="2025-01-15", amount=100000.0, category="A"),
        IncomeRecord(date="2025-02-15", amount=50000.0, category="A"),
    ]
    report = Report(records)
    january = report.filter_by_period("2025-01")
    assert january.total() == 100000.0
```

---

## 💱 Supported currencies

| Currency          | Code | Default rate | Description     |
| ----------------- | ---- | ------------ | --------------- |
| Kazakhstani tenge | KZT  | 1.0          | Base currency   |
| US dollar         | USD  | 500.0        | 1 USD = 500 KZT |
| Euro              | EUR  | 590.0        | 1 EUR = 590 KZT |
| Russian ruble     | RUB  | 6.5          | 1 RUB = 6.5 KZT |

> **Current rates:** When initializing `CurrencyService(use_online=True)`, rates are downloaded from the [National Bank of the Republic of Kazakhstan](https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut/) and cached locally.

---

## 📄 License

MIT License - free to use, modify and distribute.
