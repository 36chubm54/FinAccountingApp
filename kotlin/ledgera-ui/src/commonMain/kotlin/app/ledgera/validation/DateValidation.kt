package app.ledgera.validation

data class LedgerDate(
    val year: Int,
    val month: Int,
    val day: Int,
) : Comparable<LedgerDate> {
    override fun compareTo(other: LedgerDate): Int =
        when {
            year != other.year -> year.compareTo(other.year)
            month != other.month -> month.compareTo(other.month)
            else -> day.compareTo(other.day)
        }
}

expect fun currentLedgerDate(): LedgerDate

object DateValidation {
    fun validateYmdNotFuture(value: String, today: LedgerDate = currentLedgerDate()): String? {
        val parsed = parseYmd(value) ?: return "Date must use a valid YYYY-MM-DD value"
        return if (parsed > today) "Date cannot be in the future" else null
    }

    fun parseYmd(value: String): LedgerDate? {
        if (!Regex("\\d{4}-\\d{2}-\\d{2}").matches(value)) {
            return null
        }
        val year = value.substring(0, 4).toInt()
        val month = value.substring(5, 7).toInt()
        val day = value.substring(8, 10).toInt()
        if (month !in 1..12) {
            return null
        }
        if (day !in 1..daysInMonth(year, month)) {
            return null
        }
        return LedgerDate(year = year, month = month, day = day)
    }

    private fun daysInMonth(year: Int, month: Int): Int =
        when (month) {
            1, 3, 5, 7, 8, 10, 12 -> 31
            4, 6, 9, 11 -> 30
            2 -> if (isLeapYear(year)) 29 else 28
            else -> 0
        }

    private fun isLeapYear(year: Int): Boolean =
        year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}
