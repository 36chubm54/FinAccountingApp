import pytest
from domain.records import Record, IncomeRecord, ExpenseRecord


class TestIncomeRecord:
    def test_creation_with_category(self):
        record = IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")
        assert record.date == "2025-01-01"
        assert record.amount == 100.0
        assert record.category == "Salary"

    # Category is required in the dataclass, no default value

    def test_signed_amount_positive(self):
        record = IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")
        assert record.signed_amount() == 100.0

    def test_signed_amount_with_negative_amount(self):
        record = IncomeRecord(date="2025-01-01", amount=-50.0, category="Salary")
        assert record.signed_amount() == -50.0

    def test_immutable(self):
        record = IncomeRecord(date="2025-01-01", amount=100.0, category="Salary")
        with pytest.raises(AttributeError):
            record.amount = 200.0  # type: ignore


class TestExpenseRecord:
    def test_creation_with_category(self):
        record = ExpenseRecord(date="2025-01-01", amount=50.0, category="Food")
        assert record.date == "2025-01-01"
        assert record.amount == 50.0
        assert record.category == "Food"

    # Category is required in the dataclass, no default value

    def test_signed_amount_negative(self):
        record = ExpenseRecord(date="2025-01-01", amount=50.0, category="Food")
        assert record.signed_amount() == -50.0

    def test_signed_amount_absolute_value(self):
        record = ExpenseRecord(date="2025-01-01", amount=-100.0, category="Food")
        assert record.signed_amount() == -100.0

    def test_immutable(self):
        record = ExpenseRecord(date="2025-01-01", amount=50.0, category="Food")
        with pytest.raises(AttributeError):
            record.amount = 30.0  # type: ignore


class TestRecord:
    def test_record_is_abstract(self):
        # Record is abstract and cannot be instantiated directly
        with pytest.raises(TypeError):
            Record(date="2025-01-01", amount=100.0, category="Test")  # type: ignore
