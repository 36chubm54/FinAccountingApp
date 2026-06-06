package app.ledgera.validation

object MoneyValidation {
    fun validatePositiveAmount(value: String): String? =
        if (isPositiveMoneyAmount(value)) null else "Amount must be a positive number"

    fun isPositiveMoneyAmount(value: String): Boolean {
        val normalized = value.trim()
        if (!Regex("\\+?(\\d+(\\.\\d*)?|\\.\\d+)").matches(normalized)) {
            return false
        }
        val unsigned = normalized.removePrefix("+")
        val integerPart = unsigned.substringBefore(".")
        if (integerPart.any { it != '0' }) {
            return true
        }
        val fractionalPart = unsigned.substringAfter(".", "")
        val centDigits = fractionalPart.take(2).padEnd(2, '0')
        val roundedCents = centDigits.toInt() + if ((fractionalPart.getOrNull(2) ?: '0') >= '5') 1 else 0
        return roundedCents > 0
    }
}
