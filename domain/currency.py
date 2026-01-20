class CurrencyService:
    def __init__(self, rates: dict[str, float], base: str = "KZT"):
        self._rates = rates
        self._base = base

    def convert(self, amount: float, currency: str) -> float:
        if currency == self._base:
            return amount
        return amount * self._rates[currency]


# Пример использования:
# currency_service = CurrencyService("KZT", {"EUR": 590, "USD": 500})
# amount_in_usd = currency_service.convert(10000, "KZT")
# print(f"10000 USD в KZT: {amount_in_usd}")
