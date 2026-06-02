package app.ledgera.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF285C52),
    secondary = Color(0xFF9C6A2F),
    background = Color(0xFFF6F1E8),
    surface = Color(0xFFFFFBF4),
    error = Color(0xFFB3261E),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF8DD8C8),
    secondary = Color(0xFFE8B776),
    background = Color(0xFF171A18),
    surface = Color(0xFF202620),
    error = Color(0xFFFFB4AB),
)

@Composable
fun LedgeraTheme(dark: Boolean = false, content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (dark) DarkColors else LightColors,
        content = content,
    )
}
