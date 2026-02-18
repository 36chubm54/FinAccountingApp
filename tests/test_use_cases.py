import os
import tempfile
from datetime import date
from unittest.mock import Mock, patch

import pytest

from app.use_cases import (
    CreateExpense,
    CreateIncome,
    DeleteAllRecords,
    DeleteRecord,
    GenerateReport,
    ImportFromCSV,
)
from domain.import_policy import ImportPolicy
from domain.records import ExpenseRecord, IncomeRecord, Record
from infrastructure.repositories import JsonFileRecordRepository, RecordRepository


class TestCreateIncome:
    def test_execute_creates_income_record_and_saves_to_repository(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_currency = Mock()
        mock_currency.convert.return_value = 47000.0  # 100 * 470

        use_case = CreateIncome(repository=mock_repo, currency=mock_currency)

        # Act
        use_case.execute(date="2025-01-01", amount=100.0, currency="USD", category="Salary")

        # Assert
        mock_currency.convert.assert_called_once_with(100.0, "USD")
        expected_record = IncomeRecord(
            date="2025-01-01",
            amount_original=100.0,
            currency="USD",
            rate_at_operation=470.0,
            amount_kzt=47000.0,
            category="Salary",
        )
        mock_repo.save.assert_called_once_with(expected_record)

    def test_execute_with_default_category(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_currency = Mock()
        mock_currency.convert.return_value = 47000.0

        use_case = CreateIncome(repository=mock_repo, currency=mock_currency)

        # Act
        use_case.execute(date="2025-01-01", amount=100.0, currency="USD")

        # Assert
        expected_record = IncomeRecord(
            date="2025-01-01",
            amount_original=100.0,
            currency="USD",
            rate_at_operation=470.0,
            amount_kzt=47000.0,
            category="General",
        )
        mock_repo.save.assert_called_once_with(expected_record)


class TestCreateExpense:
    def test_execute_creates_expense_record_and_saves_to_repository(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_currency = Mock()
        mock_currency.convert.return_value = 23500.0  # 50 * 470

        use_case = CreateExpense(repository=mock_repo, currency=mock_currency)

        # Act
        use_case.execute(date="2025-01-02", amount=50.0, currency="USD", category="Food")

        # Assert
        mock_currency.convert.assert_called_once_with(50.0, "USD")
        expected_record = ExpenseRecord(
            date="2025-01-02",
            amount_original=50.0,
            currency="USD",
            rate_at_operation=470.0,
            amount_kzt=23500.0,
            category="Food",
        )
        mock_repo.save.assert_called_once_with(expected_record)

    def test_execute_with_default_category(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_currency = Mock()
        mock_currency.convert.return_value = 23500.0

        use_case = CreateExpense(repository=mock_repo, currency=mock_currency)

        # Act
        use_case.execute(date="2025-01-02", amount=50.0, currency="USD")

        # Assert
        expected_record = ExpenseRecord(
            date="2025-01-02",
            amount_original=50.0,
            currency="USD",
            rate_at_operation=470.0,
            amount_kzt=23500.0,
            category="General",
        )
        mock_repo.save.assert_called_once_with(expected_record)


class TestGenerateReport:
    def test_execute_returns_report_with_all_records(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        records = [
            IncomeRecord(date="2025-01-01", _amount_init=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", _amount_init=50.0, category="Food"),
        ]
        mock_repo.load_all.return_value = records

        use_case = GenerateReport(repository=mock_repo)

        # Act
        report = use_case.execute()

        # Assert
        mock_repo.load_all.assert_called_once()
        assert report.records() == records

    def test_delete_record_success(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_repo.delete_by_index.return_value = True

        use_case = DeleteRecord(repository=mock_repo)

        # Act
        result = use_case.execute(index=1)

        # Assert
        mock_repo.delete_by_index.assert_called_once_with(1)
        assert result is True

    def test_delete_record_failure(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_repo.delete_by_index.return_value = False

        use_case = DeleteRecord(repository=mock_repo)

        # Act
        result = use_case.execute(index=99)

        # Assert
        mock_repo.delete_by_index.assert_called_once_with(99)
        assert result is False


class TestDeleteAllRecords:
    def test_execute_calls_delete_all_on_repository(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)

        use_case = DeleteAllRecords(repository=mock_repo)

        # Act
        use_case.execute()

        # Assert
        mock_repo.delete_all.assert_called_once()


class TestImportFromCSV:
    def test_execute_imports_records_from_csv_and_saves_to_repository(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)

        with patch("utils.csv_utils.import_records_from_csv") as mock_import:
            test_records = [Mock(spec=Record), Mock(spec=Record), Mock(spec=Record)]
            mock_import.return_value = (test_records, 0.0, (3, 0, []))

            use_case = ImportFromCSV(repository=mock_repo)

            # Act
            result = use_case.execute("test.csv")

            # Assert
            mock_import.assert_called_once_with("test.csv", policy=ImportPolicy.FULL_BACKUP)
            mock_repo.replace_records.assert_called_once_with(test_records, 0.0)
            assert result == 3

    def test_execute_saves_initial_balance(self):
        mock_repo = Mock(spec=RecordRepository)
        with patch("utils.csv_utils.import_records_from_csv") as mock_import:
            mock_import.return_value = ([], 123.45, (0, 0, []))

            use_case = ImportFromCSV(repository=mock_repo)
            use_case.execute("test.csv")

            mock_repo.replace_records.assert_called_once_with([], 123.45)

    def test_execute_does_not_modify_repository_on_import_error(self):
        mock_repo = Mock(spec=RecordRepository)
        with patch("utils.csv_utils.import_records_from_csv") as mock_import:
            mock_import.side_effect = ValueError("invalid csv")
            use_case = ImportFromCSV(repository=mock_repo)

            with patch.object(mock_repo, "replace_records") as replace_records:
                with patch.object(mock_repo, "delete_all") as delete_all:
                    with patch.object(mock_repo, "save") as save_record:
                        with patch.object(mock_repo, "save_initial_balance") as save_balance:
                            with pytest.raises(ValueError):
                                use_case.execute("broken.csv")

                        replace_records.assert_not_called()
                        delete_all.assert_not_called()
                        save_record.assert_not_called()
                        save_balance.assert_not_called()

    def test_execute_keeps_existing_data_when_csv_invalid(self):
        repo_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        repo_file.close()
        csv_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        csv_file.write("date,type,category,amount_original,currency,rate_at_operation,amount_kzt\n")
        csv_file.write("bad-date,income,Salary,10,USD,500,5000\n")
        csv_file.close()
        try:
            repository = JsonFileRecordRepository(repo_file.name)
            repository.save_initial_balance(77.0)
            repository.save(IncomeRecord(date="2025-01-01", _amount_init=10.0, category="Salary"))

            use_case = ImportFromCSV(repository=repository)
            with pytest.raises(ValueError):
                use_case.execute(csv_file.name)

            assert repository.load_initial_balance() == 77.0
            records = repository.load_all()
            assert len(records) == 1
            assert records[0].date == date(2025, 1, 1)
        finally:
            os.unlink(repo_file.name)
            os.unlink(csv_file.name)
