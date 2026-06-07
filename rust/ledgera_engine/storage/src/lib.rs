use ledgera_engine_core::{
    minor_to_money_value, quantize_money_text, quantize_rate_text, rate_float_from_text,
    to_minor_units,
};
use rusqlite::{Connection, OptionalExtension};
use std::cell::RefCell;
use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};
#[cfg(windows)]
use windows_sys::Win32::{Foundation::SYSTEMTIME, System::SystemInformation::GetLocalTime};

pub type StorageResult<T> = Result<T, String>;
pub type WalletBalanceRow = (i64, String, String, f64, f64);

#[derive(Debug, Clone, PartialEq)]
pub struct WalletRow {
    pub id: i64,
    pub name: String,
    pub currency: String,
    pub initial_balance: f64,
    pub system: bool,
    pub allow_negative: bool,
    pub is_active: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct WalletDeleteResult {
    pub wallet_id: i64,
    pub action: String,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct OperationDeleteResult {
    pub deleted_records: i64,
    pub deleted_transfers: i64,
    pub skipped_records: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TransferRow {
    pub id: i64,
    pub from_wallet_id: i64,
    pub to_wallet_id: i64,
    pub date: String,
    pub amount_original: f64,
    pub currency: String,
    pub rate_at_operation: f64,
    pub amount_base: f64,
    pub description: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MandatoryExpenseRow {
    pub id: i64,
    pub wallet_id: i64,
    pub amount_original: f64,
    pub currency: String,
    pub rate_at_operation: f64,
    pub amount_base: f64,
    pub category: String,
    pub description: String,
    pub period: String,
    pub date: String,
    pub auto_pay: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RecordRow {
    pub id: i64,
    pub record_type: String,
    pub date: String,
    pub wallet_id: i64,
    pub transfer_id: Option<i64>,
    pub related_debt_id: Option<i64>,
    pub amount_original: f64,
    pub currency: String,
    pub rate_at_operation: f64,
    pub amount_base: f64,
    pub category: String,
    pub description: String,
    pub period: Option<String>,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct RecordFilterPayload {
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub wallet_id: Option<i64>,
    pub record_type: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StandaloneRecordCreatePayload {
    pub record_type: String,
    pub date: String,
    pub wallet_id: i64,
    pub amount_original: String,
    pub currency: String,
    pub rate_at_operation: String,
    pub amount_base: String,
    pub category: String,
    pub description: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StandaloneRecordUpdatePayload {
    pub record_type: String,
    pub date: String,
    pub wallet_id: i64,
    pub amount_original: String,
    pub currency: String,
    pub rate_at_operation: String,
    pub amount_base: String,
    pub category: String,
    pub description: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TransferCreatePayload {
    pub from_wallet_id: i64,
    pub to_wallet_id: i64,
    pub date: String,
    pub amount: String,
    pub currency: String,
    pub description: String,
    pub commission_amount: String,
    pub commission_currency: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TransferUpdatePayload {
    pub from_wallet_id: i64,
    pub to_wallet_id: i64,
    pub date: String,
    pub amount: String,
    pub currency: String,
    pub description: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct WalletCreatePayload {
    pub name: String,
    pub currency: String,
    pub initial_balance: String,
    pub allow_negative: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CategoryMetricRow {
    pub category: String,
    pub total_base: f64,
    pub record_count: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TagMetricRow {
    pub tag: String,
    pub color: String,
    pub total_base: f64,
    pub record_count: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TagCoverageRow {
    pub tagged_count: i64,
    pub total_count: i64,
    pub coverage_pct: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MonthlySummaryRow {
    pub month: String,
    pub income: f64,
    pub expenses: f64,
    pub cashflow: f64,
    pub savings_rate: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MonthlyCashflowRow {
    pub month: String,
    pub income: f64,
    pub expenses: f64,
    pub cashflow: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MonthlyCumulativeRow {
    pub month: String,
    pub cumulative_income: f64,
    pub cumulative_expenses: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct NetWorthDeltaRow {
    pub month: String,
    pub running_delta: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MetricsPeriodSnapshot {
    pub savings_rate: f64,
    pub burn_rate: f64,
    pub spending_by_category: Vec<CategoryMetricRow>,
    pub income_by_category: Vec<CategoryMetricRow>,
    pub spending_by_tag: Vec<TagMetricRow>,
    pub tag_coverage: TagCoverageRow,
    pub monthly_summary: Vec<MonthlySummaryRow>,
    pub monthly_cashflow: Vec<MonthlyCashflowRow>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MetricsRefreshSnapshot {
    pub savings_rate: f64,
    pub burn_rate: f64,
    pub spending_by_category: Vec<CategoryMetricRow>,
    pub income_by_category: Vec<CategoryMetricRow>,
    pub spending_by_tag: Vec<TagMetricRow>,
    pub monthly_summary: Vec<MonthlySummaryRow>,
}

mod audit;
mod metrics;
mod planning;
mod timeline;

pub use audit::{AuditFindingRow, audit_run, audit_run_for_date};
pub use metrics::{
    metrics_burn_rate, metrics_income_by_category, metrics_monthly_summary,
    metrics_period_snapshot, metrics_refresh_snapshot, metrics_savings_rate,
    metrics_spending_by_category, metrics_spending_by_tag, metrics_tag_coverage,
};
pub use planning::{
    BudgetCreatePayload, BudgetPayload, DebtPayload, DebtPaymentPayload, DebtRecalculatePayload,
    DebtRecordPayload, DistributionItemPayload, DistributionMonthlyPayload,
    DistributionSubitemPayload, DistributionValidationRow, FrozenDistributionPayload,
    budget_batch_spent_minor, budget_create, budget_delete, budget_overlap_exists,
    budget_replace_rows, budget_rows, budget_spent_minor, budget_update_limit,
    debt_create_obligation, debt_delete, debt_delete_payment, debt_payment_rows,
    debt_payment_total_minor, debt_recalculate_payload, debt_register_payment, debt_replace_rows,
    debt_rows, debt_validate_payment_amount, distribution_available_months,
    distribution_create_item, distribution_create_subitem, distribution_delete_item,
    distribution_delete_subitem, distribution_frozen_rows, distribution_history_months,
    distribution_is_month_auto_fixed, distribution_is_month_fixed, distribution_item_rows,
    distribution_monthly_payload, distribution_net_income_for_period,
    distribution_replace_frozen_rows, distribution_replace_structure, distribution_subitem_rows,
    distribution_unfreeze_month, distribution_update_item_name, distribution_update_item_order,
    distribution_update_item_pct, distribution_update_subitem_name,
    distribution_update_subitem_order, distribution_update_subitem_pct,
    distribution_validate_structure, distribution_write_frozen_row,
};
pub use timeline::{
    timeline_cumulative_income_expense, timeline_monthly_cashflow,
    timeline_net_worth_monthly_deltas,
};

pub(crate) fn sqlite_err(err: rusqlite::Error) -> String {
    format!("sqlite error: {err}")
}

fn open_sqlite_connection(db_path: &str) -> StorageResult<Connection> {
    Connection::open(db_path).map_err(sqlite_err)
}

thread_local! {
    static READ_CONNECTIONS: RefCell<HashMap<String, Connection>> = RefCell::new(HashMap::new());
}

pub(crate) fn with_cached_read_connection<T>(
    db_path: &str,
    callback: impl FnOnce(&Connection) -> StorageResult<T>,
) -> StorageResult<T> {
    READ_CONNECTIONS.with(|connections| {
        let mut connections = connections.borrow_mut();
        if !connections.contains_key(db_path) {
            connections.insert(db_path.to_owned(), open_sqlite_connection(db_path)?);
        }
        let conn = connections
            .get(db_path)
            .ok_or_else(|| "sqlite connection cache miss".to_owned())?;
        callback(conn)
    })
}

pub fn storage_clear_read_connection_cache() {
    READ_CONNECTIONS.with(|connections| {
        connections.borrow_mut().clear();
    });
}

pub(crate) fn minor_amount_expr(column: &str) -> String {
    format!(
        "CASE \
         WHEN {column}_minor IS NOT NULL \
         AND ({column}_minor != 0 OR ROUND({column}, 2) = 0) \
         THEN {column}_minor \
         ELSE CAST(ROUND({column} * 100.0) AS INTEGER) \
         END"
    )
}

pub(crate) fn signed_minor_amount_expr(column: &str, type_column: &str) -> String {
    let amount_expr = minor_amount_expr(column);
    format!("CASE WHEN {type_column} = 'income' THEN {amount_expr} ELSE -{amount_expr} END")
}

pub(crate) fn round_money(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

pub(crate) fn limit_clause(limit: Option<i64>) -> String {
    match limit {
        Some(value) if value >= 0 => format!(" LIMIT {value}"),
        _ => String::new(),
    }
}

pub(crate) fn table_has_column(
    conn: &Connection,
    table: &str,
    column: &str,
) -> StorageResult<bool> {
    let mut stmt = conn
        .prepare(&format!("PRAGMA table_info({table})"))
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| row.get::<_, String>(1))
        .map_err(sqlite_err)?;
    for row in rows {
        if row.map_err(sqlite_err)? == column {
            return Ok(true);
        }
    }
    Ok(false)
}

fn money_value_from_sql_row(
    row: &rusqlite::Row<'_>,
    real_index: usize,
    minor_index: usize,
) -> rusqlite::Result<f64> {
    let minor_value: Option<i64> = row.get(minor_index)?;
    if let Some(minor) = minor_value {
        Ok(minor_to_money_value(minor))
    } else {
        row.get::<_, f64>(real_index)
    }
}

fn rate_value_from_sql_row(
    row: &rusqlite::Row<'_>,
    real_index: usize,
    text_index: usize,
) -> rusqlite::Result<f64> {
    let rate_text = row.get::<_, Option<String>>(text_index)?;
    if let Some(text) = rate_text {
        if text.trim().is_empty() {
            row.get::<_, f64>(real_index)
        } else {
            rate_float_from_text(text.trim()).map_err(|err| {
                rusqlite::Error::FromSqlConversionFailure(
                    text_index,
                    rusqlite::types::Type::Text,
                    Box::new(std::io::Error::other(err)),
                )
            })
        }
    } else {
        row.get::<_, f64>(real_index)
    }
}

pub fn wallet_balance_parts(
    db_path: &str,
    wallet_id: i64,
    up_to_date: Option<&str>,
) -> StorageResult<Option<(f64, String, f64)>> {
    let conn = open_sqlite_connection(db_path)?;
    let wallet_row = conn
        .query_row(
            "SELECT \
                COALESCE(initial_balance_minor, CAST(ROUND(initial_balance * 100.0) AS INTEGER), 0), \
                currency \
             FROM wallets \
             WHERE id = ?1 AND is_active = 1",
            [wallet_id],
            |row| Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?)),
        )
        .optional()
        .map_err(sqlite_err)?;
    let Some((initial_minor, currency)) = wallet_row else {
        return Ok(None);
    };

    let signed_expr = signed_minor_amount_expr("amount_base", "type");
    let delta_minor = if let Some(date) = up_to_date {
        let sql = format!(
            "SELECT COALESCE(SUM({signed_expr}), 0) \
             FROM records WHERE wallet_id = ?1 AND date <= ?2"
        );
        conn.query_row(&sql, (&wallet_id, &date), |row| row.get::<_, i64>(0))
            .map_err(sqlite_err)?
    } else {
        let sql =
            format!("SELECT COALESCE(SUM({signed_expr}), 0) FROM records WHERE wallet_id = ?1");
        conn.query_row(&sql, [wallet_id], |row| row.get::<_, i64>(0))
            .map_err(sqlite_err)?
    };

    Ok(Some((
        minor_to_money_value(initial_minor),
        currency,
        minor_to_money_value(delta_minor),
    )))
}

pub fn wallet_balance_rows(
    db_path: &str,
    up_to_date: Option<&str>,
) -> StorageResult<Vec<WalletBalanceRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let signed_expr = signed_minor_amount_expr("r.amount_base", "r.type");
    let mut sql = format!(
        "SELECT \
            w.id, \
            w.name, \
            w.currency, \
            COALESCE(w.initial_balance_minor, CAST(ROUND(w.initial_balance * 100.0) AS INTEGER), 0) AS initial_minor, \
            COALESCE(SUM({signed_expr}), 0) AS delta_minor \
         FROM wallets AS w \
         LEFT JOIN records AS r ON r.wallet_id = w.id"
    );
    if up_to_date.is_some() {
        sql.push_str(" AND r.date <= ?1");
    }
    sql.push_str(
        " WHERE w.is_active = 1 GROUP BY w.id, w.name, w.currency, initial_minor ORDER BY w.id",
    );

    let mut stmt = conn.prepare(&sql).map_err(sqlite_err)?;
    let mapper = |row: &rusqlite::Row<'_>| -> rusqlite::Result<WalletBalanceRow> {
        let initial_minor: i64 = row.get(3)?;
        let delta_minor: i64 = row.get(4)?;
        Ok((
            row.get(0)?,
            row.get(1)?,
            row.get(2)?,
            minor_to_money_value(initial_minor),
            minor_to_money_value(delta_minor),
        ))
    };
    let mapped = if let Some(date) = up_to_date {
        stmt.query_map([date], mapper).map_err(sqlite_err)?
    } else {
        stmt.query_map([], mapper).map_err(sqlite_err)?
    };

    let mut rows = Vec::new();
    for row in mapped {
        rows.push(row.map_err(sqlite_err)?);
    }
    Ok(rows)
}

pub fn wallet_balance_row(
    db_path: &str,
    wallet_id: i64,
) -> StorageResult<Option<WalletBalanceRow>> {
    if wallet_id <= 0 {
        return Ok(None);
    }
    let conn = open_sqlite_connection(db_path)?;
    let signed_expr = signed_minor_amount_expr("r.amount_base", "r.type");
    let sql = format!(
        "SELECT \
            w.id, \
            w.name, \
            w.currency, \
            COALESCE(w.initial_balance_minor, CAST(ROUND(w.initial_balance * 100.0) AS INTEGER), 0) AS initial_minor, \
            COALESCE(SUM({signed_expr}), 0) AS delta_minor \
         FROM wallets AS w \
         LEFT JOIN records AS r ON r.wallet_id = w.id \
         WHERE w.is_active = 1 AND w.id = ?1 \
         GROUP BY w.id, w.name, w.currency, initial_minor"
    );
    conn.query_row(&sql, [wallet_id], |row| {
        let initial_minor: i64 = row.get(3)?;
        let delta_minor: i64 = row.get(4)?;
        Ok((
            row.get(0)?,
            row.get(1)?,
            row.get(2)?,
            minor_to_money_value(initial_minor),
            minor_to_money_value(delta_minor),
        ))
    })
    .optional()
    .map_err(sqlite_err)
}

pub fn cashflow_sum(
    db_path: &str,
    record_type: &str,
    start_date: &str,
    end_date: &str,
) -> StorageResult<f64> {
    let conn = open_sqlite_connection(db_path)?;
    let amount_expr = minor_amount_expr("amount_base");
    let minor_total = if record_type == "expense" {
        let sql = format!(
            "SELECT COALESCE(SUM({amount_expr}), 0) \
             FROM records \
             WHERE type IN ('expense', 'mandatory_expense') \
               AND transfer_id IS NULL \
               AND date >= ?1 AND date <= ?2"
        );
        conn.query_row(&sql, (start_date, end_date), |row| row.get::<_, i64>(0))
            .map_err(sqlite_err)?
    } else {
        let sql = format!(
            "SELECT COALESCE(SUM({amount_expr}), 0) \
             FROM records \
             WHERE type = ?1 \
               AND transfer_id IS NULL \
               AND date >= ?2 AND date <= ?3"
        );
        conn.query_row(&sql, (record_type, start_date, end_date), |row| {
            row.get::<_, i64>(0)
        })
        .map_err(sqlite_err)?
    };
    Ok(minor_to_money_value(minor_total))
}

pub fn wallet_list_rows(db_path: &str) -> StorageResult<Vec<WalletRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let mut stmt = conn
        .prepare(
            "SELECT
                id,
                name,
                currency,
                initial_balance,
                initial_balance_minor,
                system,
                allow_negative,
                is_active
             FROM wallets
             ORDER BY id",
        )
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| {
            Ok(WalletRow {
                id: row.get(0)?,
                name: row.get(1)?,
                currency: row.get(2)?,
                initial_balance: money_value_from_sql_row(row, 3, 4)?,
                system: row.get::<_, i64>(5)? != 0,
                allow_negative: row.get::<_, i64>(6)? != 0,
                is_active: row.get::<_, i64>(7)? != 0,
            })
        })
        .map_err(sqlite_err)?;

    let mut result = Vec::new();
    for row in rows {
        result.push(row.map_err(sqlite_err)?);
    }
    Ok(result)
}

pub fn create_wallet(db_path: &str, payload: &WalletCreatePayload) -> StorageResult<WalletRow> {
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    let name = payload.name.trim();
    if name.is_empty() {
        return Err("Wallet name is required".to_owned());
    }
    let currency = payload.currency.trim().to_uppercase();
    validate_currency_code(&currency)?;
    let base_currency = base_currency_code_in_tx(&tx)?;
    validate_wallet_base_currency_only(&currency, &base_currency)?;

    let initial_balance_minor = to_minor_units(&payload.initial_balance)?;
    if initial_balance_minor < 0 {
        return Err("Initial balance must be zero or a positive number".to_owned());
    }
    let initial_balance = quantize_money_text(&payload.initial_balance)?
        .parse::<f64>()
        .map_err(|_| "invalid initial_balance".to_owned())?;
    let is_first_wallet = tx
        .query_row("SELECT COUNT(*) FROM wallets", [], |row| {
            row.get::<_, i64>(0)
        })
        .map_err(sqlite_err)?
        == 0;

    tx.execute(
        "INSERT INTO wallets (
            name,
            currency,
            initial_balance,
            initial_balance_minor,
            system,
            allow_negative,
            is_active
        )
        VALUES (?1, ?2, ?3, ?4, ?5, ?6, 1)",
        (
            name,
            currency.as_str(),
            initial_balance,
            initial_balance_minor,
            i64::from(is_first_wallet),
            i64::from(payload.allow_negative),
        ),
    )
    .map_err(sqlite_err)?;
    let wallet_id = tx.last_insert_rowid();
    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    wallet_list_rows(db_path)?
        .into_iter()
        .find(|row| row.id == wallet_id)
        .ok_or_else(|| format!("Wallet not found: {wallet_id}"))
}

pub fn delete_wallet(db_path: &str, wallet_id: i64) -> StorageResult<WalletDeleteResult> {
    if wallet_id <= 0 {
        return Err("Wallet id is required".to_owned());
    }
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    let wallet = tx
        .query_row(
            "SELECT system, is_active FROM wallets WHERE id = ?1",
            [wallet_id],
            |row| Ok((row.get::<_, i64>(0)? != 0, row.get::<_, i64>(1)? != 0)),
        )
        .optional()
        .map_err(sqlite_err)?;
    let Some((system, active)) = wallet else {
        return Err(format!("Wallet not found: {wallet_id}"));
    };
    if system {
        return Err("System wallet cannot be deleted".to_owned());
    }
    if !active {
        return Err(format!("Wallet already inactive: {wallet_id}"));
    }

    let balance_minor = wallet_balance_minor_in_tx(&tx, wallet_id)?;
    if balance_minor != 0 {
        return Err("Wallet with non-zero balance cannot be deleted".to_owned());
    }

    let history_count = wallet_history_count_in_tx(&tx, wallet_id)?;
    let action = if history_count == 0 {
        tx.execute("DELETE FROM wallets WHERE id = ?1", [wallet_id])
            .map_err(sqlite_err)?;
        reset_sqlite_sequence_to_max_id_in_tx(&tx, "wallets")?;
        "hard_deleted"
    } else {
        tx.execute(
            "UPDATE wallets SET is_active = 0 WHERE id = ?1",
            [wallet_id],
        )
        .map_err(sqlite_err)?;
        "soft_deleted"
    };

    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    Ok(WalletDeleteResult {
        wallet_id,
        action: action.to_owned(),
    })
}

pub fn transfer_list_rows(db_path: &str) -> StorageResult<Vec<TransferRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let mut stmt = conn
        .prepare(
            "SELECT
                id,
                from_wallet_id,
                to_wallet_id,
                date,
                amount_original,
                amount_original_minor,
                currency,
                rate_at_operation,
                rate_at_operation_text,
                amount_base,
                amount_base_minor,
                description
             FROM transfers
             ORDER BY id",
        )
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| {
            Ok(TransferRow {
                id: row.get(0)?,
                from_wallet_id: row.get(1)?,
                to_wallet_id: row.get(2)?,
                date: row.get(3)?,
                amount_original: money_value_from_sql_row(row, 4, 5)?,
                currency: row.get(6)?,
                rate_at_operation: rate_value_from_sql_row(row, 7, 8)?,
                amount_base: money_value_from_sql_row(row, 9, 10)?,
                description: row.get(11)?,
            })
        })
        .map_err(sqlite_err)?;

    let mut result = Vec::new();
    for row in rows {
        result.push(row.map_err(sqlite_err)?);
    }
    Ok(result)
}

pub fn transfer_get_row(db_path: &str, transfer_id: i64) -> StorageResult<Option<TransferRow>> {
    if transfer_id <= 0 {
        return Ok(None);
    }
    Ok(transfer_list_rows(db_path)?
        .into_iter()
        .find(|row| row.id == transfer_id))
}

pub fn transfer_id_by_record_index(db_path: &str, index: i64) -> StorageResult<Option<i64>> {
    if index < 0 {
        return Ok(None);
    }
    let conn = open_sqlite_connection(db_path)?;
    conn.query_row(
        "SELECT transfer_id
         FROM records
         ORDER BY id
         LIMIT 1 OFFSET ?1",
        [index],
        |row| row.get::<_, Option<i64>>(0),
    )
    .optional()
    .map_err(sqlite_err)
    .map(|value| value.flatten())
}

pub fn create_transfer(
    db_path: &str,
    payload: &TransferCreatePayload,
) -> StorageResult<TransferRow> {
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    if payload.from_wallet_id <= 0 || payload.to_wallet_id <= 0 {
        return Err("Transfer wallets are required".to_owned());
    }
    if payload.from_wallet_id == payload.to_wallet_id {
        return Err("Transfer wallets must be different".to_owned());
    }
    if payload.date.trim().is_empty() {
        return Err("Transfer date is required".to_owned());
    }
    validate_ymd_date(payload.date.trim())?;

    let from_wallet = active_wallet_in_tx(&tx, payload.from_wallet_id, "source")?;
    active_wallet_in_tx(&tx, payload.to_wallet_id, "target")?;

    let base_currency = base_currency_code_in_tx(&tx)?;
    let currency = payload.currency.trim().to_uppercase();
    validate_currency_code(&currency)?;
    validate_transfer_base_currency_only(&currency, &base_currency)?;
    let commission_currency = if payload.commission_currency.trim().is_empty() {
        base_currency.clone()
    } else {
        payload.commission_currency.trim().to_uppercase()
    };
    validate_currency_code(&commission_currency)?;
    validate_transfer_base_currency_only(&commission_currency, &base_currency)?;

    let amount_minor = to_minor_units(&payload.amount)?;
    if amount_minor <= 0 {
        return Err("Transfer amount must be positive".to_owned());
    }
    let commission_text = payload.commission_amount.trim();
    let commission_minor = if commission_text.is_empty() {
        0
    } else {
        to_minor_units(commission_text)?
    };
    if commission_minor < 0 {
        return Err("Commission amount must be non-negative".to_owned());
    }
    if !from_wallet.allow_negative {
        let balance_minor = wallet_balance_minor_in_tx(&tx, payload.from_wallet_id)?;
        if balance_minor - amount_minor - commission_minor < 0 {
            return Err("Insufficient funds in source wallet".to_owned());
        }
    }

    let amount_text = quantize_money_text(&payload.amount)?;
    let amount_value = amount_text
        .parse::<f64>()
        .map_err(|_| "invalid transfer amount".to_owned())?;
    let commission_value = if commission_minor > 0 {
        quantize_money_text(commission_text)?
            .parse::<f64>()
            .map_err(|_| "invalid commission amount".to_owned())?
    } else {
        0.0
    };
    let rate_text = quantize_rate_text("1")?;
    let rate_value = rate_text
        .parse::<f64>()
        .map_err(|_| "invalid transfer rate".to_owned())?;
    let description = payload.description.trim();

    tx.execute(
        "INSERT INTO transfers (
            from_wallet_id,
            to_wallet_id,
            date,
            amount_original,
            amount_original_minor,
            currency,
            rate_at_operation,
            rate_at_operation_text,
            amount_base,
            amount_base_minor,
            description
        )
        VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        (
            payload.from_wallet_id,
            payload.to_wallet_id,
            payload.date.trim(),
            amount_value,
            amount_minor,
            currency.as_str(),
            rate_value,
            rate_text.as_str(),
            amount_value,
            amount_minor,
            description,
        ),
    )
    .map_err(sqlite_err)?;
    let transfer_id = tx.last_insert_rowid();

    insert_transfer_record_in_tx(
        &tx,
        "expense",
        payload.date.trim(),
        payload.from_wallet_id,
        Some(transfer_id),
        amount_value,
        amount_minor,
        currency.as_str(),
        rate_value,
        rate_text.as_str(),
        "Transfer",
        description,
    )?;
    insert_transfer_record_in_tx(
        &tx,
        "income",
        payload.date.trim(),
        payload.to_wallet_id,
        Some(transfer_id),
        amount_value,
        amount_minor,
        currency.as_str(),
        rate_value,
        rate_text.as_str(),
        "Transfer",
        description,
    )?;
    if commission_minor > 0 {
        insert_transfer_record_in_tx(
            &tx,
            "expense",
            payload.date.trim(),
            payload.from_wallet_id,
            None,
            commission_value,
            commission_minor,
            commission_currency.as_str(),
            rate_value,
            rate_text.as_str(),
            "Commission",
            &format!("[transfer:{transfer_id}]"),
        )?;
    }

    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    transfer_list_rows(db_path)?
        .into_iter()
        .find(|row| row.id == transfer_id)
        .ok_or_else(|| format!("Transfer not found: {transfer_id}"))
}

pub fn update_transfer(
    db_path: &str,
    transfer_id: i64,
    payload: &TransferUpdatePayload,
) -> StorageResult<TransferRow> {
    if transfer_id <= 0 {
        return Err("Transfer id is required".to_owned());
    }
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    if payload.from_wallet_id <= 0 || payload.to_wallet_id <= 0 {
        return Err("Transfer wallets are required".to_owned());
    }
    if payload.from_wallet_id == payload.to_wallet_id {
        return Err("Transfer wallets must be different".to_owned());
    }
    if payload.date.trim().is_empty() {
        return Err("Transfer date is required".to_owned());
    }
    validate_ymd_date(payload.date.trim())?;

    let from_wallet = active_wallet_in_tx(&tx, payload.from_wallet_id, "source")?;
    active_wallet_in_tx(&tx, payload.to_wallet_id, "target")?;

    let base_currency = base_currency_code_in_tx(&tx)?;
    let currency = payload.currency.trim().to_uppercase();
    validate_currency_code(&currency)?;
    validate_transfer_base_currency_only(&currency, &base_currency)?;

    let amount_minor = to_minor_units(&payload.amount)?;
    if amount_minor <= 0 {
        return Err("Transfer amount must be positive".to_owned());
    }
    let amount_text = quantize_money_text(&payload.amount)?;
    let amount_value = amount_text
        .parse::<f64>()
        .map_err(|_| "invalid transfer amount".to_owned())?;
    let rate_text = quantize_rate_text("1")?;
    let rate_value = rate_text
        .parse::<f64>()
        .map_err(|_| "invalid transfer rate".to_owned())?;
    let description = payload.description.trim();

    let existing = tx
        .query_row(
            "SELECT id FROM transfers WHERE id = ?1",
            [transfer_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()
        .map_err(sqlite_err)?;
    if existing.is_none() {
        return Err(format!("Transfer not found: {transfer_id}"));
    }

    let linked = transfer_linked_record_ids_in_tx(&tx, transfer_id)?;
    let commission_marker = format!("[transfer:{transfer_id}]");
    let commission_minor = tx
        .query_row(
            "SELECT COALESCE(SUM(COALESCE(amount_base_minor, CAST(ROUND(amount_base * 100.0) AS INTEGER))), 0)
             FROM records
             WHERE transfer_id IS NULL
               AND description = ?1",
            [commission_marker.as_str()],
            |row| row.get::<_, i64>(0),
        )
        .map_err(sqlite_err)?;

    if !from_wallet.allow_negative {
        let balance_minor = wallet_balance_minor_excluding_transfer_in_tx(
            &tx,
            payload.from_wallet_id,
            transfer_id,
        )?;
        if balance_minor - amount_minor - commission_minor < 0 {
            return Err("Insufficient funds in source wallet".to_owned());
        }
    }

    tx.execute(
        "UPDATE transfers
         SET from_wallet_id = ?1,
             to_wallet_id = ?2,
             date = ?3,
             amount_original = ?4,
             amount_original_minor = ?5,
             currency = ?6,
             rate_at_operation = ?7,
             rate_at_operation_text = ?8,
             amount_base = ?9,
             amount_base_minor = ?10,
             description = ?11
         WHERE id = ?12",
        (
            payload.from_wallet_id,
            payload.to_wallet_id,
            payload.date.trim(),
            amount_value,
            amount_minor,
            currency.as_str(),
            rate_value,
            rate_text.as_str(),
            amount_value,
            amount_minor,
            description,
            transfer_id,
        ),
    )
    .map_err(sqlite_err)?;

    tx.execute(
        "UPDATE records
         SET date = ?1,
             wallet_id = ?2,
             amount_original = ?3,
             amount_original_minor = ?4,
             currency = ?5,
             rate_at_operation = ?6,
             rate_at_operation_text = ?7,
             amount_base = ?8,
             amount_base_minor = ?9,
             category = 'Transfer',
             description = ?10
         WHERE id = ?11",
        (
            payload.date.trim(),
            payload.from_wallet_id,
            amount_value,
            amount_minor,
            currency.as_str(),
            rate_value,
            rate_text.as_str(),
            amount_value,
            amount_minor,
            description,
            linked.expense_record_id,
        ),
    )
    .map_err(sqlite_err)?;

    tx.execute(
        "UPDATE records
         SET date = ?1,
             wallet_id = ?2,
             amount_original = ?3,
             amount_original_minor = ?4,
             currency = ?5,
             rate_at_operation = ?6,
             rate_at_operation_text = ?7,
             amount_base = ?8,
             amount_base_minor = ?9,
             category = 'Transfer',
             description = ?10
         WHERE id = ?11",
        (
            payload.date.trim(),
            payload.to_wallet_id,
            amount_value,
            amount_minor,
            currency.as_str(),
            rate_value,
            rate_text.as_str(),
            amount_value,
            amount_minor,
            description,
            linked.income_record_id,
        ),
    )
    .map_err(sqlite_err)?;

    tx.execute(
        "UPDATE records
         SET date = ?1,
             wallet_id = ?2
         WHERE transfer_id IS NULL
           AND description = ?3",
        (
            payload.date.trim(),
            payload.from_wallet_id,
            commission_marker.as_str(),
        ),
    )
    .map_err(sqlite_err)?;

    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    transfer_get_row(db_path, transfer_id)?
        .ok_or_else(|| format!("Transfer not found: {transfer_id}"))
}

pub fn delete_transfer(db_path: &str, transfer_id: i64) -> StorageResult<bool> {
    if transfer_id <= 0 {
        return Err("Transfer id is required".to_owned());
    }
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    let existing = tx
        .query_row(
            "SELECT id FROM transfers WHERE id = ?1",
            [transfer_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()
        .map_err(sqlite_err)?;
    if existing.is_none() {
        return Err(format!("Transfer not found: {transfer_id}"));
    }
    delete_operations_in_tx(&tx, &[], &[transfer_id], 0)?;

    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    Ok(true)
}

pub fn delete_all_operations(db_path: &str) -> StorageResult<OperationDeleteResult> {
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    let transfer_ids = all_transfer_ids_in_tx(&tx)?;
    let standalone_record_ids = deletable_standalone_record_ids_in_tx(&tx, &transfer_ids)?;
    let skipped_records = skipped_operation_record_count_in_tx(&tx, &transfer_ids)?;
    let result =
        delete_operations_in_tx(&tx, &standalone_record_ids, &transfer_ids, skipped_records)?;

    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    Ok(result)
}

pub fn delete_operations_selection(
    db_path: &str,
    record_ids: &[i64],
    transfer_ids: &[i64],
) -> StorageResult<OperationDeleteResult> {
    if record_ids.is_empty() && transfer_ids.is_empty() {
        return Err("Select at least one operation or transfer".to_owned());
    }
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    let selected_transfer_ids = normalize_positive_ids(transfer_ids, "Transfer")?;
    for transfer_id in &selected_transfer_ids {
        ensure_transfer_exists_in_tx(&tx, *transfer_id)?;
        transfer_linked_record_ids_in_tx(&tx, *transfer_id)?;
    }
    let selected_record_ids =
        validate_selected_operation_record_ids_in_tx(&tx, record_ids, &selected_transfer_ids)?;
    let result = delete_operations_in_tx(&tx, &selected_record_ids, &selected_transfer_ids, 0)?;

    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    Ok(result)
}

fn mandatory_expense_select_sql(conn: &Connection, filter_by_id: bool) -> StorageResult<String> {
    let mut stmt = conn
        .prepare("PRAGMA table_info(mandatory_expenses)")
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| row.get::<_, String>(1))
        .map_err(sqlite_err)?;
    let mut has_date = false;
    let mut has_auto_pay = false;
    for row in rows {
        let name = row.map_err(sqlite_err)?;
        if name == "date" {
            has_date = true;
        } else if name == "auto_pay" {
            has_auto_pay = true;
        }
    }

    let mut sql = String::from(
        "SELECT
            id,
            wallet_id,
            amount_original,
            amount_original_minor,
            currency,
            rate_at_operation,
            rate_at_operation_text,
            amount_base,
            amount_base_minor,
            category,
            description,
            period",
    );
    if has_date {
        sql.push_str(",\n            date");
    } else {
        sql.push_str(",\n            NULL AS date");
    }
    if has_auto_pay {
        sql.push_str(",\n            auto_pay");
    } else {
        sql.push_str(",\n            0 AS auto_pay");
    }
    sql.push_str("\n         FROM mandatory_expenses");
    if filter_by_id {
        sql.push_str("\n         WHERE id = ?1");
    }
    sql.push_str("\n         ORDER BY id");
    Ok(sql)
}

fn mandatory_expense_row_dicts(
    conn: &Connection,
    sql: &str,
    params: &[&dyn rusqlite::ToSql],
) -> StorageResult<Vec<MandatoryExpenseRow>> {
    let mut stmt = conn.prepare(sql).map_err(sqlite_err)?;
    let rows = stmt
        .query_map(params, |row| {
            Ok(MandatoryExpenseRow {
                id: row.get(0)?,
                wallet_id: row.get(1)?,
                amount_original: money_value_from_sql_row(row, 2, 3)?,
                currency: row.get(4)?,
                rate_at_operation: rate_value_from_sql_row(row, 5, 6)?,
                amount_base: money_value_from_sql_row(row, 7, 8)?,
                category: row.get(9)?,
                description: row.get(10)?,
                period: row.get(11)?,
                date: row.get::<_, Option<String>>(12)?.unwrap_or_default(),
                auto_pay: row.get::<_, i64>(13)? != 0,
            })
        })
        .map_err(sqlite_err)?;

    let mut result = Vec::new();
    for row in rows {
        result.push(row.map_err(sqlite_err)?);
    }
    Ok(result)
}

pub fn mandatory_expense_rows(db_path: &str) -> StorageResult<Vec<MandatoryExpenseRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let sql = mandatory_expense_select_sql(&conn, false)?;
    mandatory_expense_row_dicts(&conn, &sql, &[])
}

pub fn mandatory_expense_row(
    db_path: &str,
    expense_id: i64,
) -> StorageResult<Option<MandatoryExpenseRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let sql = mandatory_expense_select_sql(&conn, true)?;
    let mut rows = mandatory_expense_row_dicts(&conn, &sql, &[&expense_id])?;
    Ok(rows.pop())
}

fn record_row_dicts(
    conn: &Connection,
    sql: &str,
    params: &[&dyn rusqlite::ToSql],
) -> StorageResult<Vec<RecordRow>> {
    let mut tags_by_record: HashMap<i64, Vec<String>> = HashMap::new();
    let mut tag_stmt = conn
        .prepare(
            "SELECT rt.record_id, t.name
             FROM record_tags AS rt
             JOIN tags AS t ON t.id = rt.tag_id
             ORDER BY rt.record_id, t.name COLLATE NOCASE, t.name",
        )
        .map_err(sqlite_err)?;
    let tag_rows = tag_stmt
        .query_map([], |row| {
            Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(sqlite_err)?;
    for row in tag_rows {
        let (record_id, tag_name) = row.map_err(sqlite_err)?;
        tags_by_record.entry(record_id).or_default().push(tag_name);
    }

    let mut stmt = conn.prepare(sql).map_err(sqlite_err)?;
    let rows = stmt
        .query_map(params, |row| {
            let record_id: i64 = row.get(0)?;
            Ok(RecordRow {
                id: record_id,
                record_type: row.get(1)?,
                date: row.get(2)?,
                wallet_id: row.get(3)?,
                transfer_id: row.get(4)?,
                related_debt_id: row.get(5)?,
                amount_original: money_value_from_sql_row(row, 6, 7)?,
                currency: row.get(8)?,
                rate_at_operation: rate_value_from_sql_row(row, 9, 10)?,
                amount_base: money_value_from_sql_row(row, 11, 12)?,
                category: row.get(13)?,
                description: row.get(14)?,
                period: row.get(15)?,
                tags: tags_by_record.remove(&record_id).unwrap_or_default(),
            })
        })
        .map_err(sqlite_err)?;

    let mut result = Vec::new();
    for row in rows {
        result.push(row.map_err(sqlite_err)?);
    }
    Ok(result)
}

const RECORD_SELECT: &str = "SELECT
    id,
    type,
    date,
    wallet_id,
    transfer_id,
    related_debt_id,
    amount_original,
    amount_original_minor,
    currency,
    rate_at_operation,
    rate_at_operation_text,
    amount_base,
    amount_base_minor,
    category,
    description,
    period
 FROM records";

pub fn record_list_rows(db_path: &str) -> StorageResult<Vec<RecordRow>> {
    let conn = open_sqlite_connection(db_path)?;
    record_row_dicts(&conn, &format!("{RECORD_SELECT} ORDER BY id"), &[])
}

pub fn filtered_record_list_rows(
    db_path: &str,
    filter: &RecordFilterPayload,
) -> StorageResult<Vec<RecordRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let mut sql = String::from(RECORD_SELECT);
    let mut clauses: Vec<String> = Vec::new();
    let mut params: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();

    if let Some(start_date) = filter
        .start_date
        .as_deref()
        .filter(|value| !value.is_empty())
    {
        clauses.push("date >= ?".to_owned());
        params.push(Box::new(start_date.to_owned()));
    }
    if let Some(end_date) = filter.end_date.as_deref().filter(|value| !value.is_empty()) {
        clauses.push("date <= ?".to_owned());
        params.push(Box::new(end_date.to_owned()));
    }
    if let Some(wallet_id) = filter.wallet_id {
        clauses.push("wallet_id = ?".to_owned());
        params.push(Box::new(wallet_id));
    }
    if let Some(record_type) = filter
        .record_type
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
    {
        clauses.push("type = ?".to_owned());
        params.push(Box::new(record_type.to_owned()));
    }

    if !clauses.is_empty() {
        sql.push_str(" WHERE ");
        sql.push_str(&clauses.join(" AND "));
    }
    sql.push_str(" ORDER BY date DESC, id DESC");

    let param_refs: Vec<&dyn rusqlite::ToSql> = params
        .iter()
        .map(|param| param.as_ref() as &dyn rusqlite::ToSql)
        .collect();
    record_row_dicts(&conn, &sql, &param_refs)
}

pub fn record_get_row(db_path: &str, record_id: i64) -> StorageResult<Option<RecordRow>> {
    let conn = open_sqlite_connection(db_path)?;
    let mut rows = record_row_dicts(
        &conn,
        &format!("{RECORD_SELECT} WHERE id = ?1"),
        &[&record_id],
    )?;
    Ok(rows.pop())
}

pub fn standalone_record_get_row(
    db_path: &str,
    record_id: i64,
) -> StorageResult<Option<RecordRow>> {
    let row = record_get_row(db_path, record_id)?;
    match row {
        Some(record) if record.transfer_id.is_none() && record.related_debt_id.is_none() => {
            Ok(Some(record))
        }
        Some(_) => Err("Only standalone records can be edited from Kotlin Operations".to_owned()),
        None => Ok(None),
    }
}

pub fn record_rows_by_tag(db_path: &str, tag_name: &str) -> StorageResult<Vec<RecordRow>> {
    let conn = open_sqlite_connection(db_path)?;
    record_row_dicts(
        &conn,
        &format!(
            "{RECORD_SELECT}
         WHERE EXISTS (
            SELECT 1
            FROM record_tags AS rt
            JOIN tags AS t ON t.id = rt.tag_id
            WHERE rt.record_id = records.id
              AND lower(t.name) = lower(?1)
         )
         ORDER BY id"
        ),
        &[&tag_name],
    )
}

pub fn create_standalone_record(
    db_path: &str,
    payload: &StandaloneRecordCreatePayload,
) -> StorageResult<RecordRow> {
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;

    let record_type = payload.record_type.trim().to_lowercase();
    if record_type != "income" && record_type != "expense" {
        return Err("Unsupported record type for Kotlin Operations MVP".to_owned());
    }
    if payload.date.trim().is_empty() {
        return Err("Record date is required".to_owned());
    }
    validate_ymd_date(payload.date.trim())?;
    if payload.wallet_id <= 0 {
        return Err("wallet_id must be positive".to_owned());
    }
    let category = payload.category.trim();
    if category.is_empty() {
        return Err("Category is required".to_owned());
    }
    let currency = payload.currency.trim().to_uppercase();
    validate_currency_code(&currency)?;
    let base_currency = base_currency_code_in_tx(&tx)?;
    validate_base_currency_only(&currency, &base_currency)?;

    let wallet_exists = tx
        .query_row(
            "SELECT 1 FROM wallets WHERE id = ?1",
            [payload.wallet_id],
            |_row| Ok(()),
        )
        .optional()
        .map_err(sqlite_err)?
        .is_some();
    if !wallet_exists {
        return Err(format!("Wallet not found: {}", payload.wallet_id));
    }

    let amount_original_minor = to_minor_units(&payload.amount_original)?;
    let amount_base_minor = to_minor_units(&payload.amount_base)?;
    if amount_original_minor <= 0 || amount_base_minor <= 0 {
        return Err("Record amount must be positive".to_owned());
    }
    let amount_original = quantize_money_text(&payload.amount_original)?
        .parse::<f64>()
        .map_err(|_| "invalid amount_original".to_owned())?;
    let amount_base = quantize_money_text(&payload.amount_base)?
        .parse::<f64>()
        .map_err(|_| "invalid amount_base".to_owned())?;
    let rate_at_operation_text = quantize_rate_text(&payload.rate_at_operation)?;
    let rate_at_operation = rate_at_operation_text
        .parse::<f64>()
        .map_err(|_| "invalid rate_at_operation".to_owned())?;
    if rate_at_operation <= 0.0 {
        return Err("rate_at_operation must be positive".to_owned());
    }

    let cursor = tx
        .execute(
            "INSERT INTO records (
                type,
                date,
                wallet_id,
                transfer_id,
                related_debt_id,
                amount_original,
                amount_original_minor,
                currency,
                rate_at_operation,
                rate_at_operation_text,
                amount_base,
                amount_base_minor,
                category,
                description,
                period
            )
            VALUES (?1, ?2, ?3, NULL, NULL, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, NULL)",
            (
                record_type.as_str(),
                payload.date.trim(),
                payload.wallet_id,
                amount_original,
                amount_original_minor,
                currency.as_str(),
                rate_at_operation,
                rate_at_operation_text.as_str(),
                amount_base,
                amount_base_minor,
                category,
                payload.description.as_str(),
            ),
        )
        .map_err(sqlite_err)?;
    if cursor != 1 {
        return Err("Failed to insert record".to_owned());
    }
    let record_id = tx.last_insert_rowid();
    replace_record_tags_in_tx(&tx, record_id, &payload.tags)?;
    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    record_get_row(db_path, record_id)?.ok_or_else(|| format!("Record not found: {record_id}"))
}

pub fn update_standalone_record(
    db_path: &str,
    record_id: i64,
    payload: &StandaloneRecordUpdatePayload,
) -> StorageResult<RecordRow> {
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;
    ensure_standalone_record_exists_in_tx(&tx, record_id)?;
    if let Some(marker) = transfer_commission_marker_in_tx(&tx, record_id)? {
        validate_transfer_commission_update(&marker, payload)?;
    }

    let record_type = payload.record_type.trim().to_lowercase();
    if record_type != "income" && record_type != "expense" {
        return Err("Unsupported record type for Kotlin Operations".to_owned());
    }
    if payload.date.trim().is_empty() {
        return Err("Record date is required".to_owned());
    }
    validate_ymd_date(payload.date.trim())?;
    if payload.wallet_id <= 0 {
        return Err("wallet_id must be positive".to_owned());
    }
    let category = payload.category.trim();
    if category.is_empty() {
        return Err("Category is required".to_owned());
    }
    let currency = payload.currency.trim().to_uppercase();
    validate_currency_code(&currency)?;
    let base_currency = base_currency_code_in_tx(&tx)?;
    validate_base_currency_only(&currency, &base_currency)?;
    let wallet_exists = tx
        .query_row(
            "SELECT 1 FROM wallets WHERE id = ?1",
            [payload.wallet_id],
            |_row| Ok(()),
        )
        .optional()
        .map_err(sqlite_err)?
        .is_some();
    if !wallet_exists {
        return Err(format!("Wallet not found: {}", payload.wallet_id));
    }

    let amount_original_minor = to_minor_units(&payload.amount_original)?;
    let amount_base_minor = to_minor_units(&payload.amount_base)?;
    if amount_original_minor <= 0 || amount_base_minor <= 0 {
        return Err("Record amount must be positive".to_owned());
    }
    let amount_original = quantize_money_text(&payload.amount_original)?
        .parse::<f64>()
        .map_err(|_| "invalid amount_original".to_owned())?;
    let amount_base = quantize_money_text(&payload.amount_base)?
        .parse::<f64>()
        .map_err(|_| "invalid amount_base".to_owned())?;
    let rate_at_operation_text = quantize_rate_text(&payload.rate_at_operation)?;
    let rate_at_operation = rate_at_operation_text
        .parse::<f64>()
        .map_err(|_| "invalid rate_at_operation".to_owned())?;
    if rate_at_operation <= 0.0 {
        return Err("rate_at_operation must be positive".to_owned());
    }

    let updated = tx
        .execute(
            "UPDATE records
             SET type = ?1,
                 date = ?2,
                 wallet_id = ?3,
                 amount_original = ?4,
                 amount_original_minor = ?5,
                 currency = ?6,
                 rate_at_operation = ?7,
                 rate_at_operation_text = ?8,
                 amount_base = ?9,
                 amount_base_minor = ?10,
                 category = ?11,
                 description = ?12
             WHERE id = ?13
               AND transfer_id IS NULL
               AND related_debt_id IS NULL",
            (
                record_type.as_str(),
                payload.date.trim(),
                payload.wallet_id,
                amount_original,
                amount_original_minor,
                currency.as_str(),
                rate_at_operation,
                rate_at_operation_text.as_str(),
                amount_base,
                amount_base_minor,
                category,
                payload.description.as_str(),
                record_id,
            ),
        )
        .map_err(sqlite_err)?;
    if updated != 1 {
        return Err(format!("Record not found: {record_id}"));
    }
    replace_record_tags_in_tx(&tx, record_id, &payload.tags)?;
    tx.commit().map_err(sqlite_err)?;
    storage_clear_read_connection_cache();
    record_get_row(db_path, record_id)?.ok_or_else(|| format!("Record not found: {record_id}"))
}

pub fn delete_standalone_record(db_path: &str, record_id: i64) -> StorageResult<bool> {
    let mut conn = open_sqlite_connection(db_path)?;
    conn.pragma_update(None, "foreign_keys", "ON")
        .map_err(sqlite_err)?;
    let tx = conn.transaction().map_err(sqlite_err)?;
    ensure_standalone_record_exists_in_tx(&tx, record_id)?;
    if transfer_commission_marker_in_tx(&tx, record_id)?.is_some() {
        return Err("Transfer commission must be deleted with its transfer".to_owned());
    }
    tx.execute("DELETE FROM record_tags WHERE record_id = ?1", [record_id])
        .map_err(sqlite_err)?;
    let deleted = tx
        .execute(
            "DELETE FROM records
             WHERE id = ?1
               AND transfer_id IS NULL
               AND related_debt_id IS NULL",
            [record_id],
        )
        .map_err(sqlite_err)?;
    refresh_tag_metrics_in_tx(&tx)?;
    prune_orphan_tags_in_tx(&tx)?;
    tx.commit().map_err(sqlite_err)?;
    if deleted > 0 {
        storage_clear_read_connection_cache();
    }
    Ok(deleted > 0)
}

pub fn base_currency_code(db_path: &str) -> StorageResult<String> {
    let conn = open_sqlite_connection(db_path)?;
    base_currency_code_in_conn(&conn)
}

pub fn tag_names(db_path: &str) -> StorageResult<Vec<String>> {
    let conn = open_sqlite_connection(db_path)?;
    let mut stmt = conn
        .prepare("SELECT name FROM tags ORDER BY usage_count DESC, name COLLATE NOCASE, name")
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(sqlite_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(sqlite_err)
}

pub fn distinct_record_categories(db_path: &str, record_type: &str) -> StorageResult<Vec<String>> {
    let conn = open_sqlite_connection(db_path)?;
    let normalized_type = record_type.trim().to_lowercase();
    if normalized_type != "income" && normalized_type != "expense" {
        return Err("record_type must be income or expense".to_owned());
    }
    let mut stmt = conn
        .prepare(
            "SELECT DISTINCT category
             FROM records
             WHERE type = ?1
               AND TRIM(category) <> ''
               AND transfer_id IS NULL
               AND related_debt_id IS NULL
             ORDER BY category COLLATE NOCASE, category",
        )
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([normalized_type.as_str()], |row| row.get::<_, String>(0))
        .map_err(sqlite_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(sqlite_err)
}

fn ensure_standalone_record_exists_in_tx(
    tx: &rusqlite::Transaction<'_>,
    record_id: i64,
) -> StorageResult<()> {
    let row = tx
        .query_row(
            "SELECT transfer_id, related_debt_id FROM records WHERE id = ?1",
            [record_id],
            |row| Ok((row.get::<_, Option<i64>>(0)?, row.get::<_, Option<i64>>(1)?)),
        )
        .optional()
        .map_err(sqlite_err)?;
    match row {
        Some((None, None)) => Ok(()),
        Some(_) => Err("Only standalone records can be edited from Kotlin Operations".to_owned()),
        None => Err(format!("Record not found: {record_id}")),
    }
}

#[derive(Debug, Clone, PartialEq)]
struct TransferWallet {
    id: i64,
    allow_negative: bool,
}

#[derive(Debug, Clone, PartialEq)]
struct TransferLinkedRecordIds {
    expense_record_id: i64,
    income_record_id: i64,
}

fn transfer_linked_record_ids_in_tx(
    tx: &rusqlite::Transaction<'_>,
    transfer_id: i64,
) -> StorageResult<TransferLinkedRecordIds> {
    let mut stmt = tx
        .prepare("SELECT id, type FROM records WHERE transfer_id = ?1 ORDER BY id")
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([transfer_id], |row| {
            Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(sqlite_err)?;
    let mut linked = Vec::new();
    for row in rows {
        linked.push(row.map_err(sqlite_err)?);
    }
    if linked.len() != 2 {
        return Err(format!(
            "Transfer integrity violated for #{transfer_id}: expected 2 linked records, got {}",
            linked.len()
        ));
    }
    let expense_record_id = linked
        .iter()
        .find_map(|(id, record_type)| (record_type == "expense").then_some(*id))
        .ok_or_else(|| {
            format!("Transfer integrity violated for #{transfer_id}: requires one expense and one income")
        })?;
    let income_record_id = linked
        .iter()
        .find_map(|(id, record_type)| (record_type == "income").then_some(*id))
        .ok_or_else(|| {
            format!("Transfer integrity violated for #{transfer_id}: requires one expense and one income")
        })?;
    Ok(TransferLinkedRecordIds {
        expense_record_id,
        income_record_id,
    })
}

fn ensure_transfer_exists_in_tx(
    tx: &rusqlite::Transaction<'_>,
    transfer_id: i64,
) -> StorageResult<()> {
    let exists = tx
        .query_row(
            "SELECT 1 FROM transfers WHERE id = ?1",
            [transfer_id],
            |row| row.get::<_, i64>(0),
        )
        .optional()
        .map_err(sqlite_err)?;
    if exists.is_some() {
        Ok(())
    } else {
        Err(format!("Transfer not found: {transfer_id}"))
    }
}

fn normalize_positive_ids(ids: &[i64], label: &str) -> StorageResult<Vec<i64>> {
    let mut unique = HashSet::new();
    let mut normalized = Vec::new();
    for id in ids {
        if *id <= 0 {
            return Err(format!("{label} id is required"));
        }
        if unique.insert(*id) {
            normalized.push(*id);
        }
    }
    normalized.sort_unstable();
    Ok(normalized)
}

fn all_transfer_ids_in_tx(tx: &rusqlite::Transaction<'_>) -> StorageResult<Vec<i64>> {
    let mut stmt = tx
        .prepare("SELECT id FROM transfers ORDER BY id")
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| row.get::<_, i64>(0))
        .map_err(sqlite_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(sqlite_err)
}

fn deletable_standalone_record_ids_in_tx(
    tx: &rusqlite::Transaction<'_>,
    transfer_ids: &[i64],
) -> StorageResult<Vec<i64>> {
    let selected_transfers: HashSet<i64> = transfer_ids.iter().copied().collect();
    let mut stmt = tx
        .prepare(
            "SELECT id, description
             FROM records
             WHERE transfer_id IS NULL
               AND related_debt_id IS NULL
               AND type IN ('income', 'expense')
             ORDER BY id",
        )
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| {
            Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(sqlite_err)?;
    let mut ids = Vec::new();
    for row in rows {
        let (record_id, description) = row.map_err(sqlite_err)?;
        if transfer_marker_id(&description)
            .is_some_and(|transfer_id| selected_transfers.contains(&transfer_id))
        {
            continue;
        }
        if transfer_marker_id(&description).is_some() {
            continue;
        }
        ids.push(record_id);
    }
    Ok(ids)
}

fn skipped_operation_record_count_in_tx(
    tx: &rusqlite::Transaction<'_>,
    transfer_ids: &[i64],
) -> StorageResult<i64> {
    let selected_transfers: HashSet<i64> = transfer_ids.iter().copied().collect();
    let mut stmt = tx
        .prepare("SELECT type, transfer_id, related_debt_id, description FROM records")
        .map_err(sqlite_err)?;
    let rows = stmt
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, Option<i64>>(1)?,
                row.get::<_, Option<i64>>(2)?,
                row.get::<_, String>(3)?,
            ))
        })
        .map_err(sqlite_err)?;
    let mut skipped = 0_i64;
    for row in rows {
        let (record_type, transfer_id, related_debt_id, description) = row.map_err(sqlite_err)?;
        if related_debt_id.is_some() {
            skipped += 1;
            continue;
        }
        if let Some(transfer_id) = transfer_id {
            if !selected_transfers.contains(&transfer_id) {
                skipped += 1;
            }
            continue;
        }
        if transfer_marker_id(&description)
            .is_some_and(|marker_transfer_id| !selected_transfers.contains(&marker_transfer_id))
        {
            skipped += 1;
            continue;
        }
        if record_type != "income" && record_type != "expense" {
            skipped += 1;
        }
    }
    Ok(skipped)
}

fn validate_selected_operation_record_ids_in_tx(
    tx: &rusqlite::Transaction<'_>,
    record_ids: &[i64],
    selected_transfer_ids: &[i64],
) -> StorageResult<Vec<i64>> {
    let selected_transfers: HashSet<i64> = selected_transfer_ids.iter().copied().collect();
    let normalized = normalize_positive_ids(record_ids, "Record")?;
    let mut selected_records = Vec::new();
    for record_id in normalized {
        let row = tx
            .query_row(
                "SELECT type, transfer_id, related_debt_id, description
                 FROM records
                 WHERE id = ?1",
                [record_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, Option<i64>>(1)?,
                        row.get::<_, Option<i64>>(2)?,
                        row.get::<_, String>(3)?,
                    ))
                },
            )
            .optional()
            .map_err(sqlite_err)?;
        let Some((record_type, transfer_id, related_debt_id, description)) = row else {
            return Err(format!("Record not found: {record_id}"));
        };
        if let Some(transfer_id) = transfer_id {
            return Err(format!(
                "Select transfer #{transfer_id} instead of linked record #{record_id}"
            ));
        }
        if related_debt_id.is_some() {
            return Err("Debt-linked records cannot be deleted from Kotlin Operations".to_owned());
        }
        if record_type != "income" && record_type != "expense" {
            return Err(
                "Only standalone income and expense records can be bulk deleted".to_owned(),
            );
        }
        if let Some(marker_transfer_id) = transfer_marker_id(&description) {
            if selected_transfers.contains(&marker_transfer_id) {
                continue;
            }
            return Err("Transfer commission must be deleted with its transfer".to_owned());
        }
        selected_records.push(record_id);
    }
    Ok(selected_records)
}

fn delete_operations_in_tx(
    tx: &rusqlite::Transaction<'_>,
    record_ids: &[i64],
    transfer_ids: &[i64],
    skipped_records: i64,
) -> StorageResult<OperationDeleteResult> {
    for transfer_id in transfer_ids {
        ensure_transfer_exists_in_tx(tx, *transfer_id)?;
        transfer_linked_record_ids_in_tx(tx, *transfer_id)?;
    }

    let mut deleted_records = 0_i64;
    for record_id in record_ids {
        tx.execute("DELETE FROM record_tags WHERE record_id = ?1", [record_id])
            .map_err(sqlite_err)?;
        deleted_records += tx
            .execute(
                "DELETE FROM records
                 WHERE id = ?1
                   AND transfer_id IS NULL
                   AND related_debt_id IS NULL
                   AND type IN ('income', 'expense')",
                [record_id],
            )
            .map_err(sqlite_err)? as i64;
    }

    let mut deleted_transfers = 0_i64;
    for transfer_id in transfer_ids {
        let commission_marker = format!("[transfer:{transfer_id}]");
        tx.execute(
            "DELETE FROM record_tags
             WHERE record_id IN (
                 SELECT id FROM records
                 WHERE transfer_id = ?1
                    OR (
                        transfer_id IS NULL
                        AND related_debt_id IS NULL
                        AND category = 'Commission'
                        AND description = ?2
                    )
             )",
            (transfer_id, commission_marker.as_str()),
        )
        .map_err(sqlite_err)?;
        tx.execute("DELETE FROM records WHERE transfer_id = ?1", [transfer_id])
            .map_err(sqlite_err)?;
        tx.execute(
            "DELETE FROM records
             WHERE transfer_id IS NULL
               AND related_debt_id IS NULL
               AND category = 'Commission'
               AND description = ?1",
            [commission_marker.as_str()],
        )
        .map_err(sqlite_err)?;
        deleted_transfers += tx
            .execute("DELETE FROM transfers WHERE id = ?1", [transfer_id])
            .map_err(sqlite_err)? as i64;
    }

    refresh_tag_metrics_in_tx(tx)?;
    prune_orphan_tags_in_tx(tx)?;
    Ok(OperationDeleteResult {
        deleted_records,
        deleted_transfers,
        skipped_records,
    })
}

struct TransferCommissionMarker {
    record_type: String,
    date: String,
    wallet_id: i64,
    category: String,
    description: String,
}

fn transfer_commission_marker_in_tx(
    tx: &rusqlite::Transaction<'_>,
    record_id: i64,
) -> StorageResult<Option<TransferCommissionMarker>> {
    let row = tx
        .query_row(
            "SELECT type, date, wallet_id, category, description
             FROM records
             WHERE id = ?1
               AND transfer_id IS NULL
               AND related_debt_id IS NULL",
            [record_id],
            |row| {
                Ok(TransferCommissionMarker {
                    record_type: row.get(0)?,
                    date: row.get(1)?,
                    wallet_id: row.get(2)?,
                    category: row.get(3)?,
                    description: row.get(4)?,
                })
            },
        )
        .optional()
        .map_err(sqlite_err)?;
    Ok(row.filter(|row| transfer_marker_id(&row.description).is_some()))
}

fn transfer_marker_id(description: &str) -> Option<i64> {
    let marker = description.trim();
    let id_text = marker
        .strip_prefix("[transfer:")
        .and_then(|value| value.strip_suffix(']'))?;
    let id = id_text.parse::<i64>().ok()?;
    (id > 0).then_some(id)
}

fn validate_transfer_commission_update(
    marker: &TransferCommissionMarker,
    payload: &StandaloneRecordUpdatePayload,
) -> StorageResult<()> {
    if payload.record_type.trim().to_lowercase() != marker.record_type
        || payload.date.trim() != marker.date
        || payload.wallet_id != marker.wallet_id
        || payload.category.trim() != marker.category
        || payload.description.trim() != marker.description
    {
        return Err(
            "Transfer commission date, wallet, type, category, and marker description are controlled by the transfer"
                .to_owned(),
        );
    }
    Ok(())
}

fn active_wallet_in_tx(
    tx: &rusqlite::Transaction<'_>,
    wallet_id: i64,
    role: &str,
) -> StorageResult<TransferWallet> {
    let wallet = tx
        .query_row(
            "SELECT id, allow_negative, is_active FROM wallets WHERE id = ?1",
            [wallet_id],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)? != 0,
                    row.get::<_, i64>(2)? != 0,
                ))
            },
        )
        .optional()
        .map_err(sqlite_err)?;
    let Some((id, allow_negative, is_active)) = wallet else {
        return Err(format!("Transfer {role} wallet not found"));
    };
    if !is_active {
        return Err(format!("Transfer {role} wallet is inactive"));
    }
    Ok(TransferWallet { id, allow_negative })
}

fn wallet_balance_minor_in_tx(
    tx: &rusqlite::Transaction<'_>,
    wallet_id: i64,
) -> StorageResult<i64> {
    let initial_minor = tx
        .query_row(
            "SELECT COALESCE(initial_balance_minor, CAST(ROUND(initial_balance * 100.0) AS INTEGER), 0)
             FROM wallets
             WHERE id = ?1 AND is_active = 1",
            [wallet_id],
            |row| row.get::<_, i64>(0),
        )
        .map_err(sqlite_err)?;
    let signed_expr = signed_minor_amount_expr("amount_base", "type");
    let sql = format!("SELECT COALESCE(SUM({signed_expr}), 0) FROM records WHERE wallet_id = ?1");
    let delta_minor = tx
        .query_row(&sql, [wallet_id], |row| row.get::<_, i64>(0))
        .map_err(sqlite_err)?;
    Ok(initial_minor + delta_minor)
}

fn wallet_history_count_in_tx(
    tx: &rusqlite::Transaction<'_>,
    wallet_id: i64,
) -> StorageResult<i64> {
    let records_count = tx
        .query_row(
            "SELECT COUNT(*) FROM records WHERE wallet_id = ?1",
            [wallet_id],
            |row| row.get::<_, i64>(0),
        )
        .map_err(sqlite_err)?;
    let transfer_count = tx
        .query_row(
            "SELECT COUNT(*) FROM transfers WHERE from_wallet_id = ?1 OR to_wallet_id = ?1",
            [wallet_id],
            |row| row.get::<_, i64>(0),
        )
        .map_err(sqlite_err)?;
    let mandatory_count = tx
        .query_row(
            "SELECT COUNT(*) FROM mandatory_expenses WHERE wallet_id = ?1",
            [wallet_id],
            |row| row.get::<_, i64>(0),
        )
        .map_err(sqlite_err)?;
    Ok(records_count + transfer_count + mandatory_count)
}

fn reset_sqlite_sequence_to_max_id_in_tx(
    tx: &rusqlite::Transaction<'_>,
    table: &str,
) -> StorageResult<()> {
    let has_sequence = tx
        .query_row(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'",
            [],
            |_row| Ok(()),
        )
        .optional()
        .map_err(sqlite_err)?
        .is_some();
    if !has_sequence {
        return Ok(());
    }
    let max_id_sql = format!("SELECT COALESCE(MAX(id), 0) FROM {table}");
    let max_id = tx
        .query_row(&max_id_sql, [], |row| row.get::<_, i64>(0))
        .map_err(sqlite_err)?;
    tx.execute("DELETE FROM sqlite_sequence WHERE name = ?1", [table])
        .map_err(sqlite_err)?;
    if max_id > 0 {
        tx.execute(
            "INSERT INTO sqlite_sequence(name, seq) VALUES(?1, ?2)",
            (table, max_id),
        )
        .map_err(sqlite_err)?;
    }
    Ok(())
}

fn wallet_balance_minor_excluding_transfer_in_tx(
    tx: &rusqlite::Transaction<'_>,
    wallet_id: i64,
    transfer_id: i64,
) -> StorageResult<i64> {
    let initial_minor = tx
        .query_row(
            "SELECT COALESCE(initial_balance_minor, CAST(ROUND(initial_balance * 100.0) AS INTEGER), 0)
             FROM wallets
             WHERE id = ?1 AND is_active = 1",
            [wallet_id],
            |row| row.get::<_, i64>(0),
        )
        .map_err(sqlite_err)?;
    let signed_expr = signed_minor_amount_expr("amount_base", "type");
    let marker = format!("[transfer:{transfer_id}]");
    let sql = format!(
        "SELECT COALESCE(SUM({signed_expr}), 0)
         FROM records
         WHERE wallet_id = ?1
           AND (transfer_id IS NULL OR transfer_id != ?2)
          AND NOT (transfer_id IS NULL AND description = ?3)"
    );
    let delta_minor = tx
        .query_row(&sql, (wallet_id, transfer_id, marker.as_str()), |row| {
            row.get::<_, i64>(0)
        })
        .map_err(sqlite_err)?;
    Ok(initial_minor + delta_minor)
}

#[allow(clippy::too_many_arguments)]
fn insert_transfer_record_in_tx(
    tx: &rusqlite::Transaction<'_>,
    record_type: &str,
    date: &str,
    wallet_id: i64,
    transfer_id: Option<i64>,
    amount_value: f64,
    amount_minor: i64,
    currency: &str,
    rate_value: f64,
    rate_text: &str,
    category: &str,
    description: &str,
) -> StorageResult<()> {
    tx.execute(
        "INSERT INTO records (
            type,
            date,
            wallet_id,
            transfer_id,
            related_debt_id,
            amount_original,
            amount_original_minor,
            currency,
            rate_at_operation,
            rate_at_operation_text,
            amount_base,
            amount_base_minor,
            category,
            description,
            period
        )
        VALUES (?1, ?2, ?3, ?4, NULL, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, NULL)",
        (
            record_type,
            date,
            wallet_id,
            transfer_id,
            amount_value,
            amount_minor,
            currency,
            rate_value,
            rate_text,
            amount_value,
            amount_minor,
            category,
            description,
        ),
    )
    .map_err(sqlite_err)?;
    Ok(())
}

fn base_currency_code_in_tx(tx: &rusqlite::Transaction<'_>) -> StorageResult<String> {
    let has_schema_meta = tx
        .query_row(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'",
            [],
            |_row| Ok(()),
        )
        .optional()
        .map_err(sqlite_err)?
        .is_some();
    if !has_schema_meta {
        return Ok("KZT".to_owned());
    }
    let value = tx
        .query_row(
            "SELECT value FROM schema_meta WHERE key = 'base_currency' LIMIT 1",
            [],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(sqlite_err)?
        .unwrap_or_else(|| "KZT".to_owned());
    normalize_base_currency_code(&value)
}

fn base_currency_code_in_conn(conn: &Connection) -> StorageResult<String> {
    let has_schema_meta = conn
        .query_row(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'",
            [],
            |_row| Ok(()),
        )
        .optional()
        .map_err(sqlite_err)?
        .is_some();
    if !has_schema_meta {
        return Ok("KZT".to_owned());
    }
    let value = conn
        .query_row(
            "SELECT value FROM schema_meta WHERE key = 'base_currency' LIMIT 1",
            [],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(sqlite_err)?
        .unwrap_or_else(|| "KZT".to_owned());
    normalize_base_currency_code(&value)
}

fn normalize_base_currency_code(value: &str) -> StorageResult<String> {
    let normalized = value.trim().to_uppercase();
    if normalized.is_empty() {
        return Ok("KZT".to_owned());
    }
    validate_currency_code(&normalized)?;
    Ok(normalized)
}

fn validate_base_currency_only(currency: &str, base_currency: &str) -> StorageResult<()> {
    if currency.eq_ignore_ascii_case(base_currency) {
        Ok(())
    } else {
        Err(format!(
            "Standalone Operations currently supports base-currency records only ({base_currency})"
        ))
    }
}

fn validate_transfer_base_currency_only(currency: &str, base_currency: &str) -> StorageResult<()> {
    if currency.eq_ignore_ascii_case(base_currency) {
        Ok(())
    } else {
        Err(format!(
            "Transfer flow currently supports base-currency transfers only ({base_currency})"
        ))
    }
}

fn validate_wallet_base_currency_only(currency: &str, base_currency: &str) -> StorageResult<()> {
    if currency.eq_ignore_ascii_case(base_currency) {
        Ok(())
    } else {
        Err(format!(
            "Kotlin Settings currently supports base-currency wallets only ({base_currency})"
        ))
    }
}

fn validate_ymd_date(value: &str) -> StorageResult<()> {
    let bytes = value.as_bytes();
    if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
        return Err("Date must use YYYY-MM-DD format".to_owned());
    }
    let year = parse_date_part(value, 0, 4, "year")?;
    let month = parse_date_part(value, 5, 7, "month")?;
    let day = parse_date_part(value, 8, 10, "day")?;
    if !(1..=12).contains(&month) {
        return Err("Date month must be between 01 and 12".to_owned());
    }
    let max_day = days_in_month(year, month);
    if day < 1 || day > max_day {
        return Err(format!("Date day must be between 01 and {max_day:02}"));
    }
    if (year, month, day) > current_local_date() {
        return Err("Date cannot be in the future".to_owned());
    }
    Ok(())
}

fn parse_date_part(value: &str, start: usize, end: usize, name: &str) -> StorageResult<i32> {
    let part = &value[start..end];
    if !part.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(format!("Date {name} must contain digits only"));
    }
    part.parse::<i32>()
        .map_err(|_| format!("Date {name} is invalid"))
}

fn days_in_month(year: i32, month: i32) -> i32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap_year(year) => 29,
        2 => 28,
        _ => 0,
    }
}

fn is_leap_year(year: i32) -> bool {
    year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}

fn validate_currency_code(value: &str) -> StorageResult<()> {
    if value.len() != 3 || !value.bytes().all(|byte| byte.is_ascii_alphabetic()) {
        return Err("Currency code must contain 3 letters".to_owned());
    }
    if !is_supported_currency(value) {
        return Err("Unsupported currency".to_owned());
    }
    Ok(())
}

fn is_supported_currency(value: &str) -> bool {
    matches!(
        value.to_ascii_uppercase().as_str(),
        "KZT" | "USD" | "EUR" | "RUB"
    )
}

pub fn current_local_date() -> (i32, i32, i32) {
    current_local_date_impl().unwrap_or_else(today_utc)
}

#[cfg(windows)]
fn current_local_date_impl() -> Option<(i32, i32, i32)> {
    let mut local_time = SYSTEMTIME::default();
    unsafe {
        GetLocalTime(&mut local_time);
    }
    Some((
        i32::from(local_time.wYear),
        i32::from(local_time.wMonth),
        i32::from(local_time.wDay),
    ))
}

#[cfg(unix)]
fn current_local_date_impl() -> Option<(i32, i32, i32)> {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .and_then(|duration| libc::time_t::try_from(duration.as_secs()).ok())?;
    let mut local_time = std::mem::MaybeUninit::<libc::tm>::uninit();
    let result = unsafe { libc::localtime_r(&timestamp, local_time.as_mut_ptr()) };
    if result.is_null() {
        return None;
    }
    let local_time = unsafe { local_time.assume_init() };
    Some((
        local_time.tm_year + 1900,
        local_time.tm_mon + 1,
        local_time.tm_mday,
    ))
}

#[cfg(not(any(unix, windows)))]
fn current_local_date_impl() -> Option<(i32, i32, i32)> {
    None
}

fn today_utc() -> (i32, i32, i32) {
    let days_since_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| (duration.as_secs() / 86_400) as i64)
        .unwrap_or(0);
    civil_from_days(days_since_epoch)
}

fn civil_from_days(days_since_epoch: i64) -> (i32, i32, i32) {
    let z = days_since_epoch + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = mp + if mp < 10 { 3 } else { -9 };
    let year = y + i64::from(month <= 2);
    (year as i32, month as i32, day as i32)
}

fn replace_record_tags_in_tx(
    tx: &rusqlite::Transaction<'_>,
    record_id: i64,
    tags: &[String],
) -> StorageResult<()> {
    tx.execute("DELETE FROM record_tags WHERE record_id = ?1", [record_id])
        .map_err(sqlite_err)?;
    for tag_name in normalize_tag_names(tags) {
        let tag_id = ensure_tag_id_in_tx(tx, &tag_name)?;
        tx.execute(
            "INSERT OR IGNORE INTO record_tags (record_id, tag_id) VALUES (?1, ?2)",
            (record_id, tag_id),
        )
        .map_err(sqlite_err)?;
    }
    refresh_tag_metrics_in_tx(tx)?;
    prune_orphan_tags_in_tx(tx)?;
    Ok(())
}

fn ensure_tag_id_in_tx(tx: &rusqlite::Transaction<'_>, name: &str) -> StorageResult<i64> {
    let normalized = normalize_tag_name(name);
    if normalized.is_empty() {
        return Err("Tag name must not be empty".to_owned());
    }
    let existing = tx
        .query_row(
            "SELECT id, name FROM tags WHERE lower(name) = lower(?1) LIMIT 1",
            [normalized.as_str()],
            |row| Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?)),
        )
        .optional()
        .map_err(sqlite_err)?;
    if let Some((tag_id, stored_name)) = existing {
        if stored_name != normalized {
            tx.execute(
                "UPDATE tags SET name = ?1 WHERE id = ?2",
                (normalized.as_str(), tag_id),
            )
            .map_err(sqlite_err)?;
        }
        return Ok(tag_id);
    }

