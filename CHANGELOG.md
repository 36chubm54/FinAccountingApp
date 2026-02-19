# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Wallets, Transfers and Commissions (Phase 2):
  - Added `Transfer` aggregate model and repository persistence.
  - Added `transfer_id` linkage in records and transfer double-entry creation.
  - Added transfer commission handling as a separate `Commission` expense.
  - Added wallet management enhancements including `allow_negative`.
  - Added dynamic net worth calculation (fixed and current).
  - Added transfer/wallet UI controls in desktop GUI (wallets + transfer form).
  - Added phase-2 unit tests for transfer invariants, commission effect, opening balance and date typing.
- Wallet Support (Phase 1):
  - Added `Wallet` domain model and system wallet (`id=1`, `Main wallet`).
  - Added `wallet_id` to records and automatic assignment to system wallet for new entries.
  - Added repository migration from legacy `initial_balance` to `wallet.initial_balance` with `initial_balance=0` in root JSON.
  - Added wallet-focused tests for migration invariants, record creation, report totals, opening balance, and date typing.
- Add initial balance feature to financial tracker
- Add mandatory expenses management feature
- Add CSV import and delete all records features
- Add web directory with frontend files (HTML, CSS, JS) for financial accounting interface
- Add delete all records functionality and improve currency service
- Add CSV export functionality for reports
- Add financial accounting project structure
- Add CSV import/export functionality for mandatory expenses with dedicated UI buttons and error handling
- Add utils module for mandatory expense CSV operations with validation and data integrity checks
- Add Excel import/export support: import records from `.xlsx` and export reports to `.xlsx`
- Add Excel import/export for mandatory expenses (sheet `Mandatory` with columns `Amount (KZT),Category,Description,Period`)
- Add PDF export support for reports and mandatory expenses
- UI: replace separate import/export buttons with format dropdowns and single Import/Export buttons (supports CSV, XLSX, PDF)
- Add monthly income/expense summary for past and current months in report output
- Add yearly report export as a separate XLSX sheet and as a second PDF table after the statement
- Limit XLSX report import to the first worksheet only
- Add infographic block to the main window: expense pie chart plus daily/monthly income-expense histograms
- Group minor expense categories into an "Other" slice in the pie chart
- Add time filter for the pie chart and make the category list scrollable
- Unit tests: add tests for `gui.exporters` and `gui.importers`.
- Add export of grouped category tables to Excel/PDF report after the main statement.
- Add multicurrency records with FX revaluation and unified data import/export
- Add import policies, validated row-level import, and full JSON backup support

### Changed

- Updated global report arithmetic to exclude transfer-linked records from net profit while keeping commission as expense.
- Updated controller record-list rendering to display transfer-linked records as one logical operation.
- Updated report/domain logic to use normalized `datetime.date` in records and opening-balance computations.
- Updated GUI flow so operation/report creation goes through `FinancialController` instead of direct use-case calls.
- Refactor online currency rates fetching (online mode remains opt-in)
- Replace CLI with Tkinter GUI for financial accounting
- Refactor: move export/import UI logic into `gui/exporters.py` and `gui/importers.py` and add `gui/helpers.py`.

- Improve PDF font registration to support Cyrillic on Windows/Linux, with multiple fallbacks.
- Improve GUI error handling: export/import handlers now log exceptions for diagnostics.
- Redesign GUI (tabs, error handling, and visual feedback).
- Fix filtered report totals to use period opening balance instead of global initial balance.
- Update report export rows (`CSV/XLSX/PDF`) to show opening balance label for filtered periods.
- Update GUI report summary label to show `Opening balance` for filtered reports and `Initial balance` otherwise.
- Expand `Report` tests to cover year/month/day filters, opening-balance invariant, and edge cases.
- Add strict report period validation for `YYYY`, `YYYY-MM`, `YYYY-MM-DD` and reject future filter dates.
- Add report period end filter and validate both start/end values including `end >= start`.
- Add period-range title to report generation and exports (`PDF/CSV/XLSX`), with default end date = today when end is omitted in GUI.
- Standardize filtered balance row label to `Opening balance`.

### Documentation

- Fixed link to the "Web application" title in the README_EN.md table of contents
- Improve README formatting and add test setup note
- Add web application section to README.md with features, setup, and structure details
- Document main window infographics in README.md and README_EN.md
- Update READMEs and CHANGELOG to reflect GUI refactor, improved logging and font handling
- Add section `Opening Balance in Filtered Reports` to `README.md` and `README_EN.md`.

### Initial

- Initial commit: Financial accounting - backend with domain, application and infrastructure layers
