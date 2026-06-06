package app.ledgera.settings

import app.ledgera.bridge.SettingsEngine
import app.ledgera.model.CreateWalletRequest
import app.ledgera.model.WalletSettingsItem
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class SettingsViewModelTest {
    @Test
    fun refreshLoadsWallets() {
        val engine = FakeSettingsEngine()
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()

        assertEquals(1, viewModel.state.value.wallets.size)
        assertEquals("Cash", viewModel.state.value.wallets.single().name)
        assertEquals("KZT", viewModel.state.value.baseCurrency)
    }

    @Test
    fun createWalletRejectsBlankNameBeforeEngineCall() {
        val engine = FakeSettingsEngine()
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createWallet(validWalletRequest(name = " "))

        assertEquals("Wallet name is required", viewModel.state.value.error)
        assertEquals(0, engine.createCalls)
    }

    @Test
    fun createWalletRejectsNegativeInitialBalanceBeforeEngineCall() {
        val engine = FakeSettingsEngine()
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createWallet(validWalletRequest(initialBalance = "-1"))

        assertEquals("Initial balance must be zero or a positive number", viewModel.state.value.error)
        assertEquals(0, engine.createCalls)
    }

    @Test
    fun createWalletRejectsNonBaseCurrencyBeforeEngineCall() {
        val engine = FakeSettingsEngine()
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createWallet(validWalletRequest(currency = "USD"))

        assertEquals(
            "Kotlin Settings currently supports base-currency wallets only (KZT)",
            viewModel.state.value.error,
        )
        assertEquals(0, engine.createCalls)
    }

    @Test
    fun createWalletSuccessRefreshesWalletsAndShowsNotice() {
        val engine = FakeSettingsEngine(wallets = mutableListOf())
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createWallet(validWalletRequest())

        assertEquals(1, engine.createCalls)
        assertEquals("Wallet created (id=1)", viewModel.state.value.notice)
        assertEquals(listOf("Savings"), viewModel.state.value.wallets.map { it.name })
    }

    @Test
    fun createWalletEngineErrorSurfacesInState() {
        val engine = FakeSettingsEngine(createError = IllegalStateException("storage failed"))
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createWallet(validWalletRequest())

        assertEquals("storage failed", viewModel.state.value.error)
        assertEquals(null, viewModel.state.value.notice)
    }
}

private class FakeSettingsEngine(
    private val wallets: MutableList<WalletSettingsItem> = mutableListOf(walletSettingsItem()),
    private val createError: Throwable? = null,
) : SettingsEngine {
    var createCalls = 0

    override suspend fun baseCurrency(): String = "KZT"

    override suspend fun listWalletsForSettings(): List<WalletSettingsItem> = wallets.toList()

    override suspend fun createWallet(request: CreateWalletRequest): WalletSettingsItem {
        createError?.let { throw it }
        createCalls += 1
        val wallet = walletSettingsItem(
            id = (wallets.maxOfOrNull { it.id } ?: 0) + 1,
            name = request.name,
            initialBalance = request.initialBalance,
            balance = request.initialBalance,
            allowNegative = request.allowNegative,
        )
        wallets += wallet
        return wallet
    }
}

private fun validWalletRequest(
    name: String = "Savings",
    currency: String = "KZT",
    initialBalance: String = "0",
    allowNegative: Boolean = false,
) = CreateWalletRequest(
    name = name,
    currency = currency,
    initialBalance = initialBalance,
    allowNegative = allowNegative,
)

private fun walletSettingsItem(
    id: Long = 1,
    name: String = "Cash",
    currency: String = "KZT",
    initialBalance: String = "100.00",
    balance: String = "100.00",
    system: Boolean = true,
    allowNegative: Boolean = false,
    active: Boolean = true,
) = WalletSettingsItem(
    id = id,
    name = name,
    currency = currency,
    initialBalance = initialBalance,
    balance = balance,
    system = system,
    allowNegative = allowNegative,
    active = active,
)
