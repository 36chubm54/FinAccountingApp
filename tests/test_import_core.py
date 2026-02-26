import pytest

from domain.import_policy import ImportPolicy
from utils.import_core import parse_import_row


def test_parse_import_row_rejects_malformed_currency_codes() -> None:
    bad_codes = ["US", "USDT", "12$", "", "usd1"]
    for code in bad_codes:
        record, balance, error = parse_import_row(
            {
                "date": "2025-01-01",
                "type": "income",
                "wallet_id": "1",
                "category": "Salary",
                "amount_original": "10",
                "currency": code,
                "rate_at_operation": "500",
                "amount_kzt": "5000",
            },
            row_label=f"currency-{code}",
            policy=ImportPolicy.FULL_BACKUP,
        )
        assert record is None
        assert balance is None
        assert any(
            marker in (error or "")
            for marker in ("invalid currency", "missing required field 'currency'")
        )


def test_parse_import_row_rejects_malformed_date() -> None:
    record, balance, error = parse_import_row(
        {
            "date": "2025/01/01",
            "type": "expense",
            "wallet_id": "1",
            "category": "Food",
            "amount_original": "10",
            "currency": "KZT",
            "rate_at_operation": "1",
            "amount_kzt": "10",
        },
        row_label="row 2",
        policy=ImportPolicy.FULL_BACKUP,
    )
    assert record is None
    assert balance is None
    assert "invalid date" in (error or "")


def test_parse_import_row_current_rate_requires_service() -> None:
    record, balance, error = parse_import_row(
        {
            "date": "2025-01-01",
            "type": "income",
            "wallet_id": "1",
            "category": "Salary",
            "amount_original": "10",
            "currency": "USD",
        },
        row_label="row 3",
        policy=ImportPolicy.CURRENT_RATE,
    )
    assert record is None
    assert balance is None
    assert "requires currency service" in (error or "")


def test_parse_import_row_handles_initial_balance_row() -> None:
    record, balance, error = parse_import_row(
        {"type": "initial_balance", "amount_original": "123.45"},
        row_label="row 1",
        policy=ImportPolicy.FULL_BACKUP,
    )
    assert record is None
    assert error is None
    assert balance == pytest.approx(123.45)
