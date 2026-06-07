package app.ledgera.operations

import app.ledgera.bridge.OperationsEngine
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.CreateTransferRequest
import app.ledgera.model.OperationDraft
import app.ledgera.model.OperationDeleteResult
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.TransferDraft
import app.ledgera.model.UpdateOperationRequest
import app.ledgera.model.UpdateTransferRequest
import app.ledgera.model.WalletOption
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class OperationsUiState(
    val loading: Boolean = false,
    val records: List<OperationRecord> = emptyList(),
    val wallets: List<WalletOption> = emptyList(),
    val baseCurrency: String = "KZT",
    val tags: List<String> = emptyList(),
    val categories: List<String> = emptyList(),
    val filter: OperationFilter = OperationFilter(),
    val selectedRecordId: Long? = null,
    val selectiveDeleteMode: Boolean = false,
    val selectedBulkRecordIds: Set<Long> = emptySet(),
    val selectedBulkTransferIds: Set<Long> = emptySet(),
    val editDraft: OperationDraft? = null,
    val transferDraft: TransferDraft? = null,
    val error: String? = null,
    val notice: String? = null,
) {
    val hasBulkDeleteCandidates: Boolean
        get() = records.any { record ->
            if (record.transferId != null) {
                true
            } else {
                record.relatedDebtId == null &&
                    (record.type == "income" || record.type == "expense") &&
                    !isTransferCommissionMarker(record.description)
            }
        }
}

