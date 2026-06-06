package app.ledgera.validation

import kotlin.test.Test
import kotlin.test.assertEquals

class TagValidationTest {
    @Test
    fun validateTagTextRejectsNumericOnlyTags() {
        assertEquals(
            "Invalid tag: tags must not contain numbers only (\"123\")",
            TagValidation.validateTagText("#123, food"),
        )
    }

    @Test
    fun parseTagTextMatchesBackendNormalization() {
        assertEquals(
            listOf("food", "дом", "work"),
            TagValidation.parseTagText("#Food, дом!, Work, food, fourth"),
        )
    }

    @Test
    fun parseTagTextDropsUnsupportedCharactersLikeBackend() {
        assertEquals(
            listOf("tag", "abc123"),
            TagValidation.parseTagText("t@a#g, ё, abc-123"),
        )
    }
}
