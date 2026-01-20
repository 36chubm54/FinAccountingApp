from unittest.mock import Mock
from app.use_cases import CreateIncome, CreateExpense, GenerateReport, DeleteRecord
from domain.records import IncomeRecord, ExpenseRecord
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
