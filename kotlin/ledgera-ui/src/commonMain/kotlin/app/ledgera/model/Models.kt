package app.ledgera.model

data class OperationRecord(
    val id: Long,
    val type: String,
    val date: String,
    val walletId: Long,
    val amountOriginal: String,
    val currency: String,
    val rateAtOperation: String,
    val amountBase: String,
    val category: String,
    val description: String,
    val tags: List<String>,
)

data class OperationDraft(
    val id: Long? = null,
    val type: String = "expense",
    val date: String = "",
    val walletId: Long = 0,
    val amountOriginal: String = "",
    val currency: String = "KZT",
    val rateAtOperation: String = "1",
    val amountBase: String = "",
    val category: String = "",
    val description: String = "",
    val tagsText: String = "",
)

data class OperationFilter(
    val startDate: String? = null,
    val endDate: String? = null,
    val walletId: Long? = null,
    val recordType: String? = null,
)

data class CreateOperationRequest(
    val type: String,
    val date: String,
    val walletId: Long,
    val amountOriginal: String,
    val currency: String,
    val rateAtOperation: String,
    val amountBase: String,
    val category: String,
    val description: String,
    val tags: List<String> = emptyList(),
)

data class UpdateOperationRequest(
    val type: String,
    val date: String,
    val walletId: Long,
    val amountOriginal: String,
    val currency: String,
    val rateAtOperation: String,
    val amountBase: String,
    val category: String,
    val description: String,
    val tags: List<String> = emptyList(),
)

data class WalletOption(
    val id: Long,
    val name: String,
    val currency: String,
    val balance: String = "0.00",
)

data class EngineStatus(
    val ok: Boolean,
    val dbPath: String,
    val message: String,
)
