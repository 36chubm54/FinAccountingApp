# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.
This project adheres to Semantic Versioning.

---

## [1.1.2] - 2026-03-04
### Performance
- Implement bulk import replace flow via `replace_all_for_import`
- Build records/transfers in memory and persist once for faster JSON imports
- Decouple SQLite startup cost when `USE_SQLITE=False`
- Lazy-load SQLite modules in bootstrap
- Optimize Windows file lock retry logic (`WinError 5/32`)

### Refactor
- Remove `report_from_csv` wrapper
- Simplify import pipeline integration

No breaking changes.

---

## [1.1.1] - 2026-03-02
### Removed
- Remove deprecated web frontend directory

---

## [1.1.0] - 2026-03-02
### Fixed
- Harden SQLite bootstrap integrity checks
- Restore deterministic ID normalization
- Fix transfer append ordering issues

### Stability
- Strengthen SQLite data consistency guarantees

---

## [1.0.1] - 2026-03-01
### Refactor
- Overhaul SQLite import pipeline with service architecture
- Add safety guardrails for migration consistency

---

## [1.0.0] - 2026-03-01
### Added
- SQLite as primary storage
- Storage abstraction layer
- Robust bootstrap process
- JSON-to-SQLite migration support

### Changed
- Application storage backend migrated from JSON to SQLite

This marks the beginning of the SQL era.

---

## [0.6.0] - 2026-02-28
### Added
- Storage abstraction layer
- JSON-to-SQLite migration foundation

### Stability
- Final stable JSON-based release

This is the last stable release before SQLite migration.

---

## [0.5.0] - 2026-02-19
### Added
- Wallet transfers with commissions
- Net worth calculation
- Wallet domain model

---

## [0.2.0] - 2026-01-20
### Changed
- Replace CLI with multi-window Tkinter GUI

---

## [0.1.0] - 2026-01-20
### Added
- Initial CLI-based financial accounting prototype
- Layered backend structure (domain, application, infrastructure)
