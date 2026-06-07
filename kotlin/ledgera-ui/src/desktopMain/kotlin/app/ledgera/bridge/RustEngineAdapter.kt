package app.ledgera.bridge

import app.ledgera.engine.CreateRecordRequest as NativeCreateRecordRequest
import app.ledgera.engine.CreateTransferRequest as NativeCreateTransferRequest
import app.ledgera.engine.CreateWalletRequest as NativeCreateWalletRequest
import app.ledgera.engine.LedgeraEngine
import app.ledgera.engine.RecordFilterDto
import app.ledgera.engine.UpdateRecordRequest as NativeUpdateRecordRequest
import app.ledgera.engine.UpdateTransferRequest as NativeUpdateTransferRequest
import app.ledgera.model.AuditFinding
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.CreateTransferRequest
import app.ledgera.model.CreateTransferResult
import app.ledgera.model.CreateWalletRequest
import app.ledgera.model.EngineStatus
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationDeleteResult
import app.ledgera.model.OperationRecord
import app.ledgera.model.TransferDetails
import app.ledgera.model.UpdateOperationRequest
import app.ledgera.model.UpdateTransferRequest
import app.ledgera.model.UpdateTransferResult
import app.ledgera.model.WalletDeleteResult
import app.ledgera.model.WalletOption
import app.ledgera.model.WalletSettingsItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class RustEngineAdapter(dbPath: String) : EngineAdapter {
    init {
        NativeLibraryLoader.ensureAvailable()
    }

    private val engine = LedgeraEngine(dbPath)

    override suspend fun status(): EngineStatus = withContext(Dispatchers.IO) {
        engine.engineStatus().let { EngineStatus(it.ok, it.dbPath, it.message) }
    }

    override suspend fun baseCurrency(): String = withContext(Dispatchers.IO) {
        engine.baseCurrency()
    }

    override suspend fun listRecords(filter: OperationFilter): List<OperationRecord> =
        withContext(Dispatchers.IO) {
            engine.listRecords(
                RecordFilterDto(
                    startDate = filter.startDate,
                    endDate = filter.endDate,
                    walletId = filter.walletId,
                    recordType = filter.recordType,
                )
            ).map(::toOperationRecord)
        }

    override suspend fun getRecord(recordId: Long): OperationRecord? = withContext(Dispatchers.IO) {
        engine.getRecord(recordId)?.let(::toOperationRecord)
    }

    override suspend fun createRecord(request: CreateOperationRequest): OperationRecord =
        withContext(Dispatchers.IO) {
            engine.createRecord(
                NativeCreateRecordRequest(
                    recordType = request.type,
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
            ).let(::toOperationRecord)
        }

    override suspend fun updateRecord(recordId: Long, request: UpdateOperationRequest): OperationRecord =
        withContext(Dispatchers.IO) {
            engine.updateRecord(
                recordId,
                NativeUpdateRecordRequest(
                    recordType = request.type,
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
            ).let(::toOperationRecord)
        }

    override suspend fun deleteRecord(recordId: Long): Boolean = withContext(Dispatchers.IO) {
        engine.deleteRecord(recordId)
    }

    override suspend fun createTransfer(request: CreateTransferRequest): CreateTransferResult =
        withContext(Dispatchers.IO) {
            engine.createTransfer(
                NativeCreateTransferRequest(
                    fromWalletId = request.fromWalletId,
                    toWalletId = request.toWalletId,
                    date = request.date,
                    amount = request.amount,
                    currency = request.currency,
                    description = request.description,
                    commissionAmount = request.commissionAmount,
                    commissionCurrency = request.commissionCurrency,
                )
            ).let { CreateTransferResult(transferId = it.transferId) }
        }

    override suspend fun getTransfer(transferId: Long): TransferDetails? = withContext(Dispatchers.IO) {
        engine.getTransfer(transferId)?.let(::toTransferDetails)
    }

    override suspend fun updateTransfer(
        transferId: Long,
        request: UpdateTransferRequest,
    ): UpdateTransferResult = withContext(Dispatchers.IO) {
        engine.updateTransfer(
            transferId,
            NativeUpdateTransferRequest(
                fromWalletId = request.fromWalletId,
                toWalletId = request.toWalletId,
                date = request.date,
                amount = request.amount,
                currency = request.currency,
                description = request.description,
            )
        ).let { UpdateTransferResult(transferId = it.transferId) }
    }

    override suspend fun deleteTransfer(transferId: Long): Boolean = withContext(Dispatchers.IO) {
        engine.deleteTransfer(transferId)
    }

    override suspend fun deleteAllOperations(): OperationDeleteResult = withContext(Dispatchers.IO) {
        engine.deleteAllOperations().let {
            OperationDeleteResult(
                deletedRecords = it.deletedRecords,
                deletedTransfers = it.deletedTransfers,
                skippedRecords = it.skippedRecords,
            )
        }
    }

    override suspend fun deleteOperationsSelection(
        recordIds: List<Long>,
        transferIds: List<Long>,
    ): OperationDeleteResult = withContext(Dispatchers.IO) {
        engine.deleteOperationsSelection(recordIds, transferIds).let {
            OperationDeleteResult(
                deletedRecords = it.deletedRecords,
                deletedTransfers = it.deletedTransfers,
                skippedRecords = it.skippedRecords,
            )
        }
    }

    override suspend fun listTags(): List<String> = withContext(Dispatchers.IO) {
        engine.listTags()
    }

    override suspend fun listCategories(recordType: String): List<String> = withContext(Dispatchers.IO) {
        engine.listCategories(recordType)
    }

    override suspend fun listWallets(): List<WalletOption> = withContext(Dispatchers.IO) {
        engine.listWallets().filter { it.isActive }.map {
            WalletOption(id = it.id, name = it.name, currency = it.currency)
        }
    }

    override suspend fun walletBalances(): List<WalletOption> = withContext(Dispatchers.IO) {
        engine.walletBalances().map {
            WalletOption(id = it.walletId, name = it.name, currency = it.currency, balance = it.balance)
        }
    }

    override suspend fun listWalletsForSettings(): List<WalletSettingsItem> = withContext(Dispatchers.IO) {
        val balancesById = engine.walletBalances().associateBy { it.walletId }
        engine.listWallets().map { wallet ->
            WalletSettingsItem(
                id = wallet.id,
                name = wallet.name,
                currency = wallet.currency,
                initialBalance = wallet.initialBalance,
                balance = balancesById[wallet.id]?.balance ?: wallet.initialBalance,
                system = wallet.system,
                allowNegative = wallet.allowNegative,
                active = wallet.isActive,
            )
        }
    }

    override suspend fun createWallet(request: CreateWalletRequest): WalletSettingsItem =
        withContext(Dispatchers.IO) {
            val created = engine.createWallet(
                NativeCreateWalletRequest(
                    name = request.name,
                    currency = request.currency,
                    initialBalance = request.initialBalance,
                    allowNegative = request.allowNegative,
                )
            )
            WalletSettingsItem(
                id = created.id,
                name = created.name,
                currency = created.currency,
                initialBalance = created.initialBalance,
                balance = created.initialBalance,
                system = created.system,
                allowNegative = created.allowNegative,
                active = created.isActive,
            )
        }

    override suspend fun deleteWallet(walletId: Long): WalletDeleteResult = withContext(Dispatchers.IO) {
        val result = engine.deleteWallet(walletId)
        WalletDeleteResult(
            walletId = result.walletId,
            action = result.action,
        )
    }

    override suspend fun runAudit(): List<AuditFinding> = withContext(Dispatchers.IO) {
        engine.auditRun().map {
            AuditFinding(
                check = it.check,
                severity = it.severity,
                message = it.message,
                entity = it.entity,
            )
        }
    }

    private fun toOperationRecord(record: app.ledgera.engine.RecordDto): OperationRecord =
        OperationRecord(
            id = record.id,
            type = record.recordType,
            date = record.date,
            walletId = record.walletId,
            transferId = record.transferId,
            relatedDebtId = record.relatedDebtId,
            amountOriginal = record.amountOriginal,
            currency = record.currency,
            rateAtOperation = record.rateAtOperation,
            amountBase = record.amountBase,
            category = record.category,
            description = record.description,
            tags = record.tags,
        )

    private fun toTransferDetails(transfer: app.ledgera.engine.TransferDto): TransferDetails =
        TransferDetails(
            id = transfer.id,
            fromWalletId = transfer.fromWalletId,
            toWalletId = transfer.toWalletId,
            date = transfer.date,
            amountOriginal = transfer.amountOriginal,
            currency = transfer.currency,
            rateAtOperation = transfer.rateAtOperation,
            amountBase = transfer.amountBase,
            description = transfer.description,
        )
}
