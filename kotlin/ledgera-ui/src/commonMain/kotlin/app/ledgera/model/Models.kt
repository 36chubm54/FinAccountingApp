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

data class OperationDeleteResult(
    val deletedRecords: Long,
    val deletedTransfers: Long,
    val deletedDebtLinkedRecords: Long,
    val skippedRecords: Long,
)

data class OperationImportResult(
    val imported: Long,
    val skipped: Long,
    val errors: List<String>,
    val dryRun: Boolean,
)

data class OperationExportResult(
    val exportedRows: Long,
    val path: String,
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

data class DebtItem(
    val id: Long,
    val contactName: String,
    val kind: String,
    val totalAmount: String,
    val remainingAmount: String,
    val currency: String,
    val interestRate: String,
    val status: String,
    val createdAt: String,
    val closedAt: String? = null,
)

data class DebtPaymentItem(
    val id: Long,
    val debtId: Long,
    val recordId: Long? = null,
    val operationType: String,
    val principalPaid: String,
    val isWriteOff: Boolean,
    val paymentDate: String,
)

data class DebtDraft(
    val kind: String = "debt",
    val contactName: String = "",
    val walletId: Long = 0,
    val amount: String = "",
    val currency: String = "KZT",
    val createdAt: String = "",
    val description: String = "",
)

data class DebtActionDraft(
    val action: String = "payment",
    val debtId: Long = 0,
    val walletId: Long = 0,
    val amount: String = "",
    val paymentDate: String = "",
    val description: String = "",
)

data class CreateDebtRequest(
    val kind: String,
    val contactName: String,
    val walletId: Long,
    val amount: String,
    val currency: String,
    val createdAt: String,
    val description: String,
)

data class RegisterDebtPaymentRequest(
    val debtId: Long,
    val walletId: Long?,
    val amount: String,
    val paymentDate: String,
    val description: String,
)

data class AuditFinding(
    val check: String,
    val severity: String,
    val message: String,
    val entity: String,
)

data class AuditSummary(
    val errors: Int,
    val warnings: Int,
    val ok: Int,
    val total: Int,
)

data class EngineStatus(
    val ok: Boolean,
    val dbPath: String,
    val message: String,
)
