package app.ledgera.operations

import app.ledgera.bridge.EngineAdapter
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.CreateTransferRequest
import app.ledgera.model.CreateTransferResult
import app.ledgera.model.CreateWalletRequest
import app.ledgera.model.EngineStatus
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.UpdateOperationRequest
import app.ledgera.model.WalletOption
import app.ledgera.model.WalletSettingsItem
import java.util.Locale
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class OperationsViewModelTest {
    @Test
    fun createRejectsEmptyCategoryBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "10",
                category = "",
                description = "",
            )
        )

        assertEquals("Category is required", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsInvalidDateBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-13-32",
                walletId = 1,
                amountOriginal = "10",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("Date must use a valid YYYY-MM-DD value", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsFutureDateBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2999-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("Date cannot be in the future", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsInvalidCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "K1T",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("Currency code must contain 3 letters", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsInvalidAmountBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "ten",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "ten",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("Amount must be a positive number", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsZeroAmountBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "0.004",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "0.004",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("Amount must be a positive number", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsUnsupportedCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "AAA",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("Unsupported currency", viewModel.state.value.error)
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsNonBaseCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "USD",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals(
            "Standalone Operations currently supports base-currency records only (KZT)",
            viewModel.state.value.error,
        )
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createRejectsNumericOnlyTagsBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
                tags = listOf("123", "work"),
            )
        )

        assertEquals(
            "Invalid tag: tags must not contain numbers only (\"123\")",
            viewModel.state.value.error,
        )
        assertEquals(0, adapter.createCalls)
    }

    @Test
    fun createSuccessShowsNotice() {
        val adapter = FakeEngineAdapter(records = mutableListOf())
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals(1, adapter.createCalls)
        assertEquals("Operation added", viewModel.state.value.notice)
    }

    @Test
    fun createRuntimeFailureSurfacesInState() {
        val adapter = FakeEngineAdapter(createError = NoClassDefFoundError("missing create lambda"))
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.create(
            CreateOperationRequest(
                type = "income",
                date = "2026-01-01",
                walletId = 1,
                amountOriginal = "10",
                currency = "KZT",
                rateAtOperation = "1",
                amountBase = "10",
                category = "Salary",
                description = "",
            )
        )

        assertEquals("missing create lambda", viewModel.state.value.error)
        assertEquals(null, viewModel.state.value.notice)
    }

    @Test
    fun createTransferRejectsSameWalletBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createTransfer(validTransferRequest(toWalletId = 1))

        assertEquals("Transfer wallets must be different", viewModel.state.value.error)
        assertEquals(0, adapter.createTransferCalls)
    }

    @Test
    fun createTransferRejectsInvalidAmountBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createTransfer(validTransferRequest(amount = "0"))

        assertEquals("Amount must be a positive number", viewModel.state.value.error)
        assertEquals(0, adapter.createTransferCalls)
    }

    @Test
    fun createTransferRejectsNegativeCommissionBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createTransfer(validTransferRequest(commissionAmount = "-1"))

        assertEquals("Amount must be zero or a positive number", viewModel.state.value.error)
        assertEquals(0, adapter.createTransferCalls)
    }

    @Test
    fun createTransferRejectsNonBaseCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter()
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createTransfer(validTransferRequest(currency = "USD"))

        assertEquals(
            "Transfer creator currently supports base-currency transfers only (KZT)",
            viewModel.state.value.error,
        )
        assertEquals(0, adapter.createTransferCalls)
    }

    @Test
    fun createTransferSuccessRefreshesStateAndShowsNotice() {
        val adapter = FakeEngineAdapter(records = mutableListOf())
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.createTransfer(validTransferRequest())

        assertEquals(1, adapter.createTransferCalls)
        assertEquals("Transfer created (id=42): Cash -> Card, 10 KZT", viewModel.state.value.notice)
        assertEquals(
            listOf("90.00", "10.00"),
            viewModel.state.value.wallets.map { it.balance },
        )
        assertEquals(
            listOf("expense:42", "income:42"),
            viewModel.state.value.records.map { "${it.type}:${it.transferId}" },
        )
        assertEquals(2, adapter.refreshCalls)
    }

    @Test
    fun selectTransferLinkedRecordShowsReadOnlyNotice() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 7, transferId = 42, category = "Transfer"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(7)

        assertEquals("Transfer-linked rows are read-only in this beta.1 slice", viewModel.state.value.notice)
        assertEquals(null, viewModel.state.value.editDraft)
        assertEquals(null, viewModel.state.value.selectedRecordId)
    }

    @Test
    fun createTransferEngineErrorSurfacesInState() {
        val adapter = FakeEngineAdapter(transferError = IllegalStateException("insufficient funds"))
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.createTransfer(validTransferRequest())

        assertEquals("insufficient funds", viewModel.state.value.error)
        assertEquals(null, viewModel.state.value.notice)
    }

    @Test
    fun selectPopulatesEditDraft() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(
                operationRecord(id = 7, category = "Food", tags = listOf("home")),
            )
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(7)

        assertEquals(7, viewModel.state.value.editDraft?.id)
        assertEquals("Food", viewModel.state.value.editDraft?.category)
        assertEquals("home", viewModel.state.value.editDraft?.tagsText)
    }

    @Test
    fun updateSelectedRefreshesRecords() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(category = "Updated"))
        viewModel.updateSelected()

        assertEquals(1, adapter.updateCalls)
        assertEquals("Updated", viewModel.state.value.records.single().category)
        assertEquals(null, viewModel.state.value.selectedRecordId)
        assertEquals(null, viewModel.state.value.editDraft)
        assertEquals("Operation updated", viewModel.state.value.notice)
    }

    @Test
    fun updateSelectedRejectsInvalidDateBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(date = "2026-13-01"))
        viewModel.updateSelected()

        assertEquals("Date must use a valid YYYY-MM-DD value", viewModel.state.value.error)
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun updateSelectedRejectsFutureDateBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(date = "2999-01-01"))
        viewModel.updateSelected()

        assertEquals("Date cannot be in the future", viewModel.state.value.error)
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun updateSelectedRejectsInvalidCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(currency = "US1"))
        viewModel.updateSelected()

        assertEquals("Currency code must contain 3 letters", viewModel.state.value.error)
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun updateSelectedRejectsInvalidAmountBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(amountOriginal = "-1"))
        viewModel.updateSelected()

        assertEquals("Amount must be a positive number", viewModel.state.value.error)
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun updateSelectedRejectsUnsupportedCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(currency = "AAA"))
        viewModel.updateSelected()

        assertEquals("Unsupported currency", viewModel.state.value.error)
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun updateSelectedRejectsNonBaseCurrencyBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(currency = "USD"))
        viewModel.updateSelected()

        assertEquals(
            "Standalone Operations currently supports base-currency records only (KZT)",
            viewModel.state.value.error,
        )
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun updateSelectedRejectsNumericOnlyTagsBeforeEngineCall() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1, category = "Food"))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(tagsText = "#777, food"))
        viewModel.updateSelected()

        assertEquals(
            "Invalid tag: tags must not contain numbers only (\"777\")",
            viewModel.state.value.error,
        )
        assertEquals(0, adapter.updateCalls)
    }

    @Test
    fun deleteSelectedRefreshesRecords() {
        val adapter = FakeEngineAdapter(
            records = mutableListOf(operationRecord(id = 1), operationRecord(id = 2))
        )
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.deleteSelected()

        assertEquals(1, adapter.deleteCalls)
        assertEquals(listOf(2L), viewModel.state.value.records.map { it.id })
        assertEquals(null, viewModel.state.value.selectedRecordId)
        assertEquals("Operation deleted", viewModel.state.value.notice)
    }

    @Test
    fun engineErrorSurfacesInState() {
        val adapter = FakeEngineAdapter(updateError = IllegalStateException("update failed"))
        val viewModel = OperationsViewModel(adapter, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.select(1)
        viewModel.updateSelected()

        assertEquals("update failed", viewModel.state.value.error)
    }
}

