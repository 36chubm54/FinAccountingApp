package app.ledgera.debts

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.ledgera.model.DebtDraft
import app.ledgera.model.DebtItem
import app.ledgera.model.DebtPaymentItem
import app.ledgera.model.WalletOption

@Composable
fun DebtsScreen(viewModel: DebtsViewModel, modifier: Modifier = Modifier) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    Box(modifier = modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Debts", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            Column(
                Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                DebtsListCard(
                    debts = state.debts,
                    selectedDebtId = state.selectedDebtId,
                    loading = state.loading,
                    onSelectDebt = viewModel::selectDebt,
                    modifier = Modifier.weight(0.58f),
                )
                DebtHistoryCard(
                    selectedDebt = state.debts.firstOrNull { it.id == state.selectedDebtId },
                    history = state.selectedHistory,
                    modifier = Modifier.weight(0.42f),
                )
            }
        }

        Column(
            modifier = Modifier.align(Alignment.BottomEnd).padding(32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            FloatingActionButton(
                onClick = { viewModel.openCreateDialog("loan") },
                containerColor = MaterialTheme.colorScheme.secondary,
                contentColor = MaterialTheme.colorScheme.onSecondary,
            ) {
                Text("Loan", fontWeight = FontWeight.Bold)
            }
            FloatingActionButton(
                onClick = { viewModel.openCreateDialog("debt") },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
            ) {
                Text("Debt", fontWeight = FontWeight.Bold)
            }
        }

        state.createDraft?.let { draft ->
            CreateDebtDialog(
                draft = draft,
                wallets = state.wallets,
                baseCurrency = state.baseCurrency,
                engineError = state.error,
                submitting = state.createInProgress,
                onDraftChange = viewModel::updateDraft,
                onSubmit = viewModel::createDebt,
                onCancel = viewModel::closeCreateDialog,
            )
        }
    }
}

@Composable
private fun DebtsListCard(
    debts: List<DebtItem>,
    selectedDebtId: Long?,
    loading: Boolean,
    onSelectDebt: (Long) -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Open and closed debts", style = MaterialTheme.typography.titleMedium)
            if (loading && debts.isEmpty()) {
                CircularProgressIndicator()
            } else if (debts.isEmpty()) {
                Text("No debts or loans found in the selected database.")
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(debts, key = { it.id }) { debt ->
                        DebtRow(
                            debt = debt,
                            selected = debt.id == selectedDebtId,
                            onClick = { onSelectDebt(debt.id) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DebtRow(debt: DebtItem, selected: Boolean, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) {
                MaterialTheme.colorScheme.secondaryContainer
            } else {
                MaterialTheme.colorScheme.surface
            },
        ),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(debt.contactName, fontWeight = FontWeight.SemiBold)
                Text("${debt.remainingAmount} / ${debt.totalAmount} ${debt.currency}")
            }
            Text("${debt.kindLabel()} · ${debt.status} · created ${debt.createdAt}")
            debt.closedAt?.let {
                Text("closed $it", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun DebtHistoryCard(
    selectedDebt: DebtItem?,
    history: List<DebtPaymentItem>,
    modifier: Modifier = Modifier,
) {
    Card(modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("History", style = MaterialTheme.typography.titleMedium)
            if (selectedDebt == null) {
                Text("Select a debt or loan to view history.")
            } else if (history.isEmpty()) {
                Text("No payments registered for ${selectedDebt.contactName}.")
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(history, key = { it.id }) { payment ->
                        PaymentRow(payment)
                    }
                }
            }
        }
    }
}

@Composable
private fun PaymentRow(payment: DebtPaymentItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(payment.operationType)
                Text(
                    payment.paymentDate + if (payment.isWriteOff) " · write-off" else "",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(payment.principalPaid)
        }
    }
}

@Composable
private fun CreateDebtDialog(
    draft: DebtDraft,
    wallets: List<WalletOption>,
    baseCurrency: String,
    engineError: String?,
    submitting: Boolean,
    onDraftChange: (DebtDraft) -> Unit,
    onSubmit: () -> Unit,
    onCancel: () -> Unit,
) {
    val validationError = DebtsValidation.validateCreateDraft(draft, baseCurrency)
    AlertDialog(
        onDismissRequest = { if (!submitting) onCancel() },
        title = { Text(if (draft.kind == "loan") "Add loan" else "Add debt") },
        text = {
            Column(
                Modifier.widthIn(min = 420.dp, max = 520.dp)
                    .heightIn(max = 640.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text("Wallet", fontWeight = FontWeight.SemiBold)
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    wallets.forEach { wallet ->
                        val selected = wallet.id == draft.walletId
                        if (selected) {
                            Button(onClick = { onDraftChange(draft.copy(walletId = wallet.id)) }) {
                                Text("${wallet.name} · ${wallet.currency}")
                            }
                        } else {
                            OutlinedButton(onClick = { onDraftChange(draft.copy(walletId = wallet.id)) }) {
                                Text("${wallet.name} · ${wallet.currency}")
                            }
                        }
                    }
                }
                KindSelector(draft, onDraftChange)
                OutlinedTextField(
                    value = draft.contactName,
                    onValueChange = { onDraftChange(draft.copy(contactName = it.lineSafe())) },
                    label = { Text("Contact") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = draft.createdAt,
                    onValueChange = { onDraftChange(draft.copy(createdAt = it.lineSafe())) },
                    label = { Text("Date YYYY-MM-DD") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = draft.amount,
                    onValueChange = { onDraftChange(draft.copy(amount = it.lineSafe())) },
                    label = { Text("Amount") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = draft.currency,
                    onValueChange = { onDraftChange(draft.copy(currency = it.lineSafe().uppercase())) },
                    label = { Text("Currency") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = draft.description,
                    onValueChange = { onDraftChange(draft.copy(description = it.lineSafe())) },
                    label = { Text("Description") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                validationError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                engineError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = {
            Button(onClick = onSubmit, enabled = !submitting && validationError == null) {
                Text(if (submitting) "Saving..." else "Create")
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel, enabled = !submitting) {
                Text("Cancel")
            }
        },
    )
}

@Composable
private fun KindSelector(draft: DebtDraft, onDraftChange: (DebtDraft) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        if (draft.kind == "debt") {
            Button(onClick = { onDraftChange(draft.copy(kind = "debt")) }) { Text("Debt") }
        } else {
            OutlinedButton(onClick = { onDraftChange(draft.copy(kind = "debt")) }) { Text("Debt") }
        }
        if (draft.kind == "loan") {
            Button(onClick = { onDraftChange(draft.copy(kind = "loan")) }) { Text("Loan") }
        } else {
            OutlinedButton(onClick = { onDraftChange(draft.copy(kind = "loan")) }) { Text("Loan") }
        }
    }
}

private fun DebtItem.kindLabel(): String =
    if (kind == "loan") "loan" else "debt"

private fun String.lineSafe(): String =
    lineSequence().firstOrNull().orEmpty()
