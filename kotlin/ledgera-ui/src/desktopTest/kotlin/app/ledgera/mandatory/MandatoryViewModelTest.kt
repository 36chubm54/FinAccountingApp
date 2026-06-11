package app.ledgera.mandatory

import app.ledgera.bridge.MandatoryEngine
import app.ledgera.model.AddMandatoryToRecordsRequest
import app.ledgera.model.CreateMandatoryTemplateRequest
import app.ledgera.model.MandatoryAutoPayResult
import app.ledgera.model.MandatoryTemplateItem
import app.ledgera.model.OperationRecord
import app.ledgera.model.UpdateMandatoryTemplateRequest
import app.ledgera.model.WalletOption
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class MandatoryViewModelTest {
    @Test
    fun refreshLoadsWalletsTemplatesAndSelection() {
        val engine = FakeMandatoryEngine()
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()

        assertEquals("KZT", viewModel.state.value.baseCurrency)
        assertEquals(listOf("Cash"), viewModel.state.value.wallets.map { it.name })
        assertEquals(listOf("Rent"), viewModel.state.value.templates.map { it.category })
        assertEquals(1, viewModel.state.value.selectedTemplateId)
    }

    @Test
    fun createRejectsInvalidDraftBeforeEngineCall() {
        val engine = FakeMandatoryEngine()
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openCreateDialog()
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(description = "", amountOriginal = "10", amountBase = "10"))
        viewModel.saveTemplate()

        assertEquals("Description is required", viewModel.state.value.error)
        assertEquals(0, engine.createCalls)
    }

    @Test
    fun createSuccessRefreshesAndShowsNotice() {
        val engine = FakeMandatoryEngine(templates = mutableListOf())
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openCreateDialog()
        viewModel.updateDraft(
            viewModel.state.value.editDraft!!.copy(
                amountOriginal = "25",
                amountBase = "25",
                description = "Internet",
            )
        )
        viewModel.saveTemplate()

        assertEquals(1, engine.createCalls)
        assertNull(viewModel.state.value.editDraft)
        assertEquals("Mandatory template created (id=1)", viewModel.state.value.notice)
        assertEquals(listOf("Internet"), viewModel.state.value.templates.map { it.description })
    }

    @Test
    fun updateSuccessClosesDialogAndShowsNotice() {
        val engine = FakeMandatoryEngine()
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.selectTemplate(1)
        viewModel.updateDraft(viewModel.state.value.editDraft!!.copy(amountBase = "35", period = "weekly"))
        viewModel.saveTemplate()

        assertEquals(1, engine.updateCalls)
        assertNull(viewModel.state.value.editDraft)
        assertEquals("Mandatory template updated (id=1)", viewModel.state.value.notice)
        assertEquals("weekly", viewModel.state.value.templates.first().period)
    }

    @Test
    fun addToRecordsSuccessRefreshesAndShowsNotice() {
        val engine = FakeMandatoryEngine()
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openAddToRecordsDialog()
        viewModel.addToRecords()

        assertEquals(1, engine.addToRecordsCalls)
        assertNull(viewModel.state.value.addToRecordsDraft)
        assertEquals("Mandatory record added (id=7)", viewModel.state.value.notice)
    }

    @Test
    fun autoPaySuccessShowsCreatedCount() {
        val engine = FakeMandatoryEngine(autoPayRecords = listOf(operationRecord(id = 8), operationRecord(id = 9)))
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.applyAutoPayments()

        assertEquals(1, engine.autoPayCalls)
        assertEquals("Auto-pay applied: 2 records", viewModel.state.value.notice)
    }

    @Test
    fun deleteSelectedSuccessRefreshesAndShowsNotice() {
        val engine = FakeMandatoryEngine()
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.requestDeleteSelectedTemplate()
        viewModel.deleteSelectedTemplate()

        assertEquals(1, engine.deleteCalls)
        assertEquals("Mandatory template deleted (id=1)", viewModel.state.value.notice)
        assertEquals(emptyList(), viewModel.state.value.templates)
    }

    @Test
    fun deleteAllSuccessRefreshesAndShowsNotice() {
        val engine = FakeMandatoryEngine()
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.requestDeleteAllTemplates()
        viewModel.deleteAllTemplates()

        assertEquals(1, engine.deleteAllCalls)
        assertEquals("All mandatory templates deleted (1)", viewModel.state.value.notice)
        assertEquals(emptyList(), viewModel.state.value.templates)
    }

    @Test
    fun engineErrorKeepsDialogOpen() {
        val engine = FakeMandatoryEngine(createError = IllegalStateException("boom"))
        val viewModel = MandatoryViewModel(engine, CoroutineScope(Dispatchers.Unconfined))

        viewModel.refresh()
        viewModel.openCreateDialog()
        viewModel.updateDraft(
            viewModel.state.value.editDraft!!.copy(
                amountOriginal = "25",
                amountBase = "25",
                description = "Internet",
            )
        )
        viewModel.saveTemplate()

        assertEquals("boom", viewModel.state.value.error)
        assertEquals(1, engine.createCalls)
        assertEquals("Internet", viewModel.state.value.editDraft?.description)
    }
}

