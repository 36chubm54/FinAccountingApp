use ledgera_engine_storage::{
    RecordFilterPayload, RecordRow, StandaloneRecordCreatePayload, WalletBalanceRow, WalletRow,
    create_standalone_record, filtered_record_list_rows, wallet_balance_rows, wallet_list_rows,
};
use std::fmt;
use std::path::Path;

uniffi::include_scaffolding!("ledgera_engine");

#[derive(Debug, Clone, PartialEq)]
pub struct RecordFilterDto {
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub wallet_id: Option<i64>,
    pub record_type: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CreateRecordRequest {
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
pub struct RecordDto {
    pub id: i64,
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
pub struct WalletDto {
    pub id: i64,
    pub name: String,
    pub currency: String,
    pub initial_balance: String,
    pub system: bool,
    pub allow_negative: bool,
    pub is_active: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct WalletBalanceDto {
    pub wallet_id: i64,
    pub name: String,
    pub currency: String,
    pub balance: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct EngineStatusDto {
    pub ok: bool,
    pub db_path: String,
    pub message: String,
}

#[derive(Debug)]
pub enum LedgeraEngineError {
    Validation { message: String },
    Storage { message: String },
}

impl fmt::Display for LedgeraEngineError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Validation { message } | Self::Storage { message } => {
                formatter.write_str(message)
            }
        }
    }
}

impl std::error::Error for LedgeraEngineError {}

pub struct LedgeraEngine {
    db_path: String,
}

impl LedgeraEngine {
    pub fn new(db_path: String) -> Self {
        Self { db_path }
    }

    pub fn engine_status(&self) -> EngineStatusDto {
        let ok = Path::new(&self.db_path).exists();
        EngineStatusDto {
            ok,
            db_path: self.db_path.clone(),
            message: if ok {
                "ready".to_owned()
            } else {
                "database file does not exist".to_owned()
            },
        }
    }

    pub fn list_records(
        &self,
        filter: RecordFilterDto,
    ) -> Result<Vec<RecordDto>, LedgeraEngineError> {
        let payload = RecordFilterPayload {
            start_date: filter.start_date,
            end_date: filter.end_date,
            wallet_id: filter.wallet_id,
            record_type: filter.record_type,
        };
        filtered_record_list_rows(&self.db_path, &payload)
            .map(|rows| rows.into_iter().map(record_to_dto).collect())
            .map_err(storage_error)
    }

    pub fn create_record(
        &self,
        request: CreateRecordRequest,
    ) -> Result<RecordDto, LedgeraEngineError> {
        validate_create_request(&request)?;
        let payload = StandaloneRecordCreatePayload {
            record_type: request.record_type,
            date: request.date,
            wallet_id: request.wallet_id,
            amount_original: request.amount_original,
            currency: request.currency,
            rate_at_operation: request.rate_at_operation,
            amount_base: request.amount_base,
            category: request.category,
            description: request.description,
            tags: request.tags,
        };
        create_standalone_record(&self.db_path, &payload)
            .map(record_to_dto)
            .map_err(storage_error)
    }

    pub fn list_wallets(&self) -> Result<Vec<WalletDto>, LedgeraEngineError> {
        wallet_list_rows(&self.db_path)
            .map(|rows| rows.into_iter().map(wallet_to_dto).collect())
            .map_err(storage_error)
    }

    pub fn wallet_balances(&self) -> Result<Vec<WalletBalanceDto>, LedgeraEngineError> {
        wallet_balance_rows(&self.db_path, None)
            .map(|rows| rows.into_iter().map(wallet_balance_to_dto).collect())
            .map_err(storage_error)
    }

    pub fn wallet_balance(
        &self,
        wallet_id: i64,
    ) -> Result<Option<WalletBalanceDto>, LedgeraEngineError> {
        Ok(self
            .wallet_balances()?
            .into_iter()
            .find(|row| row.wallet_id == wallet_id))
    }
}

fn validate_create_request(request: &CreateRecordRequest) -> Result<(), LedgeraEngineError> {
    let record_type = request.record_type.trim().to_lowercase();
    if record_type != "income" && record_type != "expense" {
        return Err(validation_error(
            "Only income and expense records are supported in alpha.4 Operations",
        ));
    }
    if request.date.trim().is_empty() {
        return Err(validation_error("Record date is required"));
    }
    if request.wallet_id <= 0 {
        return Err(validation_error("wallet_id must be positive"));
    }
    if request.category.trim().is_empty() {
        return Err(validation_error("Category is required"));
    }
    Ok(())
}

fn record_to_dto(row: RecordRow) -> RecordDto {
    RecordDto {
        id: row.id,
        record_type: row.record_type,
        date: row.date,
        wallet_id: row.wallet_id,
        amount_original: format_money(row.amount_original),
        currency: row.currency,
        rate_at_operation: format_rate(row.rate_at_operation),
        amount_base: format_money(row.amount_base),
        category: row.category,
        description: row.description,
        tags: row.tags,
    }
}

fn wallet_to_dto(row: WalletRow) -> WalletDto {
    WalletDto {
        id: row.id,
        name: row.name,
        currency: row.currency,
        initial_balance: format_money(row.initial_balance),
        system: row.system,
        allow_negative: row.allow_negative,
        is_active: row.is_active,
    }
}

fn wallet_balance_to_dto(row: WalletBalanceRow) -> WalletBalanceDto {
    WalletBalanceDto {
        wallet_id: row.0,
        name: row.1,
        currency: row.2,
        balance: format_money(row.4),
    }
}

fn format_money(value: f64) -> String {
    format!("{value:.2}")
}

fn format_rate(value: f64) -> String {
    format!("{value:.6}")
}

fn storage_error(message: String) -> LedgeraEngineError {
    LedgeraEngineError::Storage { message }
}

fn validation_error(message: &str) -> LedgeraEngineError {
    LedgeraEngineError::Validation {
        message: message.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn fixture_db() -> String {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("ledgera_kotlin_ffi_{unique}.db"));
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
            CREATE TABLE records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                date TEXT NOT NULL,
                wallet_id INTEGER NOT NULL,
                transfer_id INTEGER,
                related_debt_id INTEGER DEFAULT NULL,
                amount_original REAL NOT NULL,
                amount_original_minor INTEGER DEFAULT NULL,
                currency TEXT NOT NULL,
                rate_at_operation REAL NOT NULL,
                rate_at_operation_text TEXT DEFAULT NULL,
                amount_base REAL NOT NULL,
                amount_base_minor INTEGER DEFAULT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                period TEXT,
                FOREIGN KEY(wallet_id) REFERENCES wallets(id)
            );
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '',
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE record_tags (
                record_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY(record_id, tag_id)
            );
            INSERT INTO wallets (id, name, currency, initial_balance, initial_balance_minor, is_active)
            VALUES (1, 'Main', 'KZT', 100.0, 10000, 1);
            ",
        )
        .unwrap();
        path.to_string_lossy().to_string()
    }

    #[test]
    fn engine_creates_and_lists_standalone_record() {
        let db_path = fixture_db();
        let engine = LedgeraEngine::new(db_path.clone());
        let created = engine
            .create_record(CreateRecordRequest {
                record_type: "income".to_owned(),
                date: "2026-01-01".to_owned(),
                wallet_id: 1,
                amount_original: "10.005".to_owned(),
                currency: "kzt".to_owned(),
                rate_at_operation: "1".to_owned(),
                amount_base: "10.005".to_owned(),
                category: "Salary".to_owned(),
                description: "Alpha".to_owned(),
                tags: vec!["Work".to_owned(), "123".to_owned()],
            })
            .unwrap();
        assert_eq!(created.amount_base, "10.01");
        assert_eq!(created.tags, vec!["work"]);

        let rows = engine
            .list_records(RecordFilterDto {
                start_date: None,
                end_date: None,
                wallet_id: Some(1),
                record_type: Some("income".to_owned()),
            })
            .unwrap();
        assert_eq!(rows, vec![created]);
        fs::remove_file(db_path).ok();
    }
}
