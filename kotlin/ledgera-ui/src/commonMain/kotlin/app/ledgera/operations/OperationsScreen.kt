package app.ledgera.operations

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.TextButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.ledgera.model.CreateOperationRequest
import app.ledgera.model.CreateTransferRequest
import app.ledgera.model.OperationDraft
import app.ledgera.model.OperationFilter
import app.ledgera.model.TransferDraft
import app.ledgera.model.WalletOption

@Composable
fun OperationsScreen(viewModel: OperationsViewModel, modifier: Modifier = Modifier) {
    val state by viewModel.state.collectAsState()
    var showCreateDialog by remember { mutableStateOf(false) }
    var showTransferDialog by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }
    var confirmTransferDelete by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        viewModel.refresh()
    }
    LaunchedEffect(showCreateDialog, state.notice) {
        if (showCreateDialog && state.notice == "Operation added") {
            showCreateDialog = false
        }
    }
    LaunchedEffect(showTransferDialog, state.notice) {
        if (showTransferDialog && state.notice?.startsWith("Transfer created") == true) {
            showTransferDialog = false
        }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Operations", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
        OperationFilters(
            filter = state.filter,
            wallets = state.wallets,
            categories = state.categories,
            onFilterChanged = { filter -> viewModel.refresh(filter) },
        )

        Row(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Column(
                modifier = Modifier
                    .widthIn(min = 360.dp, max = 460.dp)
                    .fillMaxHeight()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                AddOperationLauncher(
                    wallets = state.wallets,
                    onAddOperation = {
                        viewModel.clearFeedback()
                        showCreateDialog = true
                    },
                    onAddTransfer = {
                        viewModel.clearFeedback()
                        showTransferDialog = true
                    },
                )
            }

            Column(
                modifier = Modifier.weight(1f).fillMaxHeight(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                state.notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
                if (state.loading) {
                    CircularProgressIndicator()
                } else if (state.records.isEmpty()) {
                    Text("No operations for the selected filter.")
                } else {
                    val journalItems = operationJournalItems(state.records, state.selectedRecordId)
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(journalItems, key = { it.key }) { item ->
                            OperationRow(
                                item = item,
                                onClick = {
                                    if (item.transferId != null) {
                                        viewModel.selectTransfer(item.transferId)
                                    } else {
                                        item.selectableRecordId?.let(viewModel::select)
                                    }
                                },
                            )
                        }
                    }
                }
            }
        }
    }

    if (showCreateDialog) {
        CreateOperationDialog(
            wallets = state.wallets,
            baseCurrency = state.baseCurrency,
            engineError = state.error,
            submitting = state.loading,
            onSubmit = { request ->
                viewModel.create(request)
            },
            onCancel = { showCreateDialog = false },
        )
    }
    if (showTransferDialog) {
        CreateTransferDialog(
            wallets = state.wallets,
            baseCurrency = state.baseCurrency,
            engineError = state.error,
            submitting = state.loading,
            onSubmit = viewModel::createTransfer,
            onCancel = { showTransferDialog = false },
        )
    }
    state.editDraft?.let { draft ->
        EditOperationDialog(
            draft = draft,
            wallets = state.wallets,
            baseCurrency = state.baseCurrency,
            onDraftChanged = viewModel::updateDraft,
            onSave = viewModel::updateSelected,
            onCancel = {
                confirmDelete = false
                viewModel.clearSelection()
            },
            onDelete = { confirmDelete = true },
        )
    }
    state.transferDraft?.let { draft ->
        EditTransferDialog(
            draft = draft,
            wallets = state.wallets,
            baseCurrency = state.baseCurrency,
            engineError = state.error,
            submitting = state.loading,
            onDraftChanged = viewModel::updateTransferDraft,
            onSave = viewModel::updateSelectedTransfer,
            onCancel = {
                confirmTransferDelete = false
                viewModel.clearSelection()
            },
            onDelete = { confirmTransferDelete = true },
        )
    }
    if (confirmTransferDelete && state.transferDraft != null) {
        DeleteTransferConfirmDialog(
            onConfirm = {
                confirmTransferDelete = false
                viewModel.deleteSelectedTransfer()
            },
            onCancel = { confirmTransferDelete = false },
        )
    }
    if (confirmDelete && state.selectedRecordId != null) {
        DeleteConfirmDialog(
            onConfirm = {
                confirmDelete = false
                viewModel.deleteSelected()
            },
            onCancel = { confirmDelete = false },
        )
    }
}

