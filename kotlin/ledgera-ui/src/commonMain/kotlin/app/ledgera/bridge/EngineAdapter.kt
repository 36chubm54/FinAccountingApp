package app.ledgera.bridge

import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.CreateTransferRequest
import app.ledgera.model.CreateTransferResult
import app.ledgera.model.CreateWalletRequest
import app.ledgera.model.AuditFinding
import app.ledgera.model.EngineStatus
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationDeleteResult
import app.ledgera.model.OperationRecord
import app.ledgera.model.TransferDetails
import app.ledgera.model.UpdateOperationRequest
import app.ledgera.model.UpdateTransferRequest
import app.ledgera.model.UpdateTransferResult
import app.ledgera.model.WalletOption
import app.ledgera.model.WalletDeleteResult
import app.ledgera.model.WalletSettingsItem

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
    suspend fun createTransfer(request: CreateTransferRequest): CreateTransferResult
    suspend fun getTransfer(transferId: Long): TransferDetails?
    suspend fun updateTransfer(transferId: Long, request: UpdateTransferRequest): UpdateTransferResult
    suspend fun deleteTransfer(transferId: Long): Boolean
    suspend fun deleteAllOperations(): OperationDeleteResult
    suspend fun deleteOperationsSelection(recordIds: List<Long>, transferIds: List<Long>): OperationDeleteResult
    suspend fun listTags(): List<String>
    suspend fun listCategories(recordType: String): List<String>
    suspend fun listWallets(): List<WalletOption>
    suspend fun walletBalances(): List<WalletOption>
}

interface SettingsEngine {
    suspend fun baseCurrency(): String
    suspend fun listWalletsForSettings(): List<WalletSettingsItem>
    suspend fun createWallet(request: CreateWalletRequest): WalletSettingsItem
    suspend fun deleteWallet(walletId: Long): WalletDeleteResult
    suspend fun runAudit(): List<AuditFinding>
}

interface EngineAdapter : RuntimeEngine, OperationsEngine, SettingsEngine