private class FakeEngineAdapter(
    private val records: MutableList<OperationRecord> = mutableListOf(operationRecord(id = 1)),
    private val createError: Throwable? = null,
    private val updateError: Throwable? = null,
    private val transferError: Throwable? = null,
    private val wallets: MutableList<WalletOption> = mutableListOf(
        WalletOption(id = 1, name = "Cash", currency = "KZT", balance = "100.00"),
        WalletOption(id = 2, name = "Card", currency = "KZT", balance = "0.00"),
    ),
) : EngineAdapter {
    var createCalls = 0
    var createTransferCalls = 0
    var updateCalls = 0
    var deleteCalls = 0
    var refreshCalls = 0

    override suspend fun status() = EngineStatus(true, "test.db", "ready")

    override suspend fun baseCurrency(): String = "KZT"

    override suspend fun listRecords(filter: OperationFilter): List<OperationRecord> {
        refreshCalls += 1
        return records.toList()
    }

    override suspend fun getRecord(recordId: Long): OperationRecord? =
        records.firstOrNull { it.id == recordId }

    override suspend fun createRecord(request: CreateOperationRequest): OperationRecord {
        createError?.let { throw it }
        createCalls += 1
        val record = OperationRecord(
            id = (records.maxOfOrNull { it.id } ?: 0) + 1,
            type = request.type,
            date = request.date,
            walletId = request.walletId,
            amountOriginal = request.amountOriginal,
            currency = request.currency,
            rateAtOperation = request.rateAtOperation,
            amountBase = request.amountBase,
            category = request.category,
            description = request.description,
            tags = request.tags,
        )
        records += record
        return record
    }

    override suspend fun updateRecord(recordId: Long, request: UpdateOperationRequest): OperationRecord {
        updateError?.let { throw it }
        updateCalls += 1
        val updated = operationRecord(
            id = recordId,
            type = request.type,
            date = request.date,
            walletId = request.walletId,
            amountOriginal = request.amountOriginal,
            currency = request.currency,
            rateAtOperation = request.rateAtOperation,
            amountBase = request.amountBase,
            category = request.category,
            description = request.description,
            tags = request.tags,
        )
        val index = records.indexOfFirst { it.id == recordId }
        if (index >= 0) {
            records[index] = updated
        }
        return updated
    }

    override suspend fun deleteRecord(recordId: Long): Boolean {
        deleteCalls += 1
        return records.removeIf { it.id == recordId }
    }

    override suspend fun createTransfer(request: CreateTransferRequest): CreateTransferResult {
        transferError?.let { throw it }
        createTransferCalls += 1
        val transferId = 42L
        val amount = request.amount.toDouble()
        replaceWalletBalance(request.fromWalletId) { balance -> balance - amount }
        replaceWalletBalance(request.toWalletId) { balance -> balance + amount }
        records += operationRecord(
            id = (records.maxOfOrNull { it.id } ?: 0) + 1,
            type = "expense",
            walletId = request.fromWalletId,
            amountOriginal = request.amount,
            amountBase = request.amount,
            category = "Transfer",
            description = request.description,
            transferId = transferId,
        )
        records += operationRecord(
            id = (records.maxOfOrNull { it.id } ?: 0) + 1,
            type = "income",
            walletId = request.toWalletId,
            amountOriginal = request.amount,
            amountBase = request.amount,
            category = "Transfer",
            description = request.description,
            transferId = transferId,
        )
        return CreateTransferResult(transferId = transferId)
    }

    override suspend fun listTags(): List<String> = listOf("home")

    override suspend fun listCategories(recordType: String): List<String> = listOf("Food")

    override suspend fun listWallets(): List<WalletOption> = emptyList()

    override suspend fun walletBalances(): List<WalletOption> = wallets.toList()

    override suspend fun listWalletsForSettings(): List<WalletSettingsItem> = emptyList()

    override suspend fun createWallet(request: CreateWalletRequest): WalletSettingsItem =
        WalletSettingsItem(
            id = 1,
            name = request.name,
            currency = request.currency,
            initialBalance = request.initialBalance,
            balance = request.initialBalance,
            system = false,
            allowNegative = request.allowNegative,
            active = true,
        )

    private fun replaceWalletBalance(walletId: Long, update: (Double) -> Double) {
        val index = wallets.indexOfFirst { it.id == walletId }
        if (index < 0) {
            return
        }
        val wallet = wallets[index]
        wallets[index] = wallet.copy(balance = String.format(Locale.US, "%.2f", update(wallet.balance.toDouble())))
    }
}

