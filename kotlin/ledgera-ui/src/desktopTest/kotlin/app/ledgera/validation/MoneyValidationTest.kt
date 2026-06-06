package app.ledgera.validation

import kotlin.test.Test
import kotlin.test.assertEquals

class MoneyValidationTest {
    @Test
    fun validatePositiveAmountRejectsInvalidAndRoundedZeroValues() {
        assertEquals("Amount must be a positive number", MoneyValidation.validatePositiveAmount("ten"))
        assertEquals("Amount must be a positive number", MoneyValidation.validatePositiveAmount("-1"))
        assertEquals("Amount must be a positive number", MoneyValidation.validatePositiveAmount("0.004"))
    }

    @Test
    fun validatePositiveAmountAllowsValuesThatRoundToPositiveMoney() {
        assertEquals(null, MoneyValidation.validatePositiveAmount("0.005"))
        assertEquals(null, MoneyValidation.validatePositiveAmount(".005"))
        assertEquals(null, MoneyValidation.validatePositiveAmount("+.005"))
        assertEquals(null, MoneyValidation.validatePositiveAmount("1."))
        assertEquals(null, MoneyValidation.validatePositiveAmount("10.005"))
    }
}
