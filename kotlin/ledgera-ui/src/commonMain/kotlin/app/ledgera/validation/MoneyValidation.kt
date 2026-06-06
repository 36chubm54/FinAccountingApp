package app.ledgera.validation

object MoneyValidation {
    fun validatePositiveAmount(value: String): String? =
        if (isPositiveMoneyAmount(value)) null else "Amount must be a positive number"

    fun validateNonNegativeAmount(value: String): String? =
        if (isNonNegativeMoneyAmount(value)) null else "Amount must be zero or a positive number"

    fun isPositiveMoneyAmount(value: String): Boolean {
        val normalized = value.trim()
        if (!isUnsignedMoneyText(normalized)) {
            return false
        }
        val unsigned = normalized.removePrefix("+")
        return roundedCents(unsigned) > 0
    }

    fun isNonNegativeMoneyAmount(value: String): Boolean {
        val normalized = value.trim()
        if (!isUnsignedMoneyText(normalized)) {
            return false
        }
        return roundedCents(normalized.removePrefix("+")) >= 0
    }

    private fun isUnsignedMoneyText(value: String): Boolean =
        Regex("\\+?(\\d+(\\.\\d*)?|\\.\\d+)").matches(value)

    private fun roundedCents(unsigned: String): Int {
        val integerPart = unsigned.substringBefore(".")
        if (integerPart.any { it != '0' }) {
            return 1
        }
        val fractionalPart = unsigned.substringAfter(".", "")
        val centDigits = fractionalPart.take(2).padEnd(2, '0')
        return centDigits.toInt() + if ((fractionalPart.getOrNull(2) ?: '0') >= '5') 1 else 0
    }
}
