package app.ledgera.debts

import app.ledgera.bridge.DebtsEngine
import app.ledgera.model.CreateDebtRequest
import app.ledgera.model.DebtItem
import app.ledgera.model.DebtPaymentItem
import app.ledgera.model.RegisterDebtPaymentRequest
import app.ledgera.model.WalletOption
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class DebtsViewModelTest {
    @Test
    fun refreshLoadsDebtsWalletsAndSelectedHistory() {
        val engine = FakeDebtsEngine()
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()

        assertEquals("KZT", viewModel.state.value.baseCurrency)
        assertEquals(listOf("Cash"), viewModel.state.value.wallets.map { it.name })
        assertEquals(listOf("Alice"), viewModel.state.value.debts.map { it.contactName })
        assertEquals(1, viewModel.state.value.selectedHistory.size)
    }

    @Test
    fun selectDebtLoadsHistory() {
        val engine = FakeDebtsEngine(
            debts = listOf(debtItem(id = 1, contactName = "Alice"), debtItem(id = 2, contactName = "Bob")),
            historyByDebt = mapOf(2L to listOf(paymentItem(id = 2, debtId = 2))),
        )
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.selectDebt(2)

        assertEquals(2, viewModel.state.value.selectedDebtId)
        assertEquals(listOf(2L), viewModel.state.value.selectedHistory.map { it.id })
    }

    @Test
    fun createDebtRejectsInvalidDraftBeforeEngineCall() {
        val engine = FakeDebtsEngine()
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openCreateDialog("debt")
        viewModel.updateDraft(viewModel.state.value.createDraft!!.copy(contactName = "", amount = "10"))
        viewModel.createDebt()

        assertEquals("Contact name is required", viewModel.state.value.error)
        assertEquals(0, engine.createCalls)
    }

    @Test
    fun createDebtSuccessRefreshesAndShowsNotice() {
        val engine = FakeDebtsEngine(debts = emptyList())
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openCreateDialog("loan")
        viewModel.updateDraft(
            viewModel.state.value.createDraft!!.copy(
                contactName = "Bob",
                amount = "25.00",
                createdAt = "2026-03-01",
            )
        )
        viewModel.createDebt()

        assertEquals(1, engine.createCalls)
        assertNull(viewModel.state.value.createDraft)
        assertEquals("Loan created (id=1)", viewModel.state.value.notice)
        assertEquals(listOf("Bob"), viewModel.state.value.debts.map { it.contactName })
    }

    @Test
    fun createDebtEngineErrorKeepsDialogOpen() {
        val engine = FakeDebtsEngine(createError = IllegalStateException("storage failed"))
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openCreateDialog("debt")
        viewModel.updateDraft(
            viewModel.state.value.createDraft!!.copy(
                contactName = "Alice",
                amount = "25.00",
                createdAt = "2026-03-01",
            )
        )
        viewModel.createDebt()

        assertEquals("storage failed", viewModel.state.value.error)
        assertEquals("Alice", viewModel.state.value.createDraft?.contactName)
        assertNull(viewModel.state.value.notice)
    }

    @Test
    fun paymentValidationBlocksBeforeEngineCall() {
        val engine = FakeDebtsEngine()
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openDebtAction("payment")
        viewModel.updateActionDraft(viewModel.state.value.actionDraft!!.copy(amount = "0"))
        viewModel.submitDebtAction()

        assertEquals("Amount must be a positive number", viewModel.state.value.error)
        assertEquals(0, engine.paymentCalls)
    }

    @Test
    fun paymentSuccessRefreshesHistoryAndShowsNotice() {
        val engine = FakeDebtsEngine(historyByDebt = mapOf(1L to emptyList()))
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openDebtAction("payment")
        viewModel.updateActionDraft(
            viewModel.state.value.actionDraft!!.copy(amount = "10.00", paymentDate = "2026-03-05")
        )
        viewModel.submitDebtAction()

        assertEquals(1, engine.paymentCalls)
        assertNull(viewModel.state.value.actionDraft)
        assertEquals("Payment registered (id=1)", viewModel.state.value.notice)
        assertEquals(listOf(1L), viewModel.state.value.selectedHistory.map { it.id })
    }

    @Test
    fun writeOffEngineErrorKeepsDialogOpen() {
        val engine = FakeDebtsEngine(actionError = IllegalStateException("write-off failed"))
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openDebtAction("write_off")
        viewModel.updateActionDraft(
            viewModel.state.value.actionDraft!!.copy(amount = "10.00", paymentDate = "2026-03-05")
        )
        viewModel.submitDebtAction()

        assertEquals("write-off failed", viewModel.state.value.error)
        assertEquals("write_off", viewModel.state.value.actionDraft?.action)
        assertNull(viewModel.state.value.notice)
    }

    @Test
    fun closeSuccessRefreshesDebtAndShowsNotice() {
        val engine = FakeDebtsEngine()
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openDebtAction("close")
        viewModel.submitDebtAction()

        assertEquals(1, engine.closeCalls)
        assertNull(viewModel.state.value.actionDraft)
        assertEquals("Debt closed (id=1)", viewModel.state.value.notice)
        assertEquals("closed", viewModel.state.value.debts.single().status)
    }

    @Test
    fun closeEngineErrorKeepsDialogOpen() {
        val engine = FakeDebtsEngine(actionError = IllegalStateException("close failed"))
        val viewModel = DebtsViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openDebtAction("close")
        viewModel.submitDebtAction()

        assertEquals("close failed", viewModel.state.value.error)
        assertEquals("close", viewModel.state.value.actionDraft?.action)
        assertNull(viewModel.state.value.notice)
    }
}

