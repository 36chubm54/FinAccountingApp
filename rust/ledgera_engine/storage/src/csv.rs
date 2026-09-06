use std::collections::HashMap;
use std::fs;

pub(crate) type TabularRows = Vec<(usize, HashMap<String, String>)>;

pub(crate) fn read_csv_rows(
    path: &str,
    max_file_size: u64,
    max_rows: usize,
    file_label: &str,
) -> Result<TabularRows, String> {
    let metadata = fs::metadata(path).map_err(|error| error.to_string())?;
    if metadata.len() > max_file_size {
        return Err(format!(
            "{file_label} file is too large: {} bytes",
            metadata.len()
        ));
    }
    let mut reader = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .map_err(|error| error.to_string())?;
    let headers = reader
        .headers()
        .map_err(|error| error.to_string())?
        .iter()
        .map(normalize_tabular_key)
        .collect::<Vec<_>>();

    let mut rows = Vec::new();
    for (index, row) in reader.records().enumerate() {
        if index >= max_rows {
            return Err(format!("{file_label} exceeded row limit ({max_rows})"));
        }
        let row = row.map_err(|error| error.to_string())?;
        rows.push((index + 2, csv_row_values(&headers, &row)));
    }
    Ok(rows)
}

pub(crate) fn write_csv_rows(
    path: &str,
    headers: &[&str],
    rows: &[Vec<String>],
) -> Result<i64, String> {
    let mut writer = csv::Writer::from_path(path).map_err(|error| error.to_string())?;
    writer
        .write_record(headers)
        .map_err(|error| error.to_string())?;
    for row in rows {
        writer
            .write_record(row)
            .map_err(|error| error.to_string())?;
    }
    writer.flush().map_err(|error| error.to_string())?;
    Ok(i64::try_from(rows.len()).unwrap_or(i64::MAX))
}

pub(crate) fn normalize_tabular_key(value: &str) -> String {
    value
        .trim()
        .trim_start_matches('\u{feff}')
        .to_lowercase()
        .replace(' ', "_")
}

fn csv_row_values(headers: &[String], row: &csv::StringRecord) -> HashMap<String, String> {
    let mut values = HashMap::new();
    for (index, header) in headers.iter().enumerate() {
        values.insert(
            header.clone(),
            row.get(index).unwrap_or("").trim().to_owned(),
        );
    }
    values
}
