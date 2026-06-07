package app.ledgera.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupProperties
import kotlinx.coroutines.delay

@Composable
fun ToastHost(
    message: String?,
    modifier: Modifier = Modifier,
    onDismiss: () -> Unit,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(modifier = modifier) {
        content()
        message?.takeIf { it.isNotBlank() }?.let { text ->
            var visible by remember(text) { mutableStateOf(false) }
            LaunchedEffect(text) {
                visible = true
                delay(3_500)
                visible = false
                delay(140)
                onDismiss()
            }
            Popup(
                alignment = Alignment.BottomCenter,
                properties = PopupProperties(focusable = false),
            ) {
                AnimatedVisibility(
                    visible = visible,
                    enter = fadeIn(animationSpec = tween(180)) +
                        slideInVertically(animationSpec = tween(180)) { height -> height / 2 },
                    exit = fadeOut(animationSpec = tween(140)) +
                        slideOutVertically(animationSpec = tween(140)) { height -> height / 2 },
                ) {
                    ToastNotification(
                        message = text,
                        modifier = Modifier.padding(24.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun ToastNotification(message: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.widthIn(max = 560.dp),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.inverseSurface,
        contentColor = MaterialTheme.colorScheme.inverseOnSurface,
        tonalElevation = 6.dp,
        shadowElevation = 6.dp,
    ) {
        Text(
            text = message,
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 12.dp),
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}
