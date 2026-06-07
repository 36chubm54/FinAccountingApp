package app.ledgera.settings

import app.ledgera.bridge.SettingsEngine
import app.ledgera.model.AuditFinding
import app.ledgera.model.CreateWalletRequest
import app.ledgera.model.WalletDeleteResult
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
        assertEquals(0, engine.auditCalls)
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

    @Test
    fun deleteWalletRejectsInvalidIdBeforeEngineCall() {
        val engine = FakeSettingsEngine()
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.deleteWallet(0)

        assertEquals("Wallet is required", viewModel.state.value.error)
        assertEquals(0, engine.deleteCalls)
    }

    @Test
    fun deleteWalletHardSuccessRefreshesWalletsAndShowsNotice() {
        val engine = FakeSettingsEngine(
            wallets = mutableListOf(walletSettingsItem(system = false, balance = "0.00")),
            deleteAction = "hard_deleted",
        )
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.deleteWallet(1)

        assertEquals(1, engine.deleteCalls)
        assertEquals("Wallet deleted (id=1)", viewModel.state.value.notice)
        assertEquals(emptyList(), viewModel.state.value.wallets)
    }

    @Test
    fun deleteWalletSoftSuccessRefreshesWalletsAndShowsNotice() {
        val engine = FakeSettingsEngine(
            wallets = mutableListOf(walletSettingsItem(system = false, balance = "0.00")),
            deleteAction = "soft_deleted",
        )
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.deleteWallet(1)

        assertEquals("Wallet deactivated (id=1)", viewModel.state.value.notice)
        assertEquals(false, viewModel.state.value.wallets.single().active)
    }

    @Test
    fun deleteWalletEngineErrorSurfacesAndKeepsWalletList() {
        val engine = FakeSettingsEngine(deleteError = IllegalStateException("non-zero balance"))
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.deleteWallet(1)

        assertEquals("non-zero balance", viewModel.state.value.error)
        assertEquals(listOf("Cash"), viewModel.state.value.wallets.map { it.name })
        assertEquals(null, viewModel.state.value.notice)
    }

    @Test
    fun runAuditSuccessStoresFindingsSummaryAndShowsNotice() {
        val engine = FakeSettingsEngine(
            auditFindings = listOf(
                auditFinding("amount_consistency", "error"),
                auditFinding("date_validity", "warning"),
                auditFinding("tag_integrity", "ok"),
            )
        )
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.runAudit()

        assertEquals(1, engine.auditCalls)
        assertEquals(3, viewModel.state.value.auditFindings.size)
        assertEquals(1, viewModel.state.value.auditSummary?.errors)
        assertEquals(1, viewModel.state.value.auditSummary?.warnings)
        assertEquals(1, viewModel.state.value.auditSummary?.ok)
        assertEquals(3, viewModel.state.value.auditSummary?.total)
        assertEquals("Audit completed: 1 errors, 1 warnings", viewModel.state.value.notice)
    }

    @Test
    fun runAuditEngineErrorSurfacesAndKeepsWalletList() {
        val engine = FakeSettingsEngine(auditError = IllegalStateException("audit failed"))
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.runAudit()

        assertEquals("audit failed", viewModel.state.value.error)
        assertEquals(false, viewModel.state.value.auditRunning)
        assertEquals(listOf("Cash"), viewModel.state.value.wallets.map { it.name })
        assertEquals(null, viewModel.state.value.notice)
    }

    @Test
    fun refreshDoesNotAutoRunAudit() {
        val engine = FakeSettingsEngine(auditFindings = listOf(auditFinding("tag_integrity", "ok")))
        val viewModel = SettingsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.refresh()

        assertEquals(0, engine.auditCalls)
        assertEquals(emptyList(), viewModel.state.value.auditFindings)
        assertEquals(null, viewModel.state.value.auditSummary)
    }
}

private class FakeSettingsEngine(
    private val wallets: MutableList<WalletSettingsItem> = mutableListOf(walletSettingsItem()),
    private val createError: Throwable? = null,
    private val deleteError: Throwable? = null,
    private val deleteAction: String = "hard_deleted",
    private val auditFindings: List<AuditFinding> = emptyList(),
    private val auditError: Throwable? = null,
) : SettingsEngine {
    var createCalls = 0
    var deleteCalls = 0
    var auditCalls = 0

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

    override suspend fun deleteWallet(walletId: Long): WalletDeleteResult {
        deleteError?.let { throw it }
        deleteCalls += 1
        val existing = wallets.first { it.id == walletId }
        if (deleteAction == "hard_deleted") {
            wallets.removeIf { it.id == walletId }
        } else {
            val index = wallets.indexOfFirst { it.id == walletId }
            wallets[index] = existing.copy(active = false)
        }
        return WalletDeleteResult(walletId, deleteAction)
    }

    override suspend fun runAudit(): List<AuditFinding> {
        auditError?.let { throw it }
        auditCalls += 1
        return auditFindings
    }
}

private fun auditFinding(check: String, severity: String) = AuditFinding(
    check = check,
    severity = severity,
    message = "$check message",
    entity = "id=1",
)

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
