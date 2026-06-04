# Ledgera v3.0.0 Alpha.4 Readiness

## Status

`v3.0.0-alpha.4` is closed as the first Kotlin Compose Desktop and Rust UniFFI bridge MVP.

Tkinter remains the primary production UI. Kotlin Desktop is a parallel alpha client focused on the Operations screen and uses the Rust storage engine through UniFFI. Python/PyO3 bridge work from earlier alpha milestones remains available for the existing Tkinter runtime and parity testing.

## Completed

- Added `kotlin/ledgera-ui` as a Gradle Kotlin Compose Multiplatform project with a Desktop JVM target.
- Added `OperationsScreen` for listing records, filtering by record type, selecting wallets, and adding standalone income/expense records.
- Added `RustEngineAdapter` and a common `EngineAdapter` seam so the Kotlin UI calls Rust through generated UniFFI bindings.
- Added `LedgeraTheme` with the first Material 3 color/token surface for Kotlin Desktop.
- Added `rust/ledgera_engine/kotlin_ffi` as a dedicated UniFFI crate with `LedgeraEngine`, record DTOs, wallet DTOs, engine status, and error mapping.
- Added Rust storage APIs for filtered record reads and standalone income/expense creation.
- Added Gradle wrapper/configuration and a `kotlin-alpha4` CI job for Desktop jar/test validation on Ubuntu and Windows.
- Marked `gradlew` executable in git so Linux CI can invoke `./gradlew`.
- Corrected Kotlin FFI wallet balances to report `initial_balance + record_delta`.

## Runtime Boundaries

- Kotlin alpha.4 is a parallel UI, not a replacement for Tkinter.
- Kotlin calls Rust through UniFFI and does not contain business logic beyond view-model validation and UI state management.
- The Kotlin Operations MVP supports standalone `income` and `expense` rows only.
- Transfers, debt-linked records, budgets, distribution, mandatory payments, reports, analytics screens, import/export, updater, and settings remain outside alpha.4 Kotlin scope.
- Kotlin does not create production databases implicitly; manual smoke testing requires an existing SQLite ledger database with at least one active wallet.
- Rust remains the owner of the Kotlin FFI storage mutations; Python remains the owner of existing Tkinter service contracts and migrations.

## Validation Evidence

- `cargo test --manifest-path rust/ledgera_engine/Cargo.toml -p ledgera_engine_kotlin_ffi --lib --bins`
- `.\gradlew.bat :ledgera-ui:desktopJar :ledgera-ui:desktopTest --no-daemon`
- The Gradle command passed from a temporary ASCII `subst` path (`L:\`) mapped to the checkout.
- Running the same Gradle test task from the local Windows path containing Cyrillic segments can trigger a Gradle/JUnit test-worker `ClassNotFoundException` even when the compiled test class exists. Use CI or an ASCII path for local reproduction of the Kotlin gate.
- UniFFI generation currently prints a non-fatal warning if `ktlint` is not installed; the generated bindings still compile and tests pass.

## Deferred

- Full Kotlin Desktop parity across all 9 Tkinter tabs.
- Android and iOS targets.
- CRDT sync and mobile/Desktop sync UX.
- Kotlin screens for Reports, Analytics, Dashboard, Budget, Debts, Distribution, Mandatory, and Settings.
- Tkinter deprecation and `--legacy-ui` release behavior.
- Rust-owned import/export, updater, broad repository replacement, and schema migration ownership.

## Acceptance

Alpha.4 is ready to merge when PR review feedback is addressed, the Kotlin Desktop Gradle gate passes in CI or an ASCII checkout path, and the branch documents the remaining Kotlin/mobile/sync boundaries listed above.