private fun validTransferRequest(
    fromWalletId: Long = 1,
    toWalletId: Long = 2,
    date: String = "2026-01-01",
    amount: String = "10",
    currency: String = "KZT",
    commissionAmount: String = "0",
    commissionCurrency: String = "KZT",
) = CreateTransferRequest(
    fromWalletId = fromWalletId,
    toWalletId = toWalletId,
    date = date,
    amount = amount,
    currency = currency,
    description = "Move",
    commissionAmount = commissionAmount,
    commissionCurrency = commissionCurrency,
)

private fun operationRecord(
    id: Long,
    type: String = "expense",
    date: String = "2026-01-01",
    walletId: Long = 1,
    amountOriginal: String = "10.00",
    currency: String = "KZT",
    rateAtOperation: String = "1.000000",
    amountBase: String = "10.00",
    category: String = "General",
    description: String = "",
    tags: List<String> = emptyList(),
    transferId: Long? = null,
    relatedDebtId: Long? = null,
) = OperationRecord(
    id = id,
    type = type,
    date = date,
    walletId = walletId,
    transferId = transferId,
    relatedDebtId = relatedDebtId,
    amountOriginal = amountOriginal,
    currency = currency,
    rateAtOperation = rateAtOperation,
    amountBase = amountBase,
    category = category,
    description = description,
    tags = tags,
)
