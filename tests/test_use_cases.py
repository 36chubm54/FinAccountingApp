from unittest.mock import Mock, patch
from app.use_cases import (
    CreateIncome,
    CreateExpense,
    GenerateReport,
    DeleteRecord,
    DeleteAllRecords,
    ImportFromCSV,
)
from domain.records import IncomeRecord, ExpenseRecord, Record
from infrastructure.repositories import RecordRepository


class TestCreateIncome:
    def test_execute_creates_income_record_and_saves_to_repository(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        mock_currency = Mock()
        mock_currency.convert.return_value = 47000.0  # 100 * 470

        use_case = CreateIncome(repository=mock_repo, currency=mock_currency)

        # Act
        use_case.execute(
            date="2025-01-01", amount=100.0, currency="USD", category="Salary"
        )

        # Assert
        mock_currency.convert.assert_called_once_with(100.0, "USD")
        expected_record = IncomeRecord(
            date="2025-01-01", amount=47000.0, category="Salary"
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
            date="2025-01-01", amount=47000.0, category="General"
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
        use_case.execute(
            date="2025-01-02", amount=50.0, currency="USD", category="Food"
        )

        # Assert
        mock_currency.convert.assert_called_once_with(50.0, "USD")
        expected_record = ExpenseRecord(
            date="2025-01-02", amount=23500.0, category="Food"
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
            date="2025-01-02", amount=23500.0, category="General"
        )
        mock_repo.save.assert_called_once_with(expected_record)


class TestGenerateReport:
    def test_execute_returns_report_with_all_records(self):
        # Arrange
        mock_repo = Mock(spec=RecordRepository)
        records = [
            IncomeRecord(date="2025-01-01", amount=100.0, category="Salary"),
            ExpenseRecord(date="2025-01-02", amount=50.0, category="Food"),
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

        # Mock Report.from_csv to return a report with test records
        with patch("app.use_cases.Report") as mock_report_class:
            mock_report = Mock()
            test_records = [Mock(spec=Record), Mock(spec=Record), Mock(spec=Record)]
            mock_report.records.return_value = test_records
            mock_report_class.from_csv.return_value = mock_report

            use_case = ImportFromCSV(repository=mock_repo)

            # Act
            result = use_case.execute("test.csv")

            # Assert
            mock_report_class.from_csv.assert_called_once_with("test.csv")
            mock_repo.delete_all.assert_called_once()
            assert mock_repo.save.call_count == 3
            assert result == 3
