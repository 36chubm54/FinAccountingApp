package app.ledgera.operations

import app.ledgera.validation.CurrencyValidation
import app.ledgera.validation.DateValidation
import app.ledgera.validation.MoneyValidation
import app.ledgera.validation.TagValidation

internal object OperationValidation {
    fun validateFields(
        type: String,
        date: String,
        walletId: Long,
        amountOriginal: String,
        currency: String,
        category: String,
        tagsText: String,
        baseCurrency: String? = null,
    ): String? {
        val normalizedType = type.trim().lowercase()
        val dateError = if (date.isBlank()) null else DateValidation.validateYmdNotFuture(date)
        val amountError = if (amountOriginal.isBlank()) null else MoneyValidation.validatePositiveAmount(amountOriginal)
        val currencyError = CurrencyValidation.validateSupportedCurrency(currency)
        val baseCurrencyError = validateBaseCurrencyOnly(currency, baseCurrency)
        val tagError = TagValidation.validateTagText(tagsText)
        return when {
            normalizedType != "income" && normalizedType != "expense" -> "Only income and expense are supported"
            date.isBlank() -> "Date is required"
            dateError != null -> dateError
            walletId <= 0 -> "Wallet is required"
            amountOriginal.isBlank() -> "Amount is required"
            amountError != null -> amountError
            currencyError != null -> currencyError
            baseCurrencyError != null -> baseCurrencyError
            category.isBlank() -> "Category is required"
            tagError != null -> tagError
            else -> null
        }
    }

    fun normalizeCurrency(value: String): String =
        CurrencyValidation.normalizeCurrencyCode(value)

    fun parseTags(value: String): List<String> =
        TagValidation.parseTagText(value)

    private fun validateBaseCurrencyOnly(currency: String, baseCurrency: String?): String? {
        val normalizedBase = baseCurrency?.trim()?.uppercase()?.takeIf { it.isNotEmpty() } ?: return null
        val normalizedCurrency = currency.trim().uppercase()
        return if (normalizedCurrency == normalizedBase) {
            null
        } else {
            "Standalone Operations currently supports base-currency records only ($normalizedBase)"
        }
    }
}