    tx.execute(
        "INSERT INTO tags (name, color, usage_count, last_used_at) VALUES (?1, ?2, 0, '')",
        (normalized.as_str(), tag_color(&normalized).as_str()),
    )
    .map_err(sqlite_err)?;
    Ok(tx.last_insert_rowid())
}

fn refresh_tag_metrics_in_tx(tx: &rusqlite::Transaction<'_>) -> StorageResult<()> {
    tx.execute(
        "UPDATE tags
         SET usage_count = (
             SELECT COUNT(*) FROM record_tags WHERE record_tags.tag_id = tags.id
         ),
         last_used_at = COALESCE((
             SELECT MAX(records.date)
             FROM record_tags
             JOIN records ON records.id = record_tags.record_id
             WHERE record_tags.tag_id = tags.id
         ), '')",
        [],
    )
    .map_err(sqlite_err)?;
    Ok(())
}

fn prune_orphan_tags_in_tx(tx: &rusqlite::Transaction<'_>) -> StorageResult<()> {
    tx.execute(
        "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM record_tags)",
        [],
    )
    .map_err(sqlite_err)?;
    Ok(())
}

fn normalize_tag_names(values: &[String]) -> Vec<String> {
    let mut normalized = Vec::new();
    for value in values {
        let name = normalize_tag_name(value);
        if name.is_empty() || normalized.contains(&name) {
            continue;
        }
        normalized.push(name);
        if normalized.len() >= 3 {
            break;
        }
    }
    normalized
}