private class FakeDebtsEngine(
    private val debts: List<DebtItem> = listOf(debtItem()),
    private val historyByDebt: Map<Long, List<DebtPaymentItem>> = mapOf(1L to listOf(paymentItem())),
    private val createError: Throwable? = null,
    private val actionError: Throwable? = null,
) : DebtsEngine {
    private val mutableDebts = debts.toMutableList()
    private val mutableHistory = historyByDebt.mapValues { it.value.toMutableList() }.toMutableMap()
    var createCalls = 0
    var paymentCalls = 0
    var writeOffCalls = 0
    var closeCalls = 0

    override suspend fun baseCurrency(): String = "KZT"

    override suspend fun listWallets(): List<WalletOption> =
        listOf(WalletOption(id = 1, name = "Cash", currency = "KZT", balance = "100.00"))

    override suspend fun listDebts(): List<DebtItem> = mutableDebts.toList()

    override suspend fun listDebtPayments(debtId: Long): List<DebtPaymentItem> =
        mutableHistory[debtId].orEmpty()

    override suspend fun createDebt(request: CreateDebtRequest): DebtItem {
        createError?.let { throw it }
        createCalls += 1
        val debt = debtItem(
            id = (mutableDebts.maxOfOrNull { it.id } ?: 0) + 1,
            contactName = request.contactName,
            kind = request.kind,
            totalAmount = request.amount,
            remainingAmount = request.amount,
            createdAt = request.createdAt,
        )
        mutableDebts += debt
        return debt
    }

    override suspend fun registerDebtPayment(request: RegisterDebtPaymentRequest): DebtPaymentItem {
        actionError?.let { throw it }
        paymentCalls += 1
        val payment = paymentItem(id = nextPaymentId(request.debtId), debtId = request.debtId)
        mutableHistory.getOrPut(request.debtId) { mutableListOf() } += payment
        return payment
    }

    override suspend fun registerDebtWriteOff(request: RegisterDebtPaymentRequest): DebtPaymentItem {
        actionError?.let { throw it }
        writeOffCalls += 1
        val payment = paymentItem(
            id = nextPaymentId(request.debtId),
            debtId = request.debtId,
            operationType = "debt_forgive",
            isWriteOff = true,
        )
        mutableHistory.getOrPut(request.debtId) { mutableListOf() } += payment
        return payment
    }

    override suspend fun closeDebt(request: RegisterDebtPaymentRequest): DebtItem {
        actionError?.let { throw it }
        closeCalls += 1
        val index = mutableDebts.indexOfFirst { it.id == request.debtId }
        val closed = mutableDebts[index].copy(status = "closed", remainingAmount = "0.00", closedAt = request.paymentDate)
        mutableDebts[index] = closed
        mutableHistory.getOrPut(request.debtId) { mutableListOf() } += paymentItem(
            id = nextPaymentId(request.debtId),
            debtId = request.debtId,
        )
        return closed
    }

    private fun nextPaymentId(debtId: Long): Long =
        (mutableHistory[debtId].orEmpty().maxOfOrNull { it.id } ?: 0) + 1
}

private fun debtItem(
    id: Long = 1,
    contactName: String = "Alice",
    kind: String = "debt",
    totalAmount: String = "50.00",
    remainingAmount: String = "30.00",
    createdAt: String = "2026-03-01",
): DebtItem =
    DebtItem(
        id = id,
        contactName = contactName,
        kind = kind,
        totalAmount = totalAmount,
        remainingAmount = remainingAmount,
        currency = "KZT",
        interestRate = "0.000000",
        status = "open",
        createdAt = createdAt,
    )

private fun paymentItem(
    id: Long = 1,
    debtId: Long = 1,
    operationType: String = "debt_repay",
    isWriteOff: Boolean = false,
): DebtPaymentItem =
    DebtPaymentItem(
        id = id,
        debtId = debtId,
        operationType = operationType,
        principalPaid = "20.00",
        isWriteOff = isWriteOff,
        paymentDate = "2026-03-05",
    )
