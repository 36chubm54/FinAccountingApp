package app.ledgera.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.window.PopupProperties

@Composable
fun AutocompleteTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    suggestions: List<String>,
    modifier: Modifier = Modifier,
    menuWidth: Dp? = null,
    maxSuggestions: Int = 6,
) {
    var expanded by remember { mutableStateOf(false) }
    val filteredSuggestions = remember(value, suggestions) {
        filterSuggestions(value, suggestions, maxSuggestions)
    }
    Box(modifier = modifier) {
        OutlinedTextField(
            modifier = Modifier
                .fillMaxWidth()
                .onFocusChanged { state ->
                    expanded = state.isFocused && filteredSuggestions.isNotEmpty()
                }
                .onPreviewKeyEvent { event ->
                    if (event.type != KeyEventType.KeyDown) {
                        false
                    } else {
                        when (event.key) {
                            Key.Escape -> {
                                expanded = false
                                true
                            }
                            else -> false
                        }
                    }
                },
            value = value,
            onValueChange = {
                onValueChange(it.lineSafe())
                expanded = true
            },
            label = { Text(label) },
            singleLine = true,
        )
        SuggestionMenu(
            expanded = expanded && filteredSuggestions.isNotEmpty(),
            suggestions = filteredSuggestions,
            menuWidth = menuWidth,
            onDismiss = { expanded = false },
            onSuggestionSelected = { suggestion ->
                onValueChange(suggestion)
                expanded = false
            },
        )
    }
}

@Composable
fun TagAutocompleteField(
    value: String,
    onValueChange: (String) -> Unit,
    suggestions: List<String>,
    modifier: Modifier = Modifier,
    menuWidth: Dp? = null,
    maxSuggestions: Int = 6,
) {
    var expanded by remember { mutableStateOf(false) }
    val token = currentTagToken(value)
    val filteredSuggestions = remember(token, suggestions) {
        filterSuggestions(token, suggestions, maxSuggestions)
    }
    Box(modifier = modifier) {
        OutlinedTextField(
            modifier = Modifier
                .fillMaxWidth()
                .onFocusChanged { state ->
                    expanded = state.isFocused && filteredSuggestions.isNotEmpty()
                }
                .onPreviewKeyEvent { event ->
                    if (event.type != KeyEventType.KeyDown) {
                        false
                    } else {
                        when (event.key) {
                            Key.Escape -> {
                                expanded = false
                                true
                            }
                            else -> false
                        }
                    }
                },
            value = value,
            onValueChange = {
                onValueChange(it.lineSafe())
                expanded = true
            },
            label = { Text("Tags, comma-separated") },
            singleLine = true,
        )
        SuggestionMenu(
            expanded = expanded && filteredSuggestions.isNotEmpty(),
            suggestions = filteredSuggestions,
            menuWidth = menuWidth,
            onDismiss = { expanded = false },
            onSuggestionSelected = { suggestion ->
                onValueChange(replaceCurrentTagToken(value, suggestion))
                expanded = false
            },
        )
    }
}

@Composable
private fun SuggestionMenu(
    expanded: Boolean,
    suggestions: List<String>,
    menuWidth: Dp?,
    onDismiss: () -> Unit,
    onSuggestionSelected: (String) -> Unit,
) {
    DropdownMenu(
        expanded = expanded,
        onDismissRequest = onDismiss,
        modifier = if (menuWidth == null) Modifier else Modifier.width(menuWidth),
        properties = PopupProperties(focusable = false),
    ) {
        suggestions.forEach { suggestion ->
            DropdownMenuItem(
                text = { Text(suggestion) },
                onClick = { onSuggestionSelected(suggestion) },
            )
        }
    }
}

private fun filterSuggestions(
    value: String,
    suggestions: List<String>,
    maxSuggestions: Int,
): List<String> {
    val query = value.trim()
    return suggestions
        .asSequence()
        .map(String::trim)
        .filter(String::isNotEmpty)
        .distinctBy(String::lowercase)
        .filter { suggestion ->
            query.isEmpty() ||
                suggestion.contains(query, ignoreCase = true) &&
                !suggestion.equals(query, ignoreCase = true)
        }
        .take(maxSuggestions.coerceAtLeast(1))
        .toList()
}

private fun currentTagToken(value: String): String =
    value.substringAfterLast(',').trim()

private fun replaceCurrentTagToken(value: String, suggestion: String): String {
    val separatorIndex = value.lastIndexOf(',')
    return if (separatorIndex < 0) {
        suggestion
    } else {
        "${value.substring(0, separatorIndex).trimEnd()}, $suggestion"
    }
}

private fun String.lineSafe(): String = replace("\r", " ").replace("\n", " ")