fn normalize_tag_name(value: &str) -> String {
    let stripped = value.trim().replace('#', "");
    let cleaned: String = stripped
        .chars()
        .filter(|ch| {
            ch.is_ascii_alphanumeric() || ('А'..='Я').contains(ch) || ('а'..='я').contains(ch)
        })
        .flat_map(char::to_lowercase)
        .collect();
    if cleaned.is_empty() || cleaned.chars().all(|ch| ch.is_ascii_digit()) {
        String::new()
    } else {
        cleaned
    }
}

fn tag_color(name: &str) -> String {
    const PALETTE: [&str; 6] = [
        "#5B8DEF", "#34A853", "#F2994A", "#EB5757", "#9B51E0", "#00A3A3",
    ];
    let checksum: usize = name.chars().map(|ch| ch as usize).sum();
    PALETTE[checksum % PALETTE.len()].to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;
    use std::fs;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn create_balance_test_db() -> String {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("ledgera_storage_test_{unique}.db"));
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch(
            "
            CREATE TABLE wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                currency TEXT NOT NULL,
                initial_balance REAL NOT NULL DEFAULT 0,
                initial_balance_minor INTEGER DEFAULT NULL,
                system INTEGER NOT NULL DEFAULT 0,
                allow_negative INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE transfers (
                id INTEGER PRIMARY KEY,
                from_wallet_id INTEGER NOT NULL,
                to_wallet_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount_original REAL NOT NULL,
                amount_original_minor INTEGER DEFAULT NULL,
                currency TEXT NOT NULL,
                rate_at_operation REAL NOT NULL,
                rate_at_operation_text TEXT DEFAULT NULL,
                amount_base REAL NOT NULL,
                amount_base_minor INTEGER DEFAULT NULL,
                description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE mandatory_expenses (
                id INTEGER PRIMARY KEY,
                wallet_id INTEGER NOT NULL,
                amount_original REAL NOT NULL,
                amount_original_minor INTEGER DEFAULT NULL,
                currency TEXT NOT NULL,
                rate_at_operation REAL NOT NULL,
                rate_at_operation_text TEXT DEFAULT NULL,
                amount_base REAL NOT NULL,
                amount_base_minor INTEGER DEFAULT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                period TEXT DEFAULT NULL,
                date TEXT DEFAULT NULL,
                auto_pay INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE records (
                id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                date TEXT NOT NULL,
                wallet_id INTEGER NOT NULL,
                transfer_id INTEGER DEFAULT NULL,
                related_debt_id INTEGER DEFAULT NULL,
                amount_original REAL NOT NULL DEFAULT 0,
                amount_original_minor INTEGER DEFAULT NULL,
                currency TEXT NOT NULL DEFAULT 'KZT',
                rate_at_operation REAL NOT NULL DEFAULT 1,
                rate_at_operation_text TEXT DEFAULT NULL,
                amount_base REAL NOT NULL,
                amount_base_minor INTEGER DEFAULT NULL,
                category TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                period TEXT DEFAULT NULL
            );
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '',
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT DEFAULT NULL
            );
            CREATE TABLE record_tags (
                record_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL
            );
            ",
        )
        .unwrap();
        conn.execute(
            "INSERT INTO wallets (
                id, name, currency, initial_balance, initial_balance_minor, system, allow_negative, is_active
             ) VALUES (1, 'Cash', 'KZT', 1000.0, 100000, 1, 0, 1)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO wallets (
                id, name, currency, initial_balance, initial_balance_minor, system, allow_negative, is_active
             ) VALUES (2, 'Card', 'KZT', 500.0, 50000, 0, 1, 1)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO wallets (
                id, name, currency, initial_balance, initial_balance_minor, system, allow_negative, is_active
             ) VALUES (3, 'Inactive', 'KZT', 999.0, 99900, 0, 0, 0)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO transfers (
                id, from_wallet_id, to_wallet_id, date, amount_original, amount_original_minor,
                currency, rate_at_operation, rate_at_operation_text, amount_base, amount_base_minor, description
             ) VALUES (
                1, 1, 2, '2026-01-04', 300.0, 30000,
                'KZT', 1.0, '1.000000', 300.0, 30000, 'Move to card'
             )",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO mandatory_expenses (
                id, wallet_id, amount_original, amount_original_minor, currency,
                rate_at_operation, rate_at_operation_text, amount_base, amount_base_minor,
                category, description, period, date, auto_pay
             ) VALUES (
                1, 1, 40.0, 4000, 'KZT',
                1.0, '1.000000', 40.0, 4000,
                'Rent', 'Monthly rent', 'monthly', '2026-01-15', 1
             )",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO records (id, type, date, wallet_id, transfer_id, amount_original, amount_original_minor, amount_base, amount_base_minor, category, description)
             VALUES (1, 'income', '2026-01-01', 1, NULL, 200.0, 20000, 200.0, 20000, 'Salary', 'January')",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO records (id, type, date, wallet_id, transfer_id, amount_original, amount_original_minor, amount_base, amount_base_minor, category, description)
             VALUES (2, 'expense', '2026-01-02', 1, NULL, 50.0, 5000, 50.0, 5000, 'Food', 'Groceries')",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO records (id, type, date, wallet_id, transfer_id, amount_original, amount_original_minor, amount_base, amount_base_minor, category, description)
             VALUES (3, 'mandatory_expense', '2026-01-03', 2, NULL, 25.0, 2500, 25.0, 2500, 'Rent', 'Monthly')",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO records (id, type, date, wallet_id, transfer_id, amount_original, amount_original_minor, amount_base, amount_base_minor)
             VALUES (4, 'expense', '2026-01-04', 1, 1, 300.0, 30000, 300.0, 30000)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO records (id, type, date, wallet_id, transfer_id, amount_original, amount_original_minor, amount_base, amount_base_minor)
             VALUES (5, 'income', '2026-01-04', 2, 1, 300.0, 30000, 300.0, 30000)",
            [],
        )
        .unwrap();
        conn.execute("INSERT INTO tags (id, name) VALUES (1, 'food')", [])
            .unwrap();
        conn.execute(
            "INSERT INTO record_tags (record_id, tag_id) VALUES (2, 1)",
            [],
        )
        .unwrap();
        path.to_string_lossy().into_owned()
    }

    fn remove_test_db(path: &str) {
        let _ = fs::remove_file(PathBuf::from(path));
    }

    #[test]
    fn balance_rows_return_active_wallets_only() {
        let db_path = create_balance_test_db();
        let rows = wallet_balance_rows(&db_path, Some("2026-01-03")).unwrap();
        assert_eq!(rows.len(), 2);
        assert_eq!(
            rows[0],
            (1, "Cash".to_owned(), "KZT".to_owned(), 1000.0, 150.0)
        );
        assert_eq!(
            rows[1],
            (2, "Card".to_owned(), "KZT".to_owned(), 500.0, -25.0)
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn balance_row_returns_one_active_wallet() {
        let db_path = create_balance_test_db();
        assert_eq!(
            wallet_balance_row(&db_path, 1).unwrap().unwrap(),
            (1, "Cash".to_owned(), "KZT".to_owned(), 1000.0, -150.0)
        );
        assert!(wallet_balance_row(&db_path, 3).unwrap().is_none());
        assert!(wallet_balance_row(&db_path, 99).unwrap().is_none());
        assert!(wallet_balance_row(&db_path, 0).unwrap().is_none());
        remove_test_db(&db_path);
    }

    #[test]
    fn create_wallet_creates_active_non_system_wallet_with_minor_balance() {
        let db_path = create_balance_test_db();
        let wallet = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Savings".to_owned(),
                currency: "kzt".to_owned(),
                initial_balance: "10.005".to_owned(),
                allow_negative: true,
            },
        )
        .unwrap();

        assert_eq!(wallet.id, 4);
        assert_eq!(wallet.name, "Savings");
        assert_eq!(wallet.currency, "KZT");
        assert_eq!(wallet.initial_balance, 10.01);
        assert!(!wallet.system);
        assert!(wallet.allow_negative);
        assert!(wallet.is_active);
        assert_eq!(
            wallet_balance_rows(&db_path, None)
                .unwrap()
                .into_iter()
                .find(|row| row.0 == wallet.id)
                .unwrap(),
            (4, "Savings".to_owned(), "KZT".to_owned(), 10.01, 0.0)
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn create_wallet_marks_first_wallet_as_system() {
        let db_path = create_balance_test_db();
        let conn = Connection::open(&db_path).unwrap();
        conn.execute("DELETE FROM record_tags", []).unwrap();
        conn.execute("DELETE FROM records", []).unwrap();
        conn.execute("DELETE FROM mandatory_expenses", []).unwrap();
        conn.execute("DELETE FROM transfers", []).unwrap();
        conn.execute("DELETE FROM wallets", []).unwrap();
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'wallets'", [])
            .unwrap();
        drop(conn);

        let first = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Main".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();
        let second = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Savings".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();

        assert_eq!(first.id, 1);
        assert!(first.system);
        assert_eq!(second.id, 2);
        assert!(!second.system);
        remove_test_db(&db_path);
    }

    #[test]
    fn create_wallet_allows_duplicate_names_for_python_compatibility() {
        let db_path = create_balance_test_db();

        let first = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Savings".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();
        let second = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Savings".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "5".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();

        assert_ne!(first.id, second.id);
        assert_eq!(first.name, second.name);
        remove_test_db(&db_path);
    }

    #[test]
    fn create_wallet_rejects_invalid_inputs() {
        let db_path = create_balance_test_db();
        let request = WalletCreatePayload {
            name: "Savings".to_owned(),
            currency: "KZT".to_owned(),
            initial_balance: "0".to_owned(),
            allow_negative: false,
        };

        assert!(
            create_wallet(
                &db_path,
                &WalletCreatePayload {
                    name: " ".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Wallet name is required")
        );
        assert!(
            create_wallet(
                &db_path,
                &WalletCreatePayload {
                    initial_balance: "-1".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Initial balance must be zero or a positive number")
        );
        assert!(
            create_wallet(
                &db_path,
                &WalletCreatePayload {
                    currency: "AAA".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Unsupported currency")
        );
        assert!(
            create_wallet(
                &db_path,
                &WalletCreatePayload {
                    currency: "USD".to_owned(),
                    ..request
                }
            )
            .unwrap_err()
            .contains("base-currency wallets only (KZT)")
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_wallet_hard_deletes_zero_wallet_without_history() {
        let db_path = create_balance_test_db();
        let wallet = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Mistake".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();

        let result = delete_wallet(&db_path, wallet.id).unwrap();

        assert_eq!(result.wallet_id, wallet.id);
        assert_eq!(result.action, "hard_deleted");
        assert!(
            !wallet_list_rows(&db_path)
                .unwrap()
                .iter()
                .any(|row| row.id == wallet.id)
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_wallet_hard_delete_normalizes_wallet_autoincrement_sequence() {
        let db_path = create_balance_test_db();
        let mistaken = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Mistake".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();

        assert_eq!(mistaken.id, 4);
        assert_eq!(
            delete_wallet(&db_path, mistaken.id).unwrap().action,
            "hard_deleted"
        );

        let corrected = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Corrected".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();
        assert_eq!(corrected.id, mistaken.id);
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_wallet_soft_deletes_zero_wallet_with_record_history() {
        let db_path = create_balance_test_db();
        let wallet = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Archive".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();
        let conn = Connection::open(&db_path).unwrap();
        conn.execute(
            "INSERT INTO records (type, date, wallet_id, amount_original, amount_original_minor, amount_base, amount_base_minor, category, description)
             VALUES ('income', '2026-01-05', ?1, 10.0, 1000, 10.0, 1000, 'Test', 'In')",
            [wallet.id],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO records (type, date, wallet_id, amount_original, amount_original_minor, amount_base, amount_base_minor, category, description)
             VALUES ('expense', '2026-01-06', ?1, 10.0, 1000, 10.0, 1000, 'Test', 'Out')",
            [wallet.id],
        )
        .unwrap();
        drop(conn);

        let result = delete_wallet(&db_path, wallet.id).unwrap();

        assert_eq!(result.action, "soft_deleted");
        let wallet = wallet_list_rows(&db_path)
            .unwrap()
            .into_iter()
            .find(|row| row.id == wallet.id)
            .unwrap();
        assert!(!wallet.is_active);
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_wallet_rejects_missing_system_inactive_and_non_zero_wallets() {
        let db_path = create_balance_test_db();

        assert!(
            delete_wallet(&db_path, 99)
                .unwrap_err()
                .contains("Wallet not found: 99")
        );
        assert!(
            delete_wallet(&db_path, 1)
                .unwrap_err()
                .contains("System wallet cannot be deleted")
        );
        assert!(
            delete_wallet(&db_path, 3)
                .unwrap_err()
                .contains("Wallet already inactive: 3")
        );
        assert!(
            delete_wallet(&db_path, 2)
                .unwrap_err()
                .contains("Wallet with non-zero balance cannot be deleted")
        );

        let wallet = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "Initial".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "1".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();
        assert!(
            delete_wallet(&db_path, wallet.id)
                .unwrap_err()
                .contains("Wallet with non-zero balance cannot be deleted")
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_wallet_treats_transfer_and_mandatory_rows_as_history() {
        let db_path = create_balance_test_db();
        let transfer_wallet = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "TransferArchive".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: true,
            },
        )
        .unwrap();
        let mandatory_wallet = create_wallet(
            &db_path,
            &WalletCreatePayload {
                name: "MandatoryArchive".to_owned(),
                currency: "KZT".to_owned(),
                initial_balance: "0".to_owned(),
                allow_negative: false,
            },
        )
        .unwrap();
        let conn = Connection::open(&db_path).unwrap();
        conn.execute(
            "INSERT INTO transfers (
                from_wallet_id, to_wallet_id, date, amount_original, amount_original_minor,
                currency, rate_at_operation, rate_at_operation_text, amount_base, amount_base_minor, description
             ) VALUES (?1, 1, '2026-01-07', 0.0, 0, 'KZT', 1.0, '1.000000', 0.0, 0, 'Zero transfer')",
            [transfer_wallet.id],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO mandatory_expenses (
                wallet_id, amount_original, amount_original_minor, currency, rate_at_operation,
                rate_at_operation_text, amount_base, amount_base_minor, category, description,
                period, date, auto_pay
             ) VALUES (?1, 0.0, 0, 'KZT', 1.0, '1.000000', 0.0, 0, 'Zero', 'History', 'monthly', '2026-01-08', 0)",
            [mandatory_wallet.id],
        )
        .unwrap();
        drop(conn);

        assert_eq!(
            delete_wallet(&db_path, transfer_wallet.id).unwrap().action,
            "soft_deleted"
        );
        assert_eq!(
            delete_wallet(&db_path, mandatory_wallet.id).unwrap().action,
            "soft_deleted"
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn cashflow_excludes_transfer_linked_records() {
        let db_path = create_balance_test_db();
        assert_eq!(
            cashflow_sum(&db_path, "income", "2026-01-01", "2026-01-31").unwrap(),
            200.0
        );
        assert_eq!(
            cashflow_sum(&db_path, "expense", "2026-01-01", "2026-01-31").unwrap(),
            75.0
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_update_replaces_tags_and_category_lookup_excludes_linked_rows() {
        let db_path = create_balance_test_db();
        let conn = Connection::open(&db_path).unwrap();
        conn.execute(
            "UPDATE records SET category = 'Transfer Mirror' WHERE id = 4",
            [],
        )
        .unwrap();
        drop(conn);

        let updated = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2026-02-10".to_owned(),
                wallet_id: 2,
                amount_original: "75.25".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "75.25".to_owned(),
                category: "Dining".to_owned(),
                description: "Updated dinner".to_owned(),
                tags: vec!["work".to_owned(), "dining".to_owned(), "work".to_owned()],
            },
        )
        .unwrap();

        assert_eq!(updated.date, "2026-02-10");
        assert_eq!(updated.wallet_id, 2);
        assert_eq!(updated.amount_original, 75.25);
        assert_eq!(updated.category, "Dining");
        assert_eq!(updated.description, "Updated dinner");
        assert_eq!(updated.tags, vec!["dining".to_owned(), "work".to_owned()]);
        assert_eq!(
            tag_names(&db_path).unwrap(),
            vec!["dining".to_owned(), "work".to_owned()]
        );
        assert_eq!(
            distinct_record_categories(&db_path, "expense").unwrap(),
            vec!["Dining".to_owned()]
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_create_and_update_reject_invalid_dates() {
        let db_path = create_balance_test_db();
        let create_error = create_standalone_record(
            &db_path,
            &StandaloneRecordCreatePayload {
                record_type: "income".to_owned(),
                date: "2026-13-32".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Salary".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(create_error.contains("Date month must be between 01 and 12"));

        let update_error = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2026-02-30".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Food".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("Date day must be between 01 and 28"));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_create_and_update_reject_future_dates() {
        let db_path = create_balance_test_db();
        let create_error = create_standalone_record(
            &db_path,
            &StandaloneRecordCreatePayload {
                record_type: "income".to_owned(),
                date: "2999-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Salary".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(create_error.contains("Date cannot be in the future"));

        let update_error = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2999-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Food".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("Date cannot be in the future"));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_create_and_update_reject_invalid_currency() {
        let db_path = create_balance_test_db();
        let create_error = create_standalone_record(
            &db_path,
            &StandaloneRecordCreatePayload {
                record_type: "income".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "K1T".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Salary".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(create_error.contains("Currency code must contain 3 letters"));

        let update_error = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "US1".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Food".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("Currency code must contain 3 letters"));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_create_and_update_reject_unsupported_currency() {
        let db_path = create_balance_test_db();
        let create_error = create_standalone_record(
            &db_path,
            &StandaloneRecordCreatePayload {
                record_type: "income".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "AAA".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Salary".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(create_error.contains("Unsupported currency"));

        let update_error = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "AAA".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Food".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("Unsupported currency"));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_create_and_update_reject_non_base_currency() {
        let db_path = create_balance_test_db();
        let create_error = create_standalone_record(
            &db_path,
            &StandaloneRecordCreatePayload {
                record_type: "income".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "USD".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Salary".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(create_error.contains("base-currency records only (KZT)"));

        let update_error = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10".to_owned(),
                currency: "USD".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10".to_owned(),
                category: "Food".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("base-currency records only (KZT)"));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_create_and_update_reject_non_positive_amounts() {
        let db_path = create_balance_test_db();
        let create_error = create_standalone_record(
            &db_path,
            &StandaloneRecordCreatePayload {
                record_type: "income".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "0".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "0".to_owned(),
                category: "Salary".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(create_error.contains("Record amount must be positive"));

        let update_error = update_standalone_record(
            &db_path,
            2,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "-1".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "-1".to_owned(),
                category: "Food".to_owned(),
                description: "".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("Record amount must be positive"));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_record_delete_removes_tags_and_rejects_linked_rows() {
        let db_path = create_balance_test_db();
        let conn = Connection::open(&db_path).unwrap();
        conn.execute(
            "INSERT INTO records (
                id, type, date, wallet_id, related_debt_id, amount_original,
                amount_original_minor, amount_base, amount_base_minor, category
             ) VALUES (6, 'expense', '2026-01-05', 1, 10, 20.0, 2000, 20.0, 2000, 'Debt')",
            [],
        )
        .unwrap();
        drop(conn);

        assert!(
            update_standalone_record(
                &db_path,
                4,
                &StandaloneRecordUpdatePayload {
                    record_type: "expense".to_owned(),
                    date: "2026-01-10".to_owned(),
                    wallet_id: 1,
                    amount_original: "10".to_owned(),
                    currency: "KZT".to_owned(),
                    rate_at_operation: "1".to_owned(),
                    amount_base: "10".to_owned(),
                    category: "Blocked".to_owned(),
                    description: "".to_owned(),
                    tags: vec![],
                },
            )
            .unwrap_err()
            .contains("Only standalone records")
        );
        assert!(
            delete_standalone_record(&db_path, 6)
                .unwrap_err()
                .contains("Only standalone records")
        );

        assert!(delete_standalone_record(&db_path, 2).unwrap());
        assert!(standalone_record_get_row(&db_path, 2).unwrap().is_none());
        assert!(tag_names(&db_path).unwrap().is_empty());
        remove_test_db(&db_path);
    }

    #[test]
    fn create_transfer_creates_transfer_and_linked_records() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "125.505".to_owned(),
                currency: "kzt".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "".to_owned(),
                commission_currency: "".to_owned(),
            },
        )
        .unwrap();

        assert_eq!(created.id, 2);
        assert_eq!(created.from_wallet_id, 1);
        assert_eq!(created.to_wallet_id, 2);
        assert_eq!(created.amount_original, 125.51);
        assert_eq!(created.currency, "KZT");
        assert_eq!(created.description, "Move funds");

        let linked: Vec<RecordRow> =
            filtered_record_list_rows(&db_path, &RecordFilterPayload::default())
                .unwrap()
                .into_iter()
                .filter(|record| record.transfer_id == Some(created.id))
                .collect();
        assert_eq!(linked.len(), 2);
        assert!(
            linked
                .iter()
                .any(|record| record.record_type == "expense" && record.wallet_id == 1)
        );
        assert!(
            linked
                .iter()
                .any(|record| record.record_type == "income" && record.wallet_id == 2)
        );
        assert_eq!(
            wallet_balance_rows(&db_path, None).unwrap()[0],
            (1, "Cash".to_owned(), "KZT".to_owned(), 1000.0, -275.51)
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn create_transfer_with_commission_creates_standalone_marker_record() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "kzt".to_owned(),
            },
        )
        .unwrap();

        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        let commission = rows
            .iter()
            .find(|record| {
                record.transfer_id.is_none()
                    && record.description == format!("[transfer:{}]", created.id)
            })
            .unwrap();
        assert_eq!(commission.record_type, "expense");
        assert_eq!(commission.wallet_id, 1);
        assert_eq!(commission.amount_base, 3.5);
        assert_eq!(commission.category, "Commission");
        remove_test_db(&db_path);
    }

    #[test]
    fn transfer_commission_marker_survives_standalone_amount_edit_and_transfer_delete() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "KZT".to_owned(),
            },
        )
        .unwrap();
        let marker = format!("[transfer:{}]", created.id);
        let commission = filtered_record_list_rows(&db_path, &RecordFilterPayload::default())
            .unwrap()
            .into_iter()
            .find(|record| record.transfer_id.is_none() && record.description == marker)
            .unwrap();

        let updated = update_standalone_record(
            &db_path,
            commission.id,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: commission.date,
                wallet_id: commission.wallet_id,
                amount_original: "7.25".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "7.25".to_owned(),
                category: "Commission".to_owned(),
                description: marker.clone(),
                tags: vec![],
            },
        )
        .unwrap();
        assert_eq!(updated.amount_base, 7.25);
        assert_eq!(updated.description, marker);

        assert!(delete_transfer(&db_path, created.id).unwrap());
        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        assert!(!rows.iter().any(|record| record.description == marker));
        remove_test_db(&db_path);
    }

    #[test]
    fn standalone_crud_rejects_transfer_commission_marker_detach() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "KZT".to_owned(),
            },
        )
        .unwrap();
        let marker = format!("[transfer:{}]", created.id);
        let commission = filtered_record_list_rows(&db_path, &RecordFilterPayload::default())
            .unwrap()
            .into_iter()
            .find(|record| record.transfer_id.is_none() && record.description == marker)
            .unwrap();

        let update_error = update_standalone_record(
            &db_path,
            commission.id,
            &StandaloneRecordUpdatePayload {
                record_type: "expense".to_owned(),
                date: commission.date,
                wallet_id: commission.wallet_id,
                amount_original: "7.25".to_owned(),
                currency: "KZT".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "7.25".to_owned(),
                category: "Fee".to_owned(),
                description: "edited".to_owned(),
                tags: vec![],
            },
        )
        .unwrap_err();
        assert!(update_error.contains("controlled by the transfer"));

        let delete_error = delete_standalone_record(&db_path, commission.id).unwrap_err();
        assert!(delete_error.contains("deleted with its transfer"));
        remove_test_db(&db_path);
    }

    #[test]
    fn update_transfer_updates_transfer_and_linked_records() {
        let db_path = create_balance_test_db();
        let updated = update_transfer(
            &db_path,
            1,
            &TransferUpdatePayload {
                from_wallet_id: 2,
                to_wallet_id: 1,
                date: "2026-02-10".to_owned(),
                amount: "80.255".to_owned(),
                currency: "kzt".to_owned(),
                description: "Back to cash".to_owned(),
            },
        )
        .unwrap();

        assert_eq!(updated.from_wallet_id, 2);
        assert_eq!(updated.to_wallet_id, 1);
        assert_eq!(updated.date, "2026-02-10");
        assert_eq!(updated.amount_original, 80.26);
        assert_eq!(updated.currency, "KZT");
        assert_eq!(updated.description, "Back to cash");

        let linked: Vec<RecordRow> =
            filtered_record_list_rows(&db_path, &RecordFilterPayload::default())
                .unwrap()
                .into_iter()
                .filter(|record| record.transfer_id == Some(1))
                .collect();
        assert_eq!(linked.len(), 2);
        let expense = linked
            .iter()
            .find(|record| record.record_type == "expense")
            .unwrap();
        let income = linked
            .iter()
            .find(|record| record.record_type == "income")
            .unwrap();
        assert_eq!(expense.wallet_id, 2);
        assert_eq!(income.wallet_id, 1);
        assert_eq!(expense.date, "2026-02-10");
        assert_eq!(income.amount_base, 80.26);
        assert_eq!(expense.description, "Back to cash");
        remove_test_db(&db_path);
    }

    #[test]
    fn update_transfer_moves_existing_commission_marker_without_changing_amount() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "KZT".to_owned(),
            },
        )
        .unwrap();

        update_transfer(
            &db_path,
            created.id,
            &TransferUpdatePayload {
                from_wallet_id: 2,
                to_wallet_id: 1,
                date: "2026-02-09".to_owned(),
                amount: "50".to_owned(),
                currency: "KZT".to_owned(),
                description: "Return funds".to_owned(),
            },
        )
        .unwrap();

        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        let commission = rows
            .iter()
            .find(|record| {
                record.transfer_id.is_none()
                    && record.description == format!("[transfer:{}]", created.id)
            })
            .unwrap();
        assert_eq!(commission.wallet_id, 2);
        assert_eq!(commission.date, "2026-02-09");
        assert_eq!(commission.amount_base, 3.5);
        remove_test_db(&db_path);
    }

    #[test]
    fn create_transfer_rejects_invalid_inputs() {
        let db_path = create_balance_test_db();
        let request = TransferCreatePayload {
            from_wallet_id: 1,
            to_wallet_id: 2,
            date: "2026-02-01".to_owned(),
            amount: "100".to_owned(),
            currency: "KZT".to_owned(),
            description: "".to_owned(),
            commission_amount: "0".to_owned(),
            commission_currency: "KZT".to_owned(),
        };

        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    to_wallet_id: 1,
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("must be different")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    to_wallet_id: 3,
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("target wallet is inactive")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    to_wallet_id: 99,
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("target wallet not found")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    date: "2026-02-30".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Date day must be between")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    date: "2999-01-01".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Date cannot be in the future")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    amount: "0".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Transfer amount must be positive")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    commission_amount: "-1".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Commission amount must be non-negative")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    currency: "USD".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("base-currency transfers only (KZT)")
        );
        assert!(
            create_transfer(
                &db_path,
                &TransferCreatePayload {
                    amount: "2000".to_owned(),
                    ..request
                }
            )
            .unwrap_err()
            .contains("Insufficient funds")
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn update_transfer_rejects_invalid_inputs_and_corrupted_integrity() {
        let db_path = create_balance_test_db();
        let request = TransferUpdatePayload {
            from_wallet_id: 1,
            to_wallet_id: 2,
            date: "2026-02-01".to_owned(),
            amount: "100".to_owned(),
            currency: "KZT".to_owned(),
            description: "".to_owned(),
        };

        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    to_wallet_id: 1,
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("must be different")
        );
        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    to_wallet_id: 3,
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("target wallet is inactive")
        );
        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    date: "2026-02-30".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Date day must be between")
        );
        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    date: "2999-01-01".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Date cannot be in the future")
        );
        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    amount: "0".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Transfer amount must be positive")
        );
        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    currency: "USD".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("base-currency transfers only (KZT)")
        );
        assert!(
            update_transfer(
                &db_path,
                1,
                &TransferUpdatePayload {
                    amount: "2000".to_owned(),
                    ..request.clone()
                }
            )
            .unwrap_err()
            .contains("Insufficient funds")
        );

        let conn = Connection::open(&db_path).unwrap();
        conn.execute("DELETE FROM records WHERE id = 5", [])
            .unwrap();
        drop(conn);
        assert!(
            update_transfer(&db_path, 1, &request)
                .unwrap_err()
                .contains("expected 2 linked records")
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_transfer_removes_transfer_linked_records_and_commission_marker() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "KZT".to_owned(),
            },
        )
        .unwrap();

        assert!(delete_transfer(&db_path, created.id).unwrap());

        assert!(transfer_get_row(&db_path, created.id).unwrap().is_none());
        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        assert!(
            !rows
                .iter()
                .any(|record| record.transfer_id == Some(created.id))
        );
        assert!(!rows.iter().any(|record| {
            record.transfer_id.is_none()
                && record.description == format!("[transfer:{}]", created.id)
        }));
        assert_eq!(
            wallet_balance_rows(&db_path, None)
                .unwrap()
                .into_iter()
                .find(|row| row.0 == 1)
                .unwrap(),
            (1, "Cash".to_owned(), "KZT".to_owned(), 1000.0, -150.0)
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_transfer_cleans_tags_without_deleting_unowned_marker_rows() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "KZT".to_owned(),
            },
        )
        .unwrap();
        let marker = format!("[transfer:{}]", created.id);
        let conn = Connection::open(&db_path).unwrap();
        let commission_id: i64 = conn
            .query_row(
                "SELECT id FROM records
                 WHERE transfer_id IS NULL
                   AND category = 'Commission'
                   AND description = ?1",
                [marker.as_str()],
                |row| row.get(0),
            )
            .unwrap();
        conn.execute(
            "INSERT INTO records (
                id, type, date, wallet_id, transfer_id, related_debt_id,
                amount_original, amount_original_minor, amount_base, amount_base_minor,
                category, description
             ) VALUES (
                99, 'expense', '2026-02-01', 1, NULL, NULL,
                1.0, 100, 1.0, 100, 'General', ?1
             )",
            [marker.as_str()],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO tags (id, name) VALUES (10, 'transfer-tag')",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO tags (id, name) VALUES (11, 'protected-tag')",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO record_tags (record_id, tag_id) VALUES (?1, 10)",
            [commission_id],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO record_tags (record_id, tag_id) VALUES (99, 11)",
            [],
        )
        .unwrap();
        drop(conn);

        assert!(delete_transfer(&db_path, created.id).unwrap());

        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        assert!(
            rows.iter()
                .any(|record| record.id == 99 && record.description == marker)
        );
        let conn = Connection::open(&db_path).unwrap();
        let record_tags: Vec<(i64, i64)> = {
            let mut stmt = conn
                .prepare("SELECT record_id, tag_id FROM record_tags ORDER BY record_id, tag_id")
                .unwrap();
            stmt.query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
                .unwrap()
                .collect::<Result<Vec<_>, _>>()
                .unwrap()
        };
        assert!(record_tags.contains(&(99, 11)));
        assert!(
            !record_tags
                .iter()
                .any(|(record_id, _tag_id)| *record_id == commission_id)
        );
        let tags: Vec<String> = {
            let mut stmt = conn.prepare("SELECT name FROM tags ORDER BY id").unwrap();
            stmt.query_map([], |row| row.get(0))
                .unwrap()
                .collect::<Result<Vec<_>, _>>()
                .unwrap()
        };
        assert!(tags.contains(&"food".to_owned()));
        assert!(tags.contains(&"protected-tag".to_owned()));
        assert!(!tags.contains(&"transfer-tag".to_owned()));
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_transfer_rejects_missing_and_corrupted_integrity() {
        let db_path = create_balance_test_db();

        assert!(
            delete_transfer(&db_path, 99)
                .unwrap_err()
                .contains("Transfer not found: 99")
        );

        let conn = Connection::open(&db_path).unwrap();
        conn.execute("DELETE FROM records WHERE id = 5", [])
            .unwrap();
        drop(conn);

        assert!(
            delete_transfer(&db_path, 1)
                .unwrap_err()
                .contains("expected 2 linked records")
        );
        assert!(transfer_get_row(&db_path, 1).unwrap().is_some());
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_all_operations_removes_owned_records_and_skips_unsupported_rows() {
        let db_path = create_balance_test_db();
        let created = create_transfer(
            &db_path,
            &TransferCreatePayload {
                from_wallet_id: 1,
                to_wallet_id: 2,
                date: "2026-02-01".to_owned(),
                amount: "100".to_owned(),
                currency: "KZT".to_owned(),
                description: "Move funds".to_owned(),
                commission_amount: "3.5".to_owned(),
                commission_currency: "KZT".to_owned(),
            },
        )
        .unwrap();

        let result = delete_all_operations(&db_path).unwrap();

        assert_eq!(
            result,
            OperationDeleteResult {
                deleted_records: 2,
                deleted_transfers: 2,
                skipped_records: 1,
            }
        );
        assert!(transfer_get_row(&db_path, created.id).unwrap().is_none());
        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].record_type, "mandatory_expense");
        let conn = Connection::open(&db_path).unwrap();
        let tag_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM tags", [], |row| row.get(0))
            .unwrap();
        assert_eq!(tag_count, 0);
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_operations_selection_removes_selected_records_and_transfers_only() {
        let db_path = create_balance_test_db();

        let result = delete_operations_selection(&db_path, &[2], &[1]).unwrap();

        assert_eq!(
            result,
            OperationDeleteResult {
                deleted_records: 1,
                deleted_transfers: 1,
                skipped_records: 0,
            }
        );
        let rows = filtered_record_list_rows(&db_path, &RecordFilterPayload::default()).unwrap();
        let mut ids: Vec<i64> = rows.iter().map(|record| record.id).collect();
        ids.sort_unstable();
        assert_eq!(ids, vec![1, 3]);
        assert!(transfer_get_row(&db_path, 1).unwrap().is_none());
        remove_test_db(&db_path);
    }

    #[test]
    fn delete_operations_selection_rejects_linked_rows_without_partial_delete() {
        let db_path = create_balance_test_db();

        let error = delete_operations_selection(&db_path, &[4], &[]).unwrap_err();

        assert!(error.contains("Select transfer #1 instead of linked record #4"));
        assert_eq!(
            filtered_record_list_rows(&db_path, &RecordFilterPayload::default())
                .unwrap()
                .len(),
            5
        );
        assert!(transfer_get_row(&db_path, 1).unwrap().is_some());
        remove_test_db(&db_path);
    }

    #[test]
    fn read_rows_preserve_contract() {
        let db_path = create_balance_test_db();
        assert_eq!(
            wallet_list_rows(&db_path).unwrap()[0].initial_balance,
            1000.0
        );
        assert_eq!(
            transfer_list_rows(&db_path).unwrap()[0].amount_original,
            300.0
        );
        assert_eq!(transfer_id_by_record_index(&db_path, 3).unwrap(), Some(1));
        assert_eq!(
            mandatory_expense_rows(&db_path).unwrap()[0].category,
            "Rent"
        );
        assert_eq!(record_rows_by_tag(&db_path, "food").unwrap()[0].id, 2);
        assert_eq!(
            record_get_row(&db_path, 1).unwrap().unwrap().category,
            "Salary"
        );
        remove_test_db(&db_path);
    }

    #[test]
    fn metrics_helpers_match_python_semantics() {
        let db_path = create_balance_test_db();
        assert_eq!(
            metrics_savings_rate(&db_path, "2026-01-01", "2026-01-31").unwrap(),
            62.5
        );
        assert_eq!(
            metrics_burn_rate(&db_path, "2026-01-01", "2026-01-31", 31).unwrap(),
            2.42
        );
        assert_eq!(
            metrics_spending_by_category(&db_path, "2026-01-01", "2026-01-31", Some(1)).unwrap()[0],
            CategoryMetricRow {
                category: "Food".to_owned(),
                total_base: 50.0,
                record_count: 1,
            }
        );
        assert_eq!(
            metrics_income_by_category(&db_path, "2026-01-01", "2026-01-31", None).unwrap()[0]
                .category,
            "Salary"
        );
        assert_eq!(
            metrics_spending_by_tag(&db_path, "2026-01-01", "2026-01-31", None).unwrap()[0],
            TagMetricRow {
                tag: "food".to_owned(),
                color: "".to_owned(),
                total_base: 50.0,
                record_count: 1,
            }
        );
        assert_eq!(
            metrics_tag_coverage(&db_path, "2026-01-01", "2026-01-31").unwrap(),
            TagCoverageRow {
                tagged_count: 1,
                total_count: 2,
                coverage_pct: 50.0,
            }
        );
        assert_eq!(
            metrics_monthly_summary(&db_path, None, None).unwrap()[0],
            MonthlySummaryRow {
                month: "2026-01".to_owned(),
                income: 200.0,
                expenses: 75.0,
                cashflow: 125.0,
                savings_rate: 62.5,
            }
        );
        let snapshot =
            metrics_period_snapshot(&db_path, "2026-01-01", "2026-01-31", 31, Some(1), Some(1))
                .unwrap();
        assert_eq!(snapshot.savings_rate, 62.5);
        assert_eq!(snapshot.burn_rate, 2.42);
        assert_eq!(snapshot.spending_by_category.len(), 1);
        assert_eq!(snapshot.income_by_category[0].category, "Salary");
        assert_eq!(snapshot.spending_by_tag[0].tag, "food");
        assert_eq!(snapshot.tag_coverage.coverage_pct, 50.0);
        assert_eq!(snapshot.monthly_summary[0].cashflow, 125.0);
        assert_eq!(snapshot.monthly_cashflow[0].cashflow, 125.0);
        remove_test_db(&db_path);
    }

    #[test]
    fn timeline_helpers_match_python_semantics() {
        let db_path = create_balance_test_db();
        assert_eq!(
            timeline_monthly_cashflow(&db_path, None, None).unwrap()[0],
            MonthlyCashflowRow {
                month: "2026-01".to_owned(),
                income: 200.0,
                expenses: 75.0,
                cashflow: 125.0,
            }
        );
        assert_eq!(
            timeline_cumulative_income_expense(&db_path).unwrap()[0],
            MonthlyCumulativeRow {
                month: "2026-01".to_owned(),
                cumulative_income: 200.0,
                cumulative_expenses: 75.0,
            }
        );
        assert_eq!(
            timeline_net_worth_monthly_deltas(&db_path).unwrap()[0],
            NetWorthDeltaRow {
                month: "2026-01".to_owned(),
                running_delta: 125.0,
            }
        );
        remove_test_db(&db_path);
    }
}
