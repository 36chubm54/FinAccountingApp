class CurrencyService:
    def __init__(self, rates: dict[str, float], base: str = "KZT"):
        self._rates = rates
        self._base = base

    @property
    def base_currency(self) -> str:
        return self._base

    def get_all_rates(self) -> dict[str, float]:
        return dict(self._rates)

    def get_rate(self, currency: str) -> float:
        if currency == self._base:
            return 1.0
        return self._rates[currency]

    def convert(self, amount: float, currency: str) -> float:
        """Convert amount to base currency.

        Raises KeyError if the currency is not present in the rates map.
        """
        return amount * self.get_rate(currency)
