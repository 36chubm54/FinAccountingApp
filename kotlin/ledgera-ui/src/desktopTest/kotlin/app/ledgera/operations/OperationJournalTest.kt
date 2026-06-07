package app.ledgera.operations

import app.ledgera.model.OperationRecord
import kotlin.test.Test
import kotlin.test.assertEquals

class OperationJournalTest {
    @Test
    fun transferLinkedMirrorRowsRenderAsSingleJournalItemWithDirection() {
        val rows = listOf(
            operationRecord(id = 10, type = "income", walletId = 2, transferId = 7),
            operationRecord(id = 9, type = "expense", walletId = 1, transferId = 7),
        )

        val items = operationJournalItems(rows, selectedRecordId = null)

        assertEquals(1, items.size)
        assertEquals("transfer:7", items.single().key)
        assertEquals("Transfer · transfer #7", items.single().title)
        assertEquals("2026-01-01 · transfer · wallet #1 -> wallet #2", items.single().meta)
        assertEquals(7, items.single().transferId)
        assertEquals(null, items.single().selectableRecordId)
    }

    @Test
    fun standaloneRowsRemainIndividualEditableJournalItems() {
        val rows = listOf(operationRecord(id = 3, category = "Food"))

        val items = operationJournalItems(rows, selectedRecordId = 3)

        assertEquals(1, items.size)
        assertEquals("record:3", items.single().key)
        assertEquals("Food · selected", items.single().title)
        assertEquals(3, items.single().selectableRecordId)
        assertEquals(null, items.single().transferId)
    }
}

private fun operationRecord(
    id: Long,
    type: String = "expense",
    walletId: Long = 1,
    category: String = "Transfer",
    transferId: Long? = null,
) = OperationRecord(
    id = id,
    type = type,
    date = "2026-01-01",
    walletId = walletId,
    transferId = transferId,
    relatedDebtId = null,
    amountOriginal = "10.00",
    currency = "KZT",
    rateAtOperation = "1.000000",
    amountBase = "10.00",
    category = category,
    description = "",
    tags = emptyList(),
)