private class FakeMandatoryEngine(
    private val templates: MutableList<MandatoryTemplateItem> = mutableListOf(mandatoryTemplate()),
    private val createError: Throwable? = null,
    private val autoPayRecords: List<OperationRecord> = emptyList(),
) : MandatoryEngine {
    var createCalls = 0
    var updateCalls = 0
    var addToRecordsCalls = 0
    var autoPayCalls = 0
    var deleteCalls = 0
    var deleteAllCalls = 0

    override suspend fun baseCurrency(): String = "KZT"

    override suspend fun listWallets(): List<WalletOption> =
        listOf(WalletOption(id = 1, name = "Cash", currency = "KZT", balance = "100.00"))

    override suspend fun listMandatoryTemplates(): List<MandatoryTemplateItem> = templates.toList()

    override suspend fun getMandatoryTemplate(templateId: Long): MandatoryTemplateItem? =
        templates.firstOrNull { it.id == templateId }

    override suspend fun createMandatoryTemplate(request: CreateMandatoryTemplateRequest): MandatoryTemplateItem {
        createCalls += 1
        createError?.let { throw it }
        val template = mandatoryTemplate(
            id = (templates.maxOfOrNull { it.id } ?: 0) + 1,
            walletId = request.walletId,
            amountOriginal = request.amountOriginal,
            amountBase = request.amountBase,
            category = request.category,
            description = request.description,
            period = request.period,
            date = request.date,
        )
        templates += template
        return template
    }

    override suspend fun updateMandatoryTemplate(
        templateId: Long,
        request: UpdateMandatoryTemplateRequest,
    ): MandatoryTemplateItem {
        updateCalls += 1
        val updated = templates.first { it.id == templateId }.copy(
            walletId = request.walletId,
            amountBase = request.amountBase,
            period = request.period,
            date = request.date,
            autoPay = request.date.isNotBlank(),
        )
        templates[templates.indexOfFirst { it.id == templateId }] = updated
        return updated
    }

    override suspend fun deleteMandatoryTemplate(templateId: Long): Boolean {
        deleteCalls += 1
        templates.removeIf { it.id == templateId }
        return true
    }

    override suspend fun deleteAllMandatoryTemplates(): Long {
        deleteAllCalls += 1
        val deleted = templates.size.toLong()
        templates.clear()
        return deleted
    }

    override suspend fun addMandatoryToRecords(request: AddMandatoryToRecordsRequest): OperationRecord {
        addToRecordsCalls += 1
        return operationRecord(id = 7, date = request.date, walletId = request.walletId)
    }

    override suspend fun applyMandatoryAutoPayments(today: String): MandatoryAutoPayResult {
        autoPayCalls += 1
        return MandatoryAutoPayResult(createdRecords = autoPayRecords)
    }
}

private fun mandatoryTemplate(
    id: Long = 1,
    walletId: Long = 1,
    amountOriginal: String = "30.00",
    amountBase: String = "30.00",
    category: String = "Rent",
    description: String = "Monthly rent",
    period: String = "monthly",
    date: String = "2026-01-01",
) = MandatoryTemplateItem(
    id = id,
    walletId = walletId,
    amountOriginal = amountOriginal,
    currency = "KZT",
    rateAtOperation = "1.000000",
    amountBase = amountBase,
    category = category,
    description = description,
    period = period,
    date = date,
    autoPay = date.isNotBlank(),
)

private fun operationRecord(
    id: Long,
    date: String = "2026-01-01",
    walletId: Long = 1,
) = OperationRecord(
    id = id,
    type = "mandatory_expense",
    date = date,
    walletId = walletId,
    amountOriginal = "10.00",
    currency = "KZT",
    rateAtOperation = "1.000000",
    amountBase = "10.00",
    category = "Rent",
    description = "Monthly rent",
    tags = emptyList(),
)
