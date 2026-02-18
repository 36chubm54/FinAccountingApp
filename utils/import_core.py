import re
from collections.abc import Callable
from typing import Any

from domain.import_policy import ImportPolicy
from domain.records import ExpenseRecord, IncomeRecord, MandatoryExpenseRecord, Record
from domain.validation import ensure_valid_period, parse_ymd

MANDATORY_PERIODS = {"daily", "weekly", "monthly", "yearly"}

ImportSummary = tuple[int, int, list[str]]


def norm_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        raw = str(value).strip()
        if raw.startswith("(") and raw.endswith(")"):
            raw = "-" + raw[1:-1]
        return float(raw)
    except (TypeError, ValueError):
        return default


def safe_type(value: str) -> str:
    normalized = norm_key(value)
    if normalized in {"income", "expense", "mandatory_expense"}:
        return normalized
    if normalized in {"mandatory_expense_record", "mandatory_expenses"}:
        return "mandatory_expense"
    if normalized in {"mandatory", "mandatoryexpense"}:
        return "mandatory_expense"
    return normalized


def record_type_name(record: Record) -> str:
    if isinstance(record, IncomeRecord):
        return "income"
    if isinstance(record, MandatoryExpenseRecord):
        return "mandatory_expense"
    return "expense"


def _validate_currency(currency: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{3}", currency or ""))


def parse_import_row(
    row: dict[str, Any],
    *,
    row_label: str,
    policy: ImportPolicy,
    get_rate: Callable[[str], float] | None = None,
    mandatory_only: bool = False,
) -> tuple[Record | None, float | None, str | None]:
    row_lc = {norm_key(str(k)): v for k, v in row.items()}
    row_type = safe_type(str(row_lc.get("type", "") or "")).lower()

    if row_type == "initial_balance":
        balance = as_float(
            row_lc.get("amount_original", row_lc.get("amount_kzt", row_lc.get("amount"))),
            0.0,
        )
        return None, float(balance or 0.0), None

    if mandatory_only:
        row_type = "mandatory_expense"

    required_fields = ["category", "type"]
    if not mandatory_only:
        required_fields.append("date")
    if policy == ImportPolicy.LEGACY:
        required_fields.append("amount")
    else:
        required_fields.extend(["amount_original", "currency"])

    for field in required_fields:
        if str(row_lc.get(field, "") or "").strip() == "":
            return None, None, f"{row_label}: missing required field '{field}'"

    date_value = str(row_lc.get("date", "") or "").strip()
    if date_value:
        try:
            parse_ymd(date_value)
        except ValueError as exc:
            return None, None, f"{row_label}: invalid date '{date_value}' ({exc})"
    elif not mandatory_only:
        return None, None, f"{row_label}: missing required field 'date'"

    category = str(row_lc.get("category", "General") or "General").strip() or "General"
    description = str(row_lc.get("description", "") or "")
    period = str(row_lc.get("period", "monthly") or "monthly").lower()

    if mandatory_only:
        row_type = "mandatory_expense"
    elif row_type not in {"income", "expense", "mandatory_expense"}:
        return None, None, f"{row_label}: unsupported type '{row_type}'"

    if policy == ImportPolicy.LEGACY:
        amount = as_float(row_lc.get("amount"), None)
        if amount is None:
            return None, None, f"{row_label}: invalid amount"
        amount_original = abs(float(amount))
        currency = "KZT"
        rate_at_operation = 1.0
        amount_kzt = abs(float(amount))
    else:
        amount_original = as_float(row_lc.get("amount_original"), None)
        if amount_original is None:
            return None, None, f"{row_label}: invalid amount_original"
        currency = str(row_lc.get("currency", "KZT") or "KZT").strip().upper()
        if not _validate_currency(currency):
            return None, None, f"{row_label}: invalid currency '{currency}'"
        rate_at_operation = as_float(row_lc.get("rate_at_operation"), None)
        amount_kzt = as_float(row_lc.get("amount_kzt"), None)

        if policy == ImportPolicy.CURRENT_RATE:
            if get_rate is None:
                return (
                    None,
                    None,
                    f"{row_label}: current-rate policy requires currency service",
                )
            try:
                rate_at_operation = float(get_rate(currency))
                amount_kzt = float(amount_original * rate_at_operation)
            except Exception as exc:
                return (
                    None,
                    None,
                    f"{row_label}: failed to get current rate for {currency} ({exc})",
                )

        if rate_at_operation is None:
            return (
                None,
                None,
                f"{row_label}: missing required field 'rate_at_operation'",
            )
        if amount_kzt is None:
            return None, None, f"{row_label}: missing required field 'amount_kzt'"

    if amount_original < 0:
        return None, None, f"{row_label}: amount_original must be >= 0"

    common = {
        "date": date_value,
        "amount_original": float(amount_original),
        "currency": currency,
        "rate_at_operation": float(rate_at_operation),
        "amount_kzt": float(amount_kzt),
        "category": category,
    }

    if row_type == "income":
        return IncomeRecord(**common), None, None

    if row_type == "expense":
        common["amount_original"] = abs(common["amount_original"])
        common["amount_kzt"] = abs(common["amount_kzt"])
        return ExpenseRecord(**common), None, None

    try:
        ensure_valid_period(period)
    except ValueError:
        return None, None, f"{row_label}: invalid mandatory period '{period}'"

    common["amount_original"] = abs(common["amount_original"])
    common["amount_kzt"] = abs(common["amount_kzt"])
    return (
        MandatoryExpenseRecord(
            **common,
            description=description,
            period=period,  # type: ignore[arg-type]
        ),
        None,
        None,
    )
