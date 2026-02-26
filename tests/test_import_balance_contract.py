from unittest.mock import Mock, patch

from app.services import CurrencyService
from domain.import_policy import ImportPolicy
from domain.records import IncomeRecord
from domain.wallets import Wallet
from gui.controllers import FinancialController
from infrastructure.repositories import RecordRepository


def _build_controller() -> tuple[FinancialController, Mock, Mock]:
    repository = Mock(spec=RecordRepository)
    repository.load_wallets.return_value = [
        Wallet(id=1, name="Main", currency="KZT", initial_balance=0.0, system=True)
    ]
    currency = Mock(spec=CurrencyService)
    return FinancialController(repository, currency), repository, currency


def test_import_records_csv_saves_imported_initial_balance() -> None:
    controller, repository, currency = _build_controller()
    imported_records = [IncomeRecord(date="2025-01-01", _amount_init=100.0, category="Salary")]

    with patch("gui.importers.import_records_from_csv") as import_csv:
        import_csv.return_value = (imported_records, 321.5, (1, 0, []))

        summary = controller.import_records(
            "CSV",
            "dummy.csv",
            policy=ImportPolicy.FULL_BACKUP,
        )

    import_csv.assert_called_once_with(
        "dummy.csv",
        policy=ImportPolicy.FULL_BACKUP,
        currency_service=currency,
        wallet_ids={1},
    )
    repository.replace_records_and_transfers.assert_called_once()
    repository.save_initial_balance.assert_called_once_with(321.5)
    assert summary == (1, 0, [])


def test_import_records_xlsx_saves_imported_initial_balance() -> None:
    controller, repository, currency = _build_controller()
    imported_records = [IncomeRecord(date="2025-01-01", _amount_init=100.0, category="Salary")]

    with patch("gui.importers.import_records_from_xlsx") as import_xlsx:
        import_xlsx.return_value = (imported_records, 654.0, (1, 0, []))

        summary = controller.import_records(
            "XLSX",
            "dummy.xlsx",
            policy=ImportPolicy.FULL_BACKUP,
        )

    import_xlsx.assert_called_once_with(
        "dummy.xlsx",
        policy=ImportPolicy.FULL_BACKUP,
        currency_service=currency,
        wallet_ids={1},
    )
    repository.replace_records_and_transfers.assert_called_once()
    repository.save_initial_balance.assert_called_once_with(654.0)
    assert summary == (1, 0, [])
