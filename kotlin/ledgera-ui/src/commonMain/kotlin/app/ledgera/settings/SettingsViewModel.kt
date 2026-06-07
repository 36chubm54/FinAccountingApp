package app.ledgera.settings

import app.ledgera.bridge.SettingsEngine
import app.ledgera.model.CreateWalletRequest
import app.ledgera.model.WalletSettingsItem
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SettingsUiState(
    val loading: Boolean = false,
    val wallets: List<WalletSettingsItem> = emptyList(),
    val baseCurrency: String = "KZT",
    val error: String? = null,
    val notice: String? = null,
)

class SettingsViewModel(
    private val engine: SettingsEngine,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main),
) {
    private val mutableState = MutableStateFlow(SettingsUiState(loading = true))
    val state: StateFlow<SettingsUiState> = mutableState.asStateFlow()

    fun refresh() {
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val baseCurrency = engine.baseCurrency()
                val wallets = engine.listWalletsForSettings()
                mutableState.value = SettingsUiState(
                    loading = false,
                    wallets = wallets,
                    baseCurrency = baseCurrency,
                )
            }.onFailure(::showError)
        }
    }

    fun clearFeedback() {
        mutableState.value = mutableState.value.copy(error = null, notice = null)
    }

    fun clearNotice() {
        mutableState.value = mutableState.value.copy(notice = null)
    }

    fun createWallet(request: CreateWalletRequest) {
        val validationError = SettingsValidation.validateWalletFields(
            name = request.name,
            currency = request.currency,
            initialBalance = request.initialBalance,
            baseCurrency = mutableState.value.baseCurrency,
        )
        if (validationError != null) {
            mutableState.value = mutableState.value.copy(error = validationError, notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val created = engine.createWallet(request.copy(initialBalance = request.initialBalance.ifBlank { "0" }))
                val baseCurrency = engine.baseCurrency()
                val wallets = engine.listWalletsForSettings()
                mutableState.value = SettingsUiState(
                    loading = false,
                    wallets = wallets,
                    baseCurrency = baseCurrency,
                    notice = "Wallet created (id=${created.id})",
                )
            }.onFailure(::showError)
        }
    }

    fun deleteWallet(walletId: Long) {
        if (walletId <= 0) {
            mutableState.value = mutableState.value.copy(error = "Wallet is required", notice = null)
            return
        }
        mutableState.value = mutableState.value.copy(loading = true, error = null, notice = null)
        launchSafely {
            runCatching {
                val result = engine.deleteWallet(walletId)
                val baseCurrency = engine.baseCurrency()
                val wallets = engine.listWalletsForSettings()
                mutableState.value = SettingsUiState(
                    loading = false,
                    wallets = wallets,
                    baseCurrency = baseCurrency,
                    notice = walletDeleteNotice(result.walletId, result.action),
                )
            }.onFailure(::showError)
        }
    }

    private fun showError(error: Throwable) {
        mutableState.value = mutableState.value.copy(
            loading = false,
            error = error.message ?: error::class.simpleName ?: "Unknown error",
            notice = null,
        )
    }

    private fun launchSafely(block: suspend () -> Unit) {
        try {
            scope.launch { block() }
        } catch (error: Throwable) {
            showError(error)
        }
    }

    private fun walletDeleteNotice(walletId: Long, action: String): String =
        when (action) {
            "hard_deleted" -> "Wallet deleted (id=$walletId)"
            "soft_deleted" -> "Wallet deactivated (id=$walletId)"
            else -> "Wallet updated (id=$walletId)"
        }
}
