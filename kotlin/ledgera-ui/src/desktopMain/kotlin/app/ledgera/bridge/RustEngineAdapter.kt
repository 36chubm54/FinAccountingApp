package app.ledgera.bridge

import app.ledgera.engine.CreateRecordRequest as NativeCreateRecordRequest
import app.ledgera.engine.CreateTransferRequest as NativeCreateTransferRequest
import app.ledgera.engine.CreateWalletRequest as NativeCreateWalletRequest
import app.ledgera.engine.LedgeraEngine
import app.ledgera.engine.RecordFilterDto
import app.ledgera.engine.UpdateRecordRequest as NativeUpdateRecordRequest
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
}
