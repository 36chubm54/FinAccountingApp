package app.ledgera

import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import app.ledgera.bridge.RustEngineAdapter
import app.ledgera.operations.OperationsScreen
import app.ledgera.operations.OperationsViewModel
import app.ledgera.theme.LedgeraTheme
import java.io.File

fun main(args: Array<String>) = application {
    val dbPath = args.asList().windowed(2, 1)
        .firstOrNull { it.first() == "--db-path" }
        ?.last()

    Window(onCloseRequest = ::exitApplication, title = "Ledgera Alpha.4") {
        LedgeraTheme {
            Surface {
                if (dbPath.isNullOrBlank()) {
                    Text("Start with --db-path <ledger.db>. Kotlin alpha.4 will not create a production DB implicitly.")
                } else if (!File(dbPath).isFile) {
                    Text("Database file not found: $dbPath. Create a test DB or pass a copy of an existing ledger.db.")
                } else {
                    OperationsScreen(OperationsViewModel(RustEngineAdapter(dbPath)))
                }
            }
        }
    }
}
