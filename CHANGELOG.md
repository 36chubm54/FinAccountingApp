# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed

- Refactor online currency rates fetching (online mode remains opt-in)
- Replace CLI with Tkinter GUI for financial accounting
- Refactor: move export/import UI logic into `gui/exporters.py` and `gui/importers.py` and add `gui/helpers.py`.

- Improve PDF font registration to support Cyrillic on Windows/Linux, with multiple fallbacks.
- Improve GUI error handling: export/import handlers now log exceptions for diagnostics.
- Redesign GUI (tabs, error handling, and visual feedback).

### Documentation

- Fixed link to the "Web application" title in the README_EN.md table of contents
- Improve README formatting and add test setup note
- Add web application section to README.md with features, setup, and structure details
- Document main window infographics in README.md and README_EN.md
- Update READMEs and CHANGELOG to reflect GUI refactor, improved logging and font handling

### Initial

- Initial commit: Financial accounting - backend with domain, application and infrastructure layers
