package app.ledgera.validation

import kotlin.test.Test
import kotlin.test.assertEquals

class DateValidationTest {
    @Test
    fun validateYmdNotFutureRejectsFutureDate() {
        val today = LedgerDate(year = 2026, month = 6, day = 6)

        assertEquals(
            "Date cannot be in the future",
            DateValidation.validateYmdNotFuture("2026-06-07", today),
        )
    }

    @Test
    fun validateYmdNotFutureRejectsInvalidCalendarDate() {
        val today = LedgerDate(year = 2026, month = 6, day = 6)

        assertEquals(
            "Date must use a valid YYYY-MM-DD value",
            DateValidation.validateYmdNotFuture("2026-02-30", today),
        )
    }

    @Test
    fun validateYmdNotFutureAcceptsTodayAndPastDates() {
        val today = LedgerDate(year = 2026, month = 6, day = 6)

        assertEquals(null, DateValidation.validateYmdNotFuture("2026-06-06", today))
        assertEquals(null, DateValidation.validateYmdNotFuture("2026-06-05", today))
    }
}
