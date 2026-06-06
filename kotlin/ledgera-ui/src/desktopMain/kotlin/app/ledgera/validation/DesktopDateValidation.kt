package app.ledgera.validation

import java.time.LocalDate

actual fun currentLedgerDate(): LedgerDate {
    val today = LocalDate.now()
    return LedgerDate(year = today.year, month = today.monthValue, day = today.dayOfMonth)
}
