package app.ledgera.operations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import app.ledgera.model.OperationFilter
import app.ledgera.model.OperationRecord
import app.ledgera.model.WalletOption

@Composable
fun OperationsScreen(viewModel: OperationsViewModel, modifier: Modifier = Modifier) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Operations", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
        OperationFilters(
            selectedType = state.filter.recordType,
            onTypeSelected = { type -> viewModel.refresh(state.filter.copy(recordType = type)) },
        )
        CreateOperationForm(
            wallets = state.wallets,
            onSubmit = viewModel::create,
        )
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (state.loading) {
            CircularProgressIndicator()
        } else if (state.records.isEmpty()) {
            Text("No operations for the selected filter.")
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(state.records, key = { it.id }) { record ->
                    OperationRow(record)
                }
            }
        }
    }
}

@Composable
private fun OperationFilters(selectedType: String?, onTypeSelected: (String?) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        FilterChip(
            selected = selectedType == null,
            onClick = { onTypeSelected(null) },
            label = { Text("All") },
        )
        FilterChip(
            selected = selectedType == "income",
            onClick = { onTypeSelected("income") },
            label = { Text("Income") },
        )
        FilterChip(
            selected = selectedType == "expense",
            onClick = { onTypeSelected("expense") },
            label = { Text("Expense") },
        )
    }
}

@Composable
private fun CreateOperationForm(wallets: List<WalletOption>, onSubmit: (CreateOperationRequest) -> Unit) {
    var type by remember { mutableStateOf("income") }
    var date by remember { mutableStateOf("2026-01-01") }
    var amount by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var tags by remember { mutableStateOf("") }
    var walletId by remember { mutableStateOf(wallets.firstOrNull()?.id ?: 0L) }

    LaunchedEffect(wallets) {
        if (wallets.none { it.id == walletId }) {
            walletId = wallets.firstOrNull()?.id ?: 0L
        }
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Add operation", style = MaterialTheme.typography.titleMedium)
            if (wallets.isEmpty()) {
                Text(
                    "No active wallets found in the selected database. Create or copy a ledger DB with at least one wallet.",
                    color = MaterialTheme.colorScheme.error,
                )
            } else {
                Text("Wallet", style = MaterialTheme.typography.labelLarge)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    wallets.forEach { wallet ->
                        FilterChip(
                            selected = wallet.id == walletId,
                            onClick = { walletId = wallet.id },
                            label = { Text("${wallet.name} · ${wallet.currency}") },
                        )
                    }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(type == "income", { type = "income" }, label = { Text("Income") })
                FilterChip(type == "expense", { type = "expense" }, label = { Text("Expense") })
            }
            OutlinedTextField(date, { date = it }, label = { Text("Date YYYY-MM-DD") })
            OutlinedTextField(amount, { amount = it }, label = { Text("Amount") })
            OutlinedTextField(category, { category = it }, label = { Text("Category") })
            OutlinedTextField(description, { description = it }, label = { Text("Description") })
            OutlinedTextField(tags, { tags = it }, label = { Text("Tags, comma-separated") })
            Button(
                onClick = {
                    onSubmit(
                        CreateOperationRequest(
                            type = type,
                            date = date,
                            walletId = walletId,
                            amountOriginal = amount,
                            currency = "KZT",
                            rateAtOperation = "1",
                            amountBase = amount,
                            category = category,
                            description = description,
                            tags = tags.split(",", ";", "\n").map { it.trim() }.filter { it.isNotEmpty() },
                        )
                    )
                },
                enabled = walletId > 0,
            ) {
                Text("Add")
            }
        }
    }
}

@Composable
private fun OperationRow(record: OperationRecord) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(record.category, fontWeight = FontWeight.SemiBold)
                Text("${record.amountBase} ${record.currency}")
            }
            Spacer(Modifier.height(4.dp))
            Text("${record.date} · ${record.type} · wallet #${record.walletId}")
            if (record.description.isNotBlank()) {
                Text(record.description)
            }
            if (record.tags.isNotEmpty()) {
                Text(record.tags.joinToString(" ") { "#$it" }, color = MaterialTheme.colorScheme.secondary)
            }
        }
    }
}
