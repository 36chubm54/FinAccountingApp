package app.ledgera.operations

import app.ledgera.bridge.OperationsEngine
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.OperationDraft
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.UpdateOperationRequest
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
    val editDraft: OperationDraft? = null,
    val error: String? = null,
    val notice: String? = null,
)

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
                    editDraft = mutableState.value.editDraft?.takeIf { draft ->
                        draft.id != null && records.any { it.id == draft.id }
                    },
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
        mutableState.value = mutableState.value.copy(
            selectedRecordId = recordId,
            editDraft = record?.toDraft(),
            error = if (record == null) "Record not found" else null,
            notice = null,
        )
    }

    fun clearSelection() {
        mutableState.value = mutableState.value.copy(selectedRecordId = null, editDraft = null, error = null, notice = null)
    }

    fun clearFeedback() {
        mutableState.value = mutableState.value.copy(error = null, notice = null)
    }

    fun updateDraft(draft: OperationDraft) {
        mutableState.value = mutableState.value.copy(editDraft = draft, error = null, notice = null)
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
