class CurrencyService:
    def __init__(self, rates: dict[str, float], base: str = "KZT"):
        self._rates = rates
        self._base = base

    def convert(self, amount: float, currency: str) -> float:
        if currency == self._base:
            return amount
        return amount * self._rates[currency]
