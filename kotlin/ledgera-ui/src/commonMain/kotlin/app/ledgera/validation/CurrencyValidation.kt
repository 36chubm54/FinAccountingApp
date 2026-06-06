package app.ledgera.validation

object CurrencyValidation {
    private val supportedCurrencies = setOf("KZT", "USD", "EUR", "RUB")

    fun validateSupportedCurrency(value: String): String? =
        when {
            !isValidCurrencyCode(value) -> "Currency code must contain 3 letters"
            !isSupportedCurrency(value) -> "Unsupported currency"
            else -> null
        }

    fun normalizeCurrencyCode(value: String): String =
        value.trim().uppercase()

    fun isValidCurrencyCode(value: String): Boolean =
        Regex("[A-Za-z]{3}").matches(value.trim())

    fun isSupportedCurrency(value: String): Boolean =
        value.trim().uppercase() in supportedCurrencies
}
