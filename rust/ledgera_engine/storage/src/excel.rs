use rust_xlsxwriter::{
    Color, Format, FormatAlign, FormatBorder, FormatPattern, Workbook, Worksheet, XlsxError,
};

const MIN_COLUMN_WIDTH: usize = 12;
const MAX_COLUMN_WIDTH: usize = 32;

pub(crate) struct StyledWorksheet {
    workbook: Workbook,
    column_widths: Vec<usize>,
    amount_columns: Vec<usize>,
    row_count: u32,
}

impl StyledWorksheet {
    pub(crate) fn new_records_sheet(
        sheet_name: &str,
        headers: &[&str],
        amount_columns: &[usize],
    ) -> Result<Self, XlsxError> {
        let mut workbook = Workbook::new();
        let worksheet = workbook.add_worksheet();
        worksheet.set_name(sheet_name)?;
        worksheet.set_freeze_panes(1, 0)?;

        let header_format = header_format();
        for (column, header) in headers.iter().enumerate() {
            worksheet.write_string_with_format(0, column as u16, *header, &header_format)?;
        }

        let column_widths = headers.iter().map(|header| header.len()).collect();
        Ok(Self {
            workbook,
            column_widths,
            amount_columns: amount_columns.to_vec(),
            row_count: 1,
        })
    }

    pub(crate) fn append_row(&mut self, values: &[String]) -> Result<(), XlsxError> {
        let row = self.row_count;
        let data_format = data_format();
        let amount_format = amount_format();
        let worksheet = active_worksheet(&mut self.workbook);
        for (column, value) in values.iter().enumerate() {
            let format = if self.amount_columns.contains(&column) {
                &amount_format
            } else {
                &data_format
            };
            if self.amount_columns.contains(&column) {
                match value.parse::<f64>() {
                    Ok(number) => {
                        worksheet.write_number_with_format(row, column as u16, number, format)?;
                    }
                    Err(_) => {
                        worksheet.write_string_with_format(row, column as u16, value, format)?;
                    }
                };
            } else {
                worksheet.write_string_with_format(row, column as u16, value, format)?;
            }
            if let Some(width) = self.column_widths.get_mut(column) {
                *width = (*width).max(value.len());
            }
        }
        self.row_count += 1;
        Ok(())
    }

    pub(crate) fn save(mut self, path: &str) -> Result<(), XlsxError> {
        let last_row = self.row_count.saturating_sub(1);
        let last_col = self.column_widths.len().saturating_sub(1) as u16;
        let worksheet = active_worksheet(&mut self.workbook);
        worksheet.autofilter(0, 0, last_row, last_col)?;
        for (column, width) in self.column_widths.iter().enumerate() {
            let bounded = (*width + 2).clamp(MIN_COLUMN_WIDTH, MAX_COLUMN_WIDTH) as f64;
            worksheet.set_column_width(column as u16, bounded)?;
        }
        self.workbook.save(path)
    }
}

fn active_worksheet(workbook: &mut Workbook) -> &mut Worksheet {
    workbook.worksheet_from_index(0).expect("records worksheet exists")
}

fn header_format() -> Format {
    Format::new()
        .set_bold()
        .set_font_color(Color::White)
        .set_background_color(Color::RGB(0x1F4E78))
        .set_pattern(FormatPattern::Solid)
        .set_border(FormatBorder::Thin)
        .set_border_color(Color::RGB(0xD9D9D9))
        .set_align(FormatAlign::Left)
        .set_align(FormatAlign::VerticalCenter)
}

fn data_format() -> Format {
    Format::new()
        .set_border(FormatBorder::Thin)
        .set_border_color(Color::RGB(0xD9D9D9))
        .set_align(FormatAlign::Left)
        .set_align(FormatAlign::VerticalCenter)
}

fn amount_format() -> Format {
    data_format()
        .set_num_format("#,##0.00")
        .set_align(FormatAlign::Right)
}
