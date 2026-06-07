package app.ledgera.operations

import app.ledgera.model.OperationRecord

internal data class OperationJournalItem(
    val key: String,
    val title: String,
    val amount: String,
    val meta: String,
    val description: String,
    val tags: List<String>,
    val selectableRecordId: Long?,
    val transferId: Long?,
    val selected: Boolean,
)

internal fun operationJournalItems(
    records: List<OperationRecord>,
    selectedRecordId: Long?,
): List<OperationJournalItem> {
    val consumedTransferIds = mutableSetOf<Long>()
    val result = mutableListOf<OperationJournalItem>()
    records.forEach { record ->
        val transferId = record.transferId
        if (transferId == null) {
            result += standaloneJournalItem(record, selectedRecordId)
            return@forEach
        }
        if (!consumedTransferIds.add(transferId)) {
            return@forEach
        }
        result += transferJournalItem(
            records = records.filter { it.transferId == transferId },
            transferId = transferId,
        )
    }
    return result
}

private fun standaloneJournalItem(
    record: OperationRecord,
    selectedRecordId: Long?,
): OperationJournalItem =
    OperationJournalItem(
        key = "record:${record.id}",
        title = if (selectedRecordId == record.id) "${record.category} · selected" else record.category,
        amount = "${record.amountOriginal} ${record.currency}",
        meta = "${record.date} · ${record.type} · wallet #${record.walletId}",
        description = record.description,
        tags = record.tags,
        selectableRecordId = record.id,
        transferId = null,
        selected = selectedRecordId == record.id,
    )

private fun transferJournalItem(
    records: List<OperationRecord>,
    transferId: Long,
): OperationJournalItem {
    val expense = records.firstOrNull { it.type == "expense" }
    val income = records.firstOrNull { it.type == "income" }
    val primary = expense ?: income ?: records.first()
    val direction = if (expense != null && income != null) {
        "wallet #${expense.walletId} -> wallet #${income.walletId}"
    } else {
        "wallet #${primary.walletId}"
    }
    return OperationJournalItem(
        key = "transfer:$transferId",
        title = "Transfer · transfer #$transferId",
        amount = "${primary.amountOriginal} ${primary.currency}",
        meta = "${primary.date} · transfer · $direction",
        description = primary.description,
        tags = emptyList(),
        selectableRecordId = null,
        transferId = transferId,
        selected = false,
    )
}