@Composable
private fun AddOperationLauncher(
    wallets: List<WalletOption>,
    onAddOperation: () -> Unit,
    onAddTransfer: () -> Unit,
) {
    val walletCount = wallets.size
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Operations", style = MaterialTheme.typography.titleMedium)
            Text("$walletCount active wallet${if (walletCount == 1) "" else "s"} available.")
            wallets.forEach { wallet ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(wallet.name)
                    Text("${wallet.balance} ${wallet.currency}")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onAddOperation, enabled = walletCount > 0) {
                    Text("Add operation")
                }
                Button(onClick = onAddTransfer, enabled = walletCount >= 2) {
                    Text("Add transfer")
                }
            }
        }
    }
}

@Composable
private fun OperationFilters(
    filter: OperationFilter,
    wallets: List<WalletOption>,
    categories: List<String>,
    onFilterChanged: (OperationFilter) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = filter.recordType == null,
                onClick = { onFilterChanged(filter.copy(recordType = null)) },
                label = { Text("All") },
            )
            FilterChip(
                selected = filter.recordType == "income",
                onClick = { onFilterChanged(filter.copy(recordType = "income")) },
                label = { Text("Income") },
            )
            FilterChip(
                selected = filter.recordType == "expense",
                onClick = { onFilterChanged(filter.copy(recordType = "expense")) },
                label = { Text("Expense") },
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                modifier = Modifier.weight(1f),
                value = filter.startDate.orEmpty(),
                onValueChange = { onFilterChanged(filter.copy(startDate = it.ifBlank { null })) },
                label = { Text("From") },
                singleLine = true,
            )
            OutlinedTextField(
                modifier = Modifier.weight(1f),
                value = filter.endDate.orEmpty(),
                onValueChange = { onFilterChanged(filter.copy(endDate = it.ifBlank { null })) },
                label = { Text("To") },
                singleLine = true,
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            FilterChip(
                selected = filter.walletId == null,
                onClick = { onFilterChanged(filter.copy(walletId = null)) },
                label = { Text("All wallets") },
            )
            wallets.forEach { wallet ->
                FilterChip(
                    selected = filter.walletId == wallet.id,
                    onClick = { onFilterChanged(filter.copy(walletId = wallet.id)) },
                    label = { Text(wallet.name) },
                )
            }
        }
        if (categories.isNotEmpty()) {
            Text("Categories: ${categories.joinToString(", ")}", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun CreateTransferDialog(
    wallets: List<WalletOption>,
    baseCurrency: String,
    engineError: String?,
    submitting: Boolean,
    onSubmit: (CreateTransferRequest) -> Unit,
    onCancel: () -> Unit,
) {
    var fromWalletId by remember { mutableStateOf(wallets.firstOrNull()?.id ?: 0L) }
    var toWalletId by remember { mutableStateOf(wallets.drop(1).firstOrNull()?.id ?: 0L) }
    var date by remember { mutableStateOf("2026-01-01") }
    var amount by remember { mutableStateOf("") }
    var currency by remember { mutableStateOf(baseCurrency) }
    var commissionAmount by remember { mutableStateOf("0") }
    var commissionCurrency by remember { mutableStateOf(baseCurrency) }
    var description by remember { mutableStateOf("") }

    LaunchedEffect(wallets, baseCurrency) {
        if (wallets.none { it.id == fromWalletId }) {
            fromWalletId = wallets.firstOrNull()?.id ?: 0L
        }
        if (wallets.none { it.id == toWalletId } || toWalletId == fromWalletId) {
            toWalletId = wallets.firstOrNull { it.id != fromWalletId }?.id ?: 0L
        }
        if (currency.isBlank()) {
            currency = baseCurrency
        }
        if (commissionCurrency.isBlank()) {
            commissionCurrency = baseCurrency
        }
    }

    val validationError = OperationValidation.validateTransferFields(
        fromWalletId = fromWalletId,
        toWalletId = toWalletId,
        date = date,
        amount = amount,
        currency = currency,
        commissionAmount = commissionAmount,
        commissionCurrency = commissionCurrency,
        baseCurrency = baseCurrency,
    )

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Add transfer") },
        text = {
            Column(
                modifier = dialogFormModifier(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (wallets.size < 2) {
                    Text(
                        "At least two active wallets are required to create a transfer.",
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    Text("From wallet", style = MaterialTheme.typography.labelLarge)
                    WalletChips(wallets, fromWalletId) { wallet ->
                        fromWalletId = wallet.id
                        if (toWalletId == wallet.id) {
                            toWalletId = wallets.firstOrNull { it.id != wallet.id }?.id ?: 0L
                        }
                    }
                    Text("To wallet", style = MaterialTheme.typography.labelLarge)
                    WalletChips(wallets, toWalletId) { wallet ->
                        toWalletId = wallet.id
                    }
                }
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = date,
                    onValueChange = { date = it },
                    label = { Text("Date YYYY-MM-DD") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = amount,
                    onValueChange = { amount = it },
                    label = { Text("Amount") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = currency,
                    onValueChange = { currency = OperationValidation.normalizeCurrency(it) },
                    label = { Text("Currency") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = commissionAmount,
                    onValueChange = { commissionAmount = it },
                    label = { Text("Commission") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = commissionCurrency,
                    onValueChange = { commissionCurrency = OperationValidation.normalizeCurrency(it) },
                    label = { Text("Commission currency") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description") },
                    singleLine = true,
                )
                (validationError ?: engineError)?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onSubmit(
                        CreateTransferRequest(
                            fromWalletId = fromWalletId,
                            toWalletId = toWalletId,
                            date = date,
                            amount = amount,
                            currency = currency,
                            description = description,
                            commissionAmount = commissionAmount.ifBlank { "0" },
                            commissionCurrency = commissionCurrency.ifBlank { baseCurrency },
                        )
                    )
                },
                enabled = validationError == null && !submitting,
            ) {
                Text(if (submitting) "Creating..." else "Create")
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Cancel") }
        },
    )
}

@Composable
private fun WalletChips(
    wallets: List<WalletOption>,
    selectedWalletId: Long,
    onWalletChanged: (WalletOption) -> Unit,
) {
    Row(
        modifier = Modifier.width(DialogContentWidth).horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        wallets.forEach { wallet ->
            FilterChip(
                selected = wallet.id == selectedWalletId,
                onClick = { onWalletChanged(wallet) },
                label = { Text("${wallet.name} · ${wallet.currency}") },
            )
        }
    }
}

@Composable
private fun CreateOperationDialog(
    wallets: List<WalletOption>,
    baseCurrency: String,
    engineError: String?,
    submitting: Boolean,
    onSubmit: (CreateOperationRequest) -> Unit,
    onCancel: () -> Unit,
) {
    var type by remember { mutableStateOf("income") }
    var date by remember { mutableStateOf("2026-01-01") }
    var amount by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var tags by remember { mutableStateOf("") }
    var walletId by remember { mutableStateOf(wallets.firstOrNull()?.id ?: 0L) }
    var currency by remember { mutableStateOf(baseCurrency) }

    LaunchedEffect(wallets, baseCurrency) {
        if (wallets.none { it.id == walletId }) {
            walletId = wallets.firstOrNull()?.id ?: 0L
        }
        if (currency.isBlank()) {
            currency = baseCurrency
        }
    }

    val validationError = OperationValidation.validateFields(
        type = type,
        date = date,
        walletId = walletId,
        amountOriginal = amount,
        currency = currency,
        category = category,
        tagsText = tags,
        baseCurrency = baseCurrency,
    )

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Add operation") },
        text = {
            CreateOperationForm(
                wallets = wallets,
                type = type,
                date = date,
                amount = amount,
                category = category,
                description = description,
                tags = tags,
                walletId = walletId,
                currency = currency,
                validationError = validationError,
                engineError = engineError,
                onTypeChanged = { type = it },
                onDateChanged = { date = it },
                onAmountChanged = { amount = it },
                onCategoryChanged = { category = it },
                onDescriptionChanged = { description = it },
                onTagsChanged = { tags = it },
                onWalletChanged = { wallet ->
                    walletId = wallet.id
                    if (currency.isBlank()) {
                        currency = baseCurrency
                    }
                },
                onCurrencyChanged = { currency = OperationValidation.normalizeCurrency(it) },
            )
        },
        confirmButton = {
            Button(
                onClick = {
                    onSubmit(
                        CreateOperationRequest(
                            type = type,
                            date = date,
                            walletId = walletId,
                            amountOriginal = amount,
                            currency = currency,
                            rateAtOperation = "1",
                            amountBase = amount,
                            category = category,
                            description = description,
                            tags = OperationValidation.parseTags(tags),
                        )
                    )
                },
                enabled = validationError == null && !submitting,
            ) {
                Text(if (submitting) "Adding..." else "Add")
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Cancel") }
        },
    )
}

@Composable
private fun CreateOperationForm(
    wallets: List<WalletOption>,
    type: String,
    date: String,
    amount: String,
    category: String,
    description: String,
    tags: String,
    walletId: Long,
    currency: String,
    validationError: String?,
    engineError: String?,
    onTypeChanged: (String) -> Unit,
    onDateChanged: (String) -> Unit,
    onAmountChanged: (String) -> Unit,
    onCategoryChanged: (String) -> Unit,
    onDescriptionChanged: (String) -> Unit,
    onTagsChanged: (String) -> Unit,
    onWalletChanged: (WalletOption) -> Unit,
    onCurrencyChanged: (String) -> Unit,
) {
    Column(
        modifier = dialogFormModifier(),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (wallets.isEmpty()) {
            Text(
                "No active wallets found in the selected database. Create or copy a ledger DB with at least one wallet.",
                color = MaterialTheme.colorScheme.error,
            )
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(type == "income", { onTypeChanged("income") }, label = { Text("Income") })
                FilterChip(type == "expense", { onTypeChanged("expense") }, label = { Text("Expense") })
            }
            Text("Wallet", style = MaterialTheme.typography.labelLarge)
            Row(
                modifier = Modifier.width(DialogContentWidth).horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                wallets.forEach { wallet ->
                    FilterChip(
                        selected = wallet.id == walletId,
                        onClick = { onWalletChanged(wallet) },
                        label = { Text("${wallet.name} · ${wallet.currency}") },
                    )
                }
            }
        }
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = date,
            onValueChange = onDateChanged,
            label = { Text("Date YYYY-MM-DD") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = amount,
            onValueChange = onAmountChanged,
            label = { Text("Amount") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = currency,
            onValueChange = onCurrencyChanged,
            label = { Text("Currency") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = category,
            onValueChange = onCategoryChanged,
            label = { Text("Category") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = description,
            onValueChange = onDescriptionChanged,
            label = { Text("Description") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = tags,
            onValueChange = onTagsChanged,
            label = { Text("Tags, comma-separated") },
            singleLine = true,
        )
        (validationError ?: engineError)?.let {
            Text(it, color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun EditOperationDialog(
    draft: OperationDraft,
    wallets: List<WalletOption>,
    baseCurrency: String,
    onDraftChanged: (OperationDraft) -> Unit,
    onSave: () -> Unit,
    onCancel: () -> Unit,
    onDelete: () -> Unit,
) {
    val validationError = OperationValidation.validateFields(
        type = draft.type,
        date = draft.date,
        walletId = draft.walletId,
        amountOriginal = draft.amountOriginal,
        currency = draft.currency,
        category = draft.category,
        tagsText = draft.tagsText,
        baseCurrency = baseCurrency,
    )

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Edit operation") },
        text = {
            Column(
                modifier = dialogFormModifier(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                EditOperationFields(
                    draft = draft,
                    wallets = wallets,
                    onDraftChanged = onDraftChanged,
                )
                validationError?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }
            }
        },
        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onDelete) { Text("Delete") }
                Button(onClick = onSave, enabled = validationError == null) { Text("Save") }
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Cancel") }
        },
    )
}

@Composable
private fun EditOperationFields(
    draft: OperationDraft,
    wallets: List<WalletOption>,
    onDraftChanged: (OperationDraft) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(draft.type == "income", { onDraftChanged(draft.copy(type = "income")) }, label = { Text("Income") })
            FilterChip(draft.type == "expense", { onDraftChanged(draft.copy(type = "expense")) }, label = { Text("Expense") })
        }
        Row(
            modifier = Modifier.width(DialogContentWidth).horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            wallets.forEach { wallet ->
                FilterChip(
                    selected = wallet.id == draft.walletId,
                    onClick = {
                        onDraftChanged(draft.copy(walletId = wallet.id))
                    },
                    label = { Text("${wallet.name} · ${wallet.currency}") },
                )
            }
        }
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = draft.date,
            onValueChange = { onDraftChanged(draft.copy(date = it)) },
            label = { Text("Date YYYY-MM-DD") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = draft.amountOriginal,
            onValueChange = { onDraftChanged(draft.copy(amountOriginal = it)) },
            label = { Text("Amount") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = draft.currency,
            onValueChange = { onDraftChanged(draft.copy(currency = OperationValidation.normalizeCurrency(it))) },
            label = { Text("Currency") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = draft.category,
            onValueChange = { onDraftChanged(draft.copy(category = it)) },
            label = { Text("Category") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = draft.description,
            onValueChange = { onDraftChanged(draft.copy(description = it)) },
            label = { Text("Description") },
            singleLine = true,
        )
        OutlinedTextField(
            modifier = dialogFieldModifier(),
            value = draft.tagsText,
            onValueChange = { onDraftChanged(draft.copy(tagsText = it)) },
            label = { Text("Tags, comma-separated") },
            singleLine = true,
        )
    }
}

@Composable
private fun EditTransferDialog(
    draft: TransferDraft,
    wallets: List<WalletOption>,
    baseCurrency: String,
    engineError: String?,
    submitting: Boolean,
    onDraftChanged: (TransferDraft) -> Unit,
    onSave: () -> Unit,
    onCancel: () -> Unit,
    onDelete: () -> Unit,
) {
    val validationError = OperationValidation.validateTransferFields(
        fromWalletId = draft.fromWalletId,
        toWalletId = draft.toWalletId,
        date = draft.date,
        amount = draft.amount,
        currency = draft.currency,
        commissionAmount = "0",
        commissionCurrency = baseCurrency,
        baseCurrency = baseCurrency,
    )

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Edit transfer #${draft.id}") },
        text = {
            Column(
                modifier = dialogFormModifier(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("From wallet", style = MaterialTheme.typography.labelLarge)
                WalletChips(wallets, draft.fromWalletId) { wallet ->
                    val nextToWallet = if (draft.toWalletId == wallet.id) {
                        wallets.firstOrNull { it.id != wallet.id }?.id ?: 0L
                    } else {
                        draft.toWalletId
                    }
                    onDraftChanged(draft.copy(fromWalletId = wallet.id, toWalletId = nextToWallet))
                }
                Text("To wallet", style = MaterialTheme.typography.labelLarge)
                WalletChips(wallets, draft.toWalletId) { wallet ->
                    onDraftChanged(draft.copy(toWalletId = wallet.id))
                }
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = draft.date,
                    onValueChange = { onDraftChanged(draft.copy(date = it)) },
                    label = { Text("Date YYYY-MM-DD") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = draft.amount,
                    onValueChange = { onDraftChanged(draft.copy(amount = it)) },
                    label = { Text("Amount") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = draft.currency,
                    onValueChange = {
                        onDraftChanged(draft.copy(currency = OperationValidation.normalizeCurrency(it)))
                    },
                    label = { Text("Currency") },
                    singleLine = true,
                )
                OutlinedTextField(
                    modifier = dialogFieldModifier(),
                    value = draft.description,
                    onValueChange = { onDraftChanged(draft.copy(description = it)) },
                    label = { Text("Description") },
                    singleLine = true,
                )
                Text(
                    "Transfer commission is edited as a standalone operation and deleted with the transfer.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                (validationError ?: engineError)?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }
            }
        },
        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onDelete, enabled = !submitting) { Text("Delete") }
                Button(onClick = onSave, enabled = validationError == null && !submitting) {
                    Text(if (submitting) "Saving..." else "Save")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Cancel") }
        },
    )
}

private val DialogContentWidth = 360.dp

private fun dialogFieldModifier(): Modifier = Modifier.fillMaxWidth()

@Composable
private fun dialogFormModifier(): Modifier =
    Modifier
        .width(DialogContentWidth)
        .heightIn(max = 560.dp)
        .verticalScroll(rememberScrollState())

@Composable
private fun DeleteConfirmDialog(onConfirm: () -> Unit, onCancel: () -> Unit) {
    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Delete operation") },
        text = { Text("Delete selected standalone operation?") },
        confirmButton = {
            Button(onClick = onConfirm) { Text("Delete") }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Cancel") }
        },
    )
}

@Composable
private fun DeleteTransferConfirmDialog(onConfirm: () -> Unit, onCancel: () -> Unit) {
    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Delete transfer") },
        text = { Text("Delete selected transfer and linked operation rows?") },
        confirmButton = {
            Button(onClick = onConfirm) { Text("Delete") }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text("Cancel") }
        },
    )
}

@Composable
private fun OperationRow(item: OperationJournalItem, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    item.title,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(item.amount)
            }
            Spacer(Modifier.height(4.dp))
            Text(item.meta)
            if (item.transferId != null) {
                Text(
                    "Transfer-linked",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (item.description.isNotBlank()) {
                Text(item.description)
            }
            if (item.tags.isNotEmpty()) {
                Text(item.tags.joinToString(" ") { "#$it" }, color = MaterialTheme.colorScheme.secondary)
            }
        }
    }
}
