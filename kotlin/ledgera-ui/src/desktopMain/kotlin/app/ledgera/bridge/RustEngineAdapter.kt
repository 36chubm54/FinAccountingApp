package app.ledgera.bridge

import app.ledgera.engine.CreateRecordRequest as NativeCreateRecordRequest
import app.ledgera.engine.LedgeraEngine
import app.ledgera.engine.RecordFilterDto
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.EngineStatus
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.WalletOption
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

    override suspend fun listRecords(filter: OperationFilter): List<OperationRecord> =
        withContext(Dispatchers.IO) {
            engine.listRecords(
                RecordFilterDto(
                    startDate = filter.startDate,
                    endDate = filter.endDate,
                    walletId = filter.walletId,
                    recordType = filter.recordType,
                )
            ).map {
                OperationRecord(
                    id = it.id,
                    type = it.recordType,
                    date = it.date,
                    walletId = it.walletId,
                    amountOriginal = it.amountOriginal,
                    currency = it.currency,
                    rateAtOperation = it.rateAtOperation,
                    amountBase = it.amountBase,
                    category = it.category,
                    description = it.description,
                    tags = it.tags,
                )
            }
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
            ).let {
                OperationRecord(
                    id = it.id,
                    type = it.recordType,
                    date = it.date,
                    walletId = it.walletId,
                    amountOriginal = it.amountOriginal,
                    currency = it.currency,
                    rateAtOperation = it.rateAtOperation,
                    amountBase = it.amountBase,
                    category = it.category,
                    description = it.description,
                    tags = it.tags,
                )
            }
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
}
