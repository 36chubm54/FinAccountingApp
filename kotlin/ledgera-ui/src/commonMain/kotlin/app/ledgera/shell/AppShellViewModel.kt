package app.ledgera.shell

import app.ledgera.bridge.RuntimeEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AppShellUiState(
    val selectedSection: DesktopSection = DesktopSection.Operations,
    val sections: List<DesktopSection> = DesktopSection.entries,
    val engineMessage: String = "Checking engine",
    val error: String? = null,
)

class AppShellViewModel(
    private val engine: RuntimeEngine,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main),
) {
    private val mutableState = MutableStateFlow(AppShellUiState())
    val state: StateFlow<AppShellUiState> = mutableState.asStateFlow()

    fun select(section: DesktopSection) {
        mutableState.value = mutableState.value.copy(selectedSection = section)
    }

    fun refreshStatus() {
        scope.launch {
            runCatching { engine.status() }
                .onSuccess { status ->
                    mutableState.value = mutableState.value.copy(
                        engineMessage = status.message.ifBlank { status.dbPath },
                        error = if (status.ok) null else status.message,
                    )
                }
                .onFailure { error ->
                    mutableState.value = mutableState.value.copy(
                        engineMessage = "Engine unavailable",
                        error = error.message ?: error::class.simpleName ?: "Unknown error",
                    )
                }
        }
    }
}
