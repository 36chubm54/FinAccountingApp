package app.ledgera.operations

import app.ledgera.bridge.EngineAdapter
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.EngineStatus
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.WalletOption
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
}

private class FakeEngineAdapter : EngineAdapter {
    var createCalls = 0

    override suspend fun status() = EngineStatus(true, "test.db", "ready")

    override suspend fun listRecords(filter: OperationFilter): List<OperationRecord> = emptyList()

    override suspend fun createRecord(request: CreateOperationRequest): OperationRecord {
        createCalls += 1
        return OperationRecord(
            id = 1,
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
    }

    override suspend fun listWallets(): List<WalletOption> = emptyList()

    override suspend fun walletBalances(): List<WalletOption> = emptyList()
}
