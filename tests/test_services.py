import pytest
from app.services import CurrencyService


class TestCurrencyServiceAdapter:
    def test_default_rates(self):
        service = CurrencyService()
        assert service.convert(100.0, "USD") == 50000.0  # 100 * 500
        assert service.convert(50.0, "EUR") == 29500.0  # 50 * 590
        assert service.convert(100.0, "RUB") == 650.0  # 100 * 6.5

    def test_custom_rates(self):
        service = CurrencyService(rates={"USD": 450.0, "EUR": 550.0})
        assert service.convert(100.0, "USD") == 45000.0
        assert service.convert(50.0, "EUR") == 27500.0

    def test_base_currency_conversion(self):
        service = CurrencyService()
        assert service.convert(100.0, "KZT") == 100.0

    def test_unsupported_currency_raises_valueerror(self):
        service = CurrencyService()
        with pytest.raises(ValueError, match="Unsupported currency: BTC"):
            service.convert(100.0, "BTC")

    def test_domain_service_keyerror_converted_to_valueerror(self):
        # Since the adapter catches KeyError from domain service and raises ValueError
        service = CurrencyService(
            rates={}
        )  # Empty rates, no currencies supported except base
        with pytest.raises(ValueError, match="Unsupported currency: USD"):
            service.convert(100.0, "USD")

    def test_get_rate(self):
        service = CurrencyService(rates={"USD": 510.0})
        assert service.get_rate("USD") == 510.0
        assert service.get_rate("KZT") == 1.0
