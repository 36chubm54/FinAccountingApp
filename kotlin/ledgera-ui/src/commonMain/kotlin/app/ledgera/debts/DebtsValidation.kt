package app.ledgera.debts

import app.ledgera.model.DebtDraft
import app.ledgera.validation.CurrencyValidation
import app.ledgera.validation.DateValidation
import app.ledgera.validation.MoneyValidation

object DebtsValidation {
    fun validateCreateDraft(draft: DebtDraft, baseCurrency: String): String? {
        val kind = draft.kind.trim().lowercase()
        if (kind != "debt" && kind != "loan") {
            return "Debt kind must be debt or loan"
        }
        if (draft.contactName.trim().isEmpty()) {
            return "Contact name is required"
        }
        if (draft.walletId <= 0) {
            return "Wallet is required"
        }
        DateValidation.validateYmdNotFuture(draft.createdAt.trim())?.let { return it }
        MoneyValidation.validatePositiveAmount(draft.amount.trim())?.let { return it }
        CurrencyValidation.validateSupportedCurrency(draft.currency.trim())?.let { return it }
        if (!draft.currency.trim().equals(baseCurrency.trim(), ignoreCase = true)) {
            return "Kotlin Debts currently supports base-currency obligations only (${baseCurrency.trim().uppercase()})"
        }
        return null
    }
}
