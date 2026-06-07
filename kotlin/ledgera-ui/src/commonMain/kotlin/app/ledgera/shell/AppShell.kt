package app.ledgera.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.ledgera.operations.OperationsScreen
import app.ledgera.operations.OperationsViewModel
import app.ledgera.settings.SettingsScreen
import app.ledgera.settings.SettingsViewModel
import app.ledgera.ui.ToastHost

@Composable
fun AppShell(
    viewModel: AppShellViewModel,
    operationsViewModel: OperationsViewModel,
    settingsViewModel: SettingsViewModel,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.state.collectAsState()
    val operationsState by operationsViewModel.state.collectAsState()
    val settingsState by settingsViewModel.state.collectAsState()
    LaunchedEffect(Unit) {
        viewModel.refreshStatus()
    }

    ToastHost(
        message = when (state.selectedSection) {
            DesktopSection.Operations -> operationsState.notice
            DesktopSection.Settings -> settingsState.notice
            else -> null
        },
        modifier = modifier.fillMaxSize(),
        onDismiss = {
            when (state.selectedSection) {
                DesktopSection.Operations -> operationsViewModel.clearNotice()
                DesktopSection.Settings -> settingsViewModel.clearNotice()
                else -> Unit
            }
        },
    ) {
        Row(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
            NavigationRail(
                modifier = Modifier.fillMaxHeight().width(176.dp),
                header = {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Ledgera", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text("Beta.1", style = MaterialTheme.typography.labelMedium)
                    }
                },
            ) {
                state.sections.forEach { section ->
                    NavigationRailItem(
                        selected = state.selectedSection == section,
                        onClick = { viewModel.select(section) },
                        icon = { Text(section.label.take(1), fontWeight = FontWeight.Bold) },
                        label = { Text(section.label) },
                        alwaysShowLabel = true,
                    )
                }
            }

            Column(Modifier.fillMaxSize()) {
                if (state.error != null || state.engineMessage.isMeaningfulStatus()) {
                    StatusBanner(state.engineMessage, state.error)
                }
                Surface(Modifier.fillMaxSize()) {
                    when (state.selectedSection) {
                        DesktopSection.Operations -> OperationsScreen(operationsViewModel)
                        DesktopSection.Reports -> PendingSection(state.selectedSection)
                        DesktopSection.Analytics -> PendingSection(state.selectedSection)
                        DesktopSection.Dashboard -> PendingSection(state.selectedSection)
                        DesktopSection.Budget -> PendingSection(state.selectedSection)
                        DesktopSection.Debts -> PendingSection(state.selectedSection)
                        DesktopSection.Distribution -> PendingSection(state.selectedSection)
                        DesktopSection.Mandatory -> PendingSection(state.selectedSection)
                        DesktopSection.Settings -> SettingsScreen(settingsViewModel)
                    }
                }
            }
        }
    }
}

private fun String.isMeaningfulStatus(): Boolean =
    trim().isNotEmpty() && !equals("ready", ignoreCase = true)

@Composable
private fun StatusBanner(message: String, error: String?) {
    val containerColor = if (error == null) {
        MaterialTheme.colorScheme.surfaceVariant
    } else {
        MaterialTheme.colorScheme.errorContainer
    }
    val textColor = if (error == null) {
        MaterialTheme.colorScheme.onSurfaceVariant
    } else {
        MaterialTheme.colorScheme.onErrorContainer
    }
    Row(
        Modifier.fillMaxWidth().background(containerColor).padding(horizontal = 20.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(message, color = textColor, style = MaterialTheme.typography.bodyMedium)
        error?.let { Text(it, color = textColor, style = MaterialTheme.typography.bodyMedium) }
    }
}

@Composable
private fun PendingSection(section: DesktopSection) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.TopStart) {
        Column(
            Modifier.fillMaxWidth().heightIn(min = 160.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(section.label, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
            Text(
                "Beta.1 surface pending Rust UniFFI capability wiring.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
