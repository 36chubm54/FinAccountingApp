package app.ledgera.model

data class OperationRecord(
    val id: Long,
    val type: String,
    val date: String,
    val walletId: Long,
    val transferId: Long? = null,
    val relatedDebtId: Long? = null,
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
    val transferId: Long? = null,
    val relatedDebtId: Long? = null,
    val amountOriginal: String,
    val currency: String,
    val rateAtOperation: String,
    val amountBase: String,
    val category: String,
    val description: String,
    val tags: List<String> = emptyList(),
)

data class CreateTransferRequest(
    val fromWalletId: Long,
    val toWalletId: Long,
    val date: String,
    val amount: String,
    val currency: String,
    val description: String,
    val commissionAmount: String = "0",
    val commissionCurrency: String = "",
)

data class CreateTransferResult(
    val transferId: Long,
)

data class TransferDetails(
    val id: Long,
    val fromWalletId: Long,
    val toWalletId: Long,
    val date: String,
    val amountOriginal: String,
    val currency: String,
    val rateAtOperation: String,
    val amountBase: String,
    val description: String,
)

data class TransferDraft(
    val id: Long,
    val fromWalletId: Long = 0,
    val toWalletId: Long = 0,
    val date: String = "",
    val amount: String = "",
    val currency: String = "KZT",
    val description: String = "",
)

data class UpdateTransferRequest(
    val fromWalletId: Long,
    val toWalletId: Long,
    val date: String,
    val amount: String,
    val currency: String,
    val description: String,
)

data class UpdateTransferResult(
    val transferId: Long,
)

data class WalletOption(
    val id: Long,
    val name: String,
    val currency: String,
    val balance: String = "0.00",
)

data class WalletSettingsItem(
    val id: Long,
    val name: String,
    val currency: String,
    val initialBalance: String,
    val balance: String,
    val system: Boolean,
    val allowNegative: Boolean,
    val active: Boolean,
)

data class CreateWalletRequest(
    val name: String,
    val currency: String,
    val initialBalance: String,
    val allowNegative: Boolean,
)

data class WalletDeleteResult(
    val walletId: Long,
    val action: String,
)

data class EngineStatus(
    val ok: Boolean,
    val dbPath: String,
    val message: String,
)
