package app.ledgera.bridge

import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.EngineStatus
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.UpdateOperationRequest
import app.ledgera.model.WalletOption

interface RuntimeEngine {
    suspend fun status(): EngineStatus
}

interface OperationsEngine {
    suspend fun baseCurrency(): String
    suspend fun listRecords(filter: OperationFilter): List<OperationRecord>
    suspend fun getRecord(recordId: Long): OperationRecord?
    suspend fun createRecord(request: CreateOperationRequest): OperationRecord
    suspend fun updateRecord(recordId: Long, request: UpdateOperationRequest): OperationRecord
    suspend fun deleteRecord(recordId: Long): Boolean
    suspend fun listTags(): List<String>
    suspend fun listCategories(recordType: String): List<String>
    suspend fun listWallets(): List<WalletOption>
    suspend fun walletBalances(): List<WalletOption>
}

interface EngineAdapter : RuntimeEngine, OperationsEngine
