package app.ledgera

import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.WindowPlacement
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import app.ledgera.bridge.RustEngineAdapter
import app.ledgera.operations.OperationsViewModel
import app.ledgera.settings.SettingsViewModel
import app.ledgera.shell.AppShell
import app.ledgera.shell.AppShellViewModel
import app.ledgera.theme.LedgeraTheme
import java.awt.Window as AwtWindow
import java.awt.event.ComponentEvent
import java.io.File
import javax.swing.SwingUtilities
import kotlinx.coroutines.delay

fun main(args: Array<String>) {
    val singleInstance = SingleInstanceSupport.acquire()
    if (singleInstance == null) {
        SingleInstanceSupport.requestActivation()
        return
    }

    singleInstance.use {
        runApplication(args)
    }
}

private fun runApplication(args: Array<String>) = application {
    val dbPath = args.asList().windowed(2, 1)
        .firstOrNull { it.first() == "--db-path" }
        ?.last()
    val windowState = rememberWindowState(placement = WindowPlacement.Maximized)

    Window(onCloseRequest = ::exitApplication, state = windowState, title = "Ledgera Beta.1") {
        RefreshDpiAfterStartup(window)
        LedgeraTheme {
            Surface {
                if (dbPath.isNullOrBlank()) {
                    Text("Start with --db-path <ledger.db>. Kotlin beta.1 will not create a production DB implicitly.")
                } else if (!File(dbPath).isFile) {
                    Text("Database file not found: $dbPath. Create a test DB or pass a copy of an existing ledger.db.")
                } else {
                    val engine = RustEngineAdapter(dbPath)
                    AppShell(
                        viewModel = AppShellViewModel(engine),
                        operationsViewModel = OperationsViewModel(engine),
                        settingsViewModel = SettingsViewModel(engine),
                    )
                }
            }
        }
    }
}

@Composable
private fun RefreshDpiAfterStartup(window: AwtWindow) {
    LaunchedEffect(window) {
        repeat(2) {
            delay(50)
            SwingUtilities.invokeLater {
                window.dispatchEvent(ComponentEvent(window, ComponentEvent.COMPONENT_RESIZED))
                window.invalidate()
                window.validate()
                window.repaint()
            }
        }
    }
}
