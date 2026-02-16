import os
import tempfile

from domain.import_policy import ImportPolicy
from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord
from utils.backup_utils import export_full_backup_to_json, import_full_backup_from_json
from utils.csv_utils import import_records_from_csv


class DummyCurrency:
    def get_rate(self, currency: str) -> float:
        rates = {"USD": 500.0, "EUR": 600.0, "KZT": 1.0}
        return rates[currency]


def test_current_rate_policy_fills_missing_fx_fields():
    csv_content = """date,type,category,amount_original,currency
2025-01-01,income,Salary,100,USD
"""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", encoding="utf-8"
    ) as tmp:
        tmp.write(csv_content)
        path = tmp.name
    try:
        records, initial_balance, summary = import_records_from_csv(
            path,
            policy=ImportPolicy.CURRENT_RATE,
            currency_service=DummyCurrency(),
        )
        assert initial_balance == 0.0
        assert summary[0] == 1
        assert summary[1] == 0
        assert len(records) == 1
        assert records[0].rate_at_operation == 500.0
        assert records[0].amount_kzt == 50000.0
    finally:
        os.unlink(path)


def test_current_rate_policy_overrides_existing_fx_fields():
    csv_content = """date,type,category,amount_original,currency,rate_at_operation,amount_kzt
2025-01-01,income,Salary,100,USD,450,45000
"""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", encoding="utf-8"
    ) as tmp:
        tmp.write(csv_content)
        path = tmp.name
    try:
        records, _, summary = import_records_from_csv(
            path,
            policy=ImportPolicy.CURRENT_RATE,
            currency_service=DummyCurrency(),
        )
        assert summary[0] == 1
        assert records[0].rate_at_operation == 500.0
        assert records[0].amount_kzt == 50000.0
    finally:
        os.unlink(path)


def test_legacy_policy_imports_old_amount_column():
    csv_content = """date,type,category,amount
2025-01-02,expense,Food,2500
"""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", encoding="utf-8"
    ) as tmp:
        tmp.write(csv_content)
        path = tmp.name
    try:
        records, _, summary = import_records_from_csv(path, policy=ImportPolicy.LEGACY)
        assert summary[0] == 1
        assert isinstance(records[0], ExpenseRecord)
        assert records[0].currency == "KZT"
        assert records[0].rate_at_operation == 1.0
        assert records[0].amount_kzt == 2500.0
    finally:
        os.unlink(path)


def test_import_validation_skips_invalid_rows():
    csv_content = """date,type,category,amount_original,currency,rate_at_operation,amount_kzt
bad-date,income,Salary,10,USD,500,5000
2025-01-02,expense,Food,-5,KZT,1,5
2025-01-03,income,Salary,10,USDX,500,5000
2025-01-04,income,Salary,10,USD,500,5000
"""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", encoding="utf-8"
    ) as tmp:
        tmp.write(csv_content)
        path = tmp.name
    try:
        records, _, summary = import_records_from_csv(
            path, policy=ImportPolicy.FULL_BACKUP
        )
        assert len(records) == 1
        assert isinstance(records[0], IncomeRecord)
        assert summary[0] == 1
        assert summary[1] == 3
        assert len(summary[2]) == 3
    finally:
        os.unlink(path)


def test_full_backup_roundtrip():
    records = [
        IncomeRecord(
            date="2025-01-01",
            amount_original=100.0,
            currency="USD",
            rate_at_operation=500.0,
            amount_kzt=50000.0,
            category="Salary",
        )
    ]
    mandatory = [
        MandatoryExpenseRecord(
            date="",
            amount_original=50.0,
            currency="KZT",
            rate_at_operation=1.0,
            amount_kzt=50.0,
            category="Mandatory",
            description="Rent",
            period="monthly",
        )
    ]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        path = tmp.name
    try:
        export_full_backup_to_json(
            path,
            initial_balance=123.0,
            records=records,
            mandatory_expenses=mandatory,
        )
        initial_balance, imported_records, imported_mandatory, summary = (
            import_full_backup_from_json(path)
        )
        assert initial_balance == 123.0
        assert len(imported_records) == 1
        assert len(imported_mandatory) == 1
        assert summary[1] == 0
    finally:
        os.unlink(path)