class OperationsViewModel(
    private val engine: OperationsEngine,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main),
) {
    private val mutableState = MutableStateFlow(OperationsUiState(loading = true))
    val state: StateFlow<OperationsUiState> = mutableState.asStateFlow()

    fun refresh(filter: OperationFilter = mutableState.value.filter) {
        refresh(filter = filter, notice = null)
    }

    private fun refresh(filter: OperationFilter = mutableState.value.filter, notice: String?) {
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = notice, filter = filter)
        launchSafely {
            runCatching {
                val wallets = engine.walletBalances().ifEmpty { engine.listWallets() }
                val baseCurrency = engine.baseCurrency()
                val records = engine.listRecords(filter)
                val tags = engine.listTags()
                val categories = engine.listCategories(filter.recordType ?: "expense")
                mutableState.value = OperationsUiState(
                    loading = false,
                    records = records,
                    wallets = wallets,
                    baseCurrency = baseCurrency,
                    tags = tags,
                    categories = categories,
                    filter = filter,
                    selectedRecordId = mutableState.value.selectedRecordId?.takeIf { selectedId ->
                        records.any { it.id == selectedId }
                    },
                    selectiveDeleteMode = mutableState.value.selectiveDeleteMode,
                    selectedBulkRecordIds = mutableState.value.selectedBulkRecordIds
                        .filterTo(mutableSetOf()) { selectedId ->
                            records.any { it.id == selectedId }
                        },
                    selectedBulkTransferIds = mutableState.value.selectedBulkTransferIds
                        .filterTo(mutableSetOf()) { selectedId ->
                            records.any { it.transferId == selectedId }
                        },
                    editDraft = mutableState.value.editDraft?.takeIf { draft ->
                        draft.id != null && records.any { it.id == draft.id }
                    },
                    transferDraft = mutableState.value.transferDraft,
                    notice = notice,
                )
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun select(recordId: Long) {
        val record = mutableState.value.records.firstOrNull { it.id == recordId }
        if (record?.transferId != null) {
            mutableState.value = mutableState.value.copy(
                selectedRecordId = null,
                editDraft = null,
                transferDraft = null,
                error = null,
                notice = "Transfer-linked rows are read-only in this beta.1 slice",
            )
            return
        }
        if (record?.relatedDebtId != null) {
            mutableState.value = mutableState.value.copy(
                selectedRecordId = null,
                editDraft = null,
                transferDraft = null,
                error = null,
                notice = "Debt-linked rows are read-only in this beta.1 slice",
            )
            return
        }
        mutableState.value = mutableState.value.copy(
            selectedRecordId = recordId,
            editDraft = record?.toDraft(),
            transferDraft = null,
            error = if (record == null) "Record not found" else null,
            notice = null,
        )
    }

    fun clearSelection() {
        mutableState.value = mutableState.value.copy(
            selectedRecordId = null,
            selectiveDeleteMode = false,
            selectedBulkRecordIds = emptySet(),
            selectedBulkTransferIds = emptySet(),
            editDraft = null,
            transferDraft = null,
            error = null,
            notice = null,
        )
    }

    fun clearFeedback() {
        mutableState.value = mutableState.value.copy(error = null, notice = null)
    }

    fun clearNotice() {
        mutableState.value = mutableState.value.copy(notice = null)
    }

    fun showImportPlaceholder() {
        showPlaceholderNotice("Import")
    }

    fun showExportPlaceholder() {
        showPlaceholderNotice("Export")
    }

    fun startSelectiveDelete() {
        mutableState.value = mutableState.value.copy(
            selectiveDeleteMode = true,
            selectedBulkRecordIds = emptySet(),
            selectedBulkTransferIds = emptySet(),
            selectedRecordId = null,
            editDraft = null,
            transferDraft = null,
            error = null,
            notice = null,
        )
    }

    fun cancelSelectiveDelete() {
        mutableState.value = mutableState.value.copy(
            selectiveDeleteMode = false,
            selectedBulkRecordIds = emptySet(),
            selectedBulkTransferIds = emptySet(),
            error = null,
            notice = null,
        )
    }

    fun toggleBulkRecord(recordId: Long) {
        if (recordId <= 0) {
            mutableState.value = mutableState.value.copy(error = "Record is required", notice = null)
            return
        }
        val record = mutableState.value.records.firstOrNull { it.id == recordId }
        if (record == null) {
            mutableState.value = mutableState.value.copy(error = "Record not found", notice = null)
            return
        }
        if (
            record.transferId != null ||
            record.relatedDebtId != null ||
            (record.type != "income" && record.type != "expense") ||
            isTransferCommissionMarker(record.description)
        ) {
            mutableState.value = mutableState.value.copy(
                error = "This linked record cannot be selected for bulk delete",
                notice = null,
            )
            return
        }
        mutableState.value = mutableState.value.copy(
            selectiveDeleteMode = true,
            selectedBulkRecordIds = toggleId(mutableState.value.selectedBulkRecordIds, recordId),
            error = null,
            notice = null,
        )
    }

    fun toggleBulkTransfer(transferId: Long) {
        if (transferId <= 0) {
            mutableState.value = mutableState.value.copy(error = "Transfer is required", notice = null)
            return
        }
        if (mutableState.value.records.none { it.transferId == transferId }) {
            mutableState.value = mutableState.value.copy(error = "Transfer not found", notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(
            selectiveDeleteMode = true,
            selectedBulkTransferIds = toggleId(mutableState.value.selectedBulkTransferIds, transferId),
            error = null,
            notice = null,
        )
    }

    fun updateDraft(draft: OperationDraft) {
        mutableState.value = mutableState.value.copy(editDraft = draft, error = null, notice = null)
    }

    fun selectTransfer(transferId: Long) {
        mutableState.value = mutableState.value.copy(
            loading = true,
            selectedRecordId = null,
            editDraft = null,
            transferDraft = null,
            error = null,
            notice = null,
        )
        launchSafely {
            runCatching {
                val transfer = engine.getTransfer(transferId)
                    ?: error("Transfer not found: $transferId")
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    transferDraft = transfer.toDraft(),
                    error = null,
                    notice = null,
                )
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun updateTransferDraft(draft: TransferDraft) {
        mutableState.value = mutableState.value.copy(transferDraft = draft, error = null, notice = null)
    }

    fun create(request: CreateOperationRequest) {
        val validationError = validate(request)
        if (validationError != null) {
            mutableState.value = mutableState.value.copy(error = validationError, notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                engine.createRecord(request)
                refresh(notice = "Operation added")
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun createTransfer(request: CreateTransferRequest) {
        val validationError = validate(request)
        if (validationError != null) {
            mutableState.value = mutableState.value.copy(error = validationError, notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val result = engine.createTransfer(request)
                refresh(notice = transferNotice(result.transferId, request, mutableState.value.wallets))
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun updateSelected() {
        val draft = mutableState.value.editDraft
        if (draft?.id == null) {
            mutableState.value = mutableState.value.copy(error = "Select a record first", notice = null)
            return
        }
        val validationError = validate(draft)
        if (validationError != null) {
            mutableState.value = mutableState.value.copy(error = validationError, notice = null)
            return
        }
        val request = draft.toUpdateRequest()
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                engine.updateRecord(draft.id, request)
                mutableState.value = mutableState.value.copy(selectedRecordId = null, editDraft = null)
                refresh(notice = "Operation updated")
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun updateSelectedTransfer() {
        val draft = mutableState.value.transferDraft
        if (draft == null) {
            mutableState.value = mutableState.value.copy(error = "Select a transfer first", notice = null)
            return
        }
        val validationError = validate(draft)
        if (validationError != null) {
            mutableState.value = mutableState.value.copy(error = validationError, notice = null)
            return
        }
        val request = draft.toUpdateRequest()
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val result = engine.updateTransfer(draft.id, request)
                mutableState.value = mutableState.value.copy(transferDraft = null)
                refresh(notice = "Transfer updated (id=${result.transferId})")
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun deleteSelected() {
        val recordId = mutableState.value.selectedRecordId
        if (recordId == null) {
            mutableState.value = mutableState.value.copy(error = "Select a record first", notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                engine.deleteRecord(recordId)
                mutableState.value = mutableState.value.copy(selectedRecordId = null, editDraft = null)
                refresh(notice = "Operation deleted")
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun deleteSelectedTransfer() {
        val draft = mutableState.value.transferDraft
        if (draft == null) {
            mutableState.value = mutableState.value.copy(error = "Select a transfer first", notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                engine.deleteTransfer(draft.id)
                mutableState.value = mutableState.value.copy(transferDraft = null)
                refresh(notice = "Transfer deleted (id=${draft.id})")
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun deleteAllOperations() {
        if (!mutableState.value.hasBulkDeleteCandidates) {
            mutableState.value = mutableState.value.copy(
                error = null,
                notice = "No standalone operations or transfers to delete",
            )
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val result = engine.deleteAllOperations()
                mutableState.value = mutableState.value.copy(
                    selectedRecordId = null,
                    editDraft = null,
                    transferDraft = null,
                    selectiveDeleteMode = false,
                    selectedBulkRecordIds = emptySet(),
                    selectedBulkTransferIds = emptySet(),
                )
                refresh(notice = deleteNotice(result))
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    fun deleteSelectedOperations() {
        val recordIds = mutableState.value.selectedBulkRecordIds.toList().sorted()
        val transferIds = mutableState.value.selectedBulkTransferIds.toList().sorted()
        if (recordIds.isEmpty() && transferIds.isEmpty()) {
            mutableState.value = mutableState.value.copy(error = "Select at least one operation or transfer", notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val result = engine.deleteOperationsSelection(recordIds, transferIds)
                mutableState.value = mutableState.value.copy(
                    selectedRecordId = null,
                    editDraft = null,
                    transferDraft = null,
                    selectiveDeleteMode = false,
                    selectedBulkRecordIds = emptySet(),
                    selectedBulkTransferIds = emptySet(),
                )
                refresh(notice = deleteNotice(result))
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                    notice = null,
                )
            }
        }
    }

    private fun validate(request: CreateOperationRequest): String? =
        OperationValidation.validateFields(
            type = request.type,
            date = request.date,
            walletId = request.walletId,
            amountOriginal = request.amountOriginal,
            currency = request.currency,
            category = request.category,
            tagsText = request.tags.joinToString(", "),
            baseCurrency = mutableState.value.baseCurrency,
        )

    private fun validate(request: UpdateOperationRequest): String? =
        OperationValidation.validateFields(
            type = request.type,
            date = request.date,
            walletId = request.walletId,
            amountOriginal = request.amountOriginal,
            currency = request.currency,
            category = request.category,
            tagsText = request.tags.joinToString(", "),
            baseCurrency = mutableState.value.baseCurrency,
        )

    private fun validate(request: CreateTransferRequest): String? =
        OperationValidation.validateTransferFields(
            fromWalletId = request.fromWalletId,
            toWalletId = request.toWalletId,
            date = request.date,
            amount = request.amount,
            currency = request.currency,
            commissionAmount = request.commissionAmount,
            commissionCurrency = request.commissionCurrency,
            baseCurrency = mutableState.value.baseCurrency,
        )

    private fun validate(draft: TransferDraft): String? =
        OperationValidation.validateTransferFields(
            fromWalletId = draft.fromWalletId,
            toWalletId = draft.toWalletId,
            date = draft.date,
            amount = draft.amount,
            currency = draft.currency,
            commissionAmount = "0",
            commissionCurrency = mutableState.value.baseCurrency,
            baseCurrency = mutableState.value.baseCurrency,
        )

    private fun validate(draft: OperationDraft): String? =
        OperationValidation.validateFields(
            type = draft.type,
            date = draft.date,
            walletId = draft.walletId,
            amountOriginal = draft.amountOriginal,
            currency = draft.currency,
            category = draft.category,
            tagsText = draft.tagsText,
            baseCurrency = mutableState.value.baseCurrency,
        )

    private fun transferNotice(
        transferId: Long,
        request: CreateTransferRequest,
        wallets: List<WalletOption>,
    ): String {
        val fromWallet = wallets.firstOrNull { it.id == request.fromWalletId }?.name ?: "wallet #${request.fromWalletId}"
        val toWallet = wallets.firstOrNull { it.id == request.toWalletId }?.name ?: "wallet #${request.toWalletId}"
        return "Transfer created (id=$transferId): $fromWallet -> $toWallet, ${request.amount} ${request.currency}"
    }

    private fun showPlaceholderNotice(action: String) {
        mutableState.value = mutableState.value.copy(
            error = null,
            notice = "$action is not available in beta.1 yet",
        )
    }

    private fun deleteNotice(result: OperationDeleteResult): String {
        val base = "Deleted ${result.deletedRecords} records and ${result.deletedTransfers} transfers"
        return if (result.skippedRecords > 0) {
            "$base. Skipped ${result.skippedRecords} unsupported linked records"
        } else {
            base
        }
    }

    private fun toggleId(ids: Set<Long>, id: Long): Set<Long> =
        if (ids.contains(id)) ids - id else ids + id

    private fun OperationRecord.toDraft(): OperationDraft =
        OperationDraft(
            id = id,
            type = type,
            date = date,
            walletId = walletId,
            amountOriginal = amountOriginal,
            currency = currency,
            rateAtOperation = "1",
            amountBase = amountOriginal,
            category = category,
            description = description,
            tagsText = tags.joinToString(", "),
        )

    private fun app.ledgera.model.TransferDetails.toDraft(): TransferDraft =
        TransferDraft(
            id = id,
            fromWalletId = fromWalletId,
            toWalletId = toWalletId,
            date = date,
            amount = amountOriginal,
            currency = currency,
            description = description,
        )

    private fun OperationDraft.toUpdateRequest(): UpdateOperationRequest =
        UpdateOperationRequest(
            type = type,
            date = date,
            walletId = walletId,
            amountOriginal = amountOriginal,
            currency = currency,
            rateAtOperation = "1",
            amountBase = amountOriginal,
            category = category,
            description = description,
            tags = OperationValidation.parseTags(tagsText),
        )

    private fun TransferDraft.toUpdateRequest(): UpdateTransferRequest =
        UpdateTransferRequest(
            fromWalletId = fromWalletId,
            toWalletId = toWalletId,
            date = date,
            amount = amount,
            currency = currency,
            description = description,
        )

    private fun launchSafely(block: suspend () -> Unit) {
        try {
            scope.launch { block() }
        } catch (error: Throwable) {
            mutableState.value = mutableState.value.copy(
                loading = false,
                error = error.message ?: error::class.simpleName ?: "Unknown error",
                notice = null,
            )
        }
    }
}

private fun isTransferCommissionMarker(description: String): Boolean =
    Regex("""^\[transfer:\d+]$""").matches(description.trim())
