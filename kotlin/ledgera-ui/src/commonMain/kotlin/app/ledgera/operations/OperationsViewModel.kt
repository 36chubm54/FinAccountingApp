package app.ledgera.operations

import app.ledgera.bridge.EngineAdapter
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
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
    val filter: OperationFilter = OperationFilter(),
    val error: String? = null,
)

class OperationsViewModel(
    private val engine: EngineAdapter,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main),
) {
    private val mutableState = MutableStateFlow(OperationsUiState(loading = true))
    val state: StateFlow<OperationsUiState> = mutableState.asStateFlow()

    fun refresh(filter: OperationFilter = mutableState.value.filter) {
        mutableState.value = mutableState.value.copy(loading = true, error = null, filter = filter)
        scope.launch {
            runCatching {
                val wallets = engine.walletBalances().ifEmpty { engine.listWallets() }
                val records = engine.listRecords(filter)
                mutableState.value = OperationsUiState(
                    loading = false,
                    records = records,
                    wallets = wallets,
                    filter = filter,
                )
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                )
            }
        }
    }

    fun create(request: CreateOperationRequest) {
        val validationError = validate(request)
        if (validationError != null) {
            mutableState.value = mutableState.value.copy(error = validationError)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null)
        scope.launch {
            runCatching {
                engine.createRecord(request)
                refresh()
            }.onFailure { error ->
                mutableState.value = mutableState.value.copy(
                    loading = false,
                    error = error.message ?: error::class.simpleName ?: "Unknown error",
                )
            }
        }
    }

    private fun validate(request: CreateOperationRequest): String? {
        val type = request.type.trim().lowercase()
        return when {
            type != "income" && type != "expense" -> "Only income and expense are supported"
            request.date.isBlank() -> "Date is required"
            request.walletId <= 0 -> "Wallet is required"
            request.amountBase.isBlank() || request.amountOriginal.isBlank() -> "Amount is required"
            request.category.isBlank() -> "Category is required"
            else -> null
        }
    }
}
