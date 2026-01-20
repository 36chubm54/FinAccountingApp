from typing import Optional, Dict
from domain.currency import CurrencyService as DomainCurrencyService
from pathlib import Path
import json


class CurrencyService:
    """Адаптер сервиса валют для приложения.

    По умолчанию использует локальные дефолтные курсы (совместимо с тестами).
    Если требуется — можно разрешить попытку получить актуальные курсы с
    https://www.nationalbank.kz/rss/rates_all.xml
    установив `use_online=True` при создании. В этом случае курсы кэшируются
    в `project/currency_rates.json` и будут использованы при отсутствии сети.
    """

    CACHE_FILE = Path(__file__).resolve().parents[1] / "currency_rates.json"

    def __init__(
        self,
        rates: Optional[Dict[str, float]] = None,
        base: str = "KZT",
        use_online: bool = False,  # connect to online source if no rates provided
    ):
        # If explicit rates provided, use them.
        if rates is not None:
            self._service = DomainCurrencyService(rates=rates, base=base)
            return

        # If online fetching requested, try to fetch and cache; else fall back to defaults.
        if use_online:
            parsed = self._fetch_and_cache_rates()
            if parsed:
                self._service = DomainCurrencyService(rates=parsed, base=base)
                return

        # Default static rates (keeps existing test expectations)
        defaults = {"USD": 500.0, "EUR": 590.0, "RUB": 6.5}
        self._service = DomainCurrencyService(rates=defaults, base=base)

    def convert(self, amount: float, currency: str) -> float:
        try:
            return self._service.convert(amount, currency)
        except KeyError:
            raise ValueError(f"Unsupported currency: {currency}")

    def _fetch_and_cache_rates(self) -> Optional[Dict[str, float]]:
        """Попытаться получить курсы с RSS-фида НБРК и сохранить в кеш.

        Возвращает словарь rates или None при ошибке.
        """
        url = "https://www.nationalbank.kz/rss/rates_all.xml"
        try:
            import requests
            from bs4 import BeautifulSoup
        except Exception:
            return self._load_cached()

        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")

            rates: Dict[str, float] = {}

            # Parse RSS items
            for item in soup.find_all("item"):
                title = item.find("title")
                description = item.find("description")
                if title and description:
                    code = title.get_text(strip=True)
                    rate_text = description.get_text(strip=True)
                    try:
                        rate = float(rate_text.replace(",", "."))
                        rates[code] = rate
                    except ValueError:
                        continue

            if rates:
                self._save_cache(rates)
                return rates
        except Exception:
            return self._load_cached()

        return self._load_cached()

    def _load_cached(self) -> Optional[Dict[str, float]]:
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Expect mapping code->rate
                    return {k: float(v) for k, v in data.items()}
        except Exception:
            return None
        return None

    def _save_cache(self, rates: Dict[str, float]) -> None:
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(rates, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
