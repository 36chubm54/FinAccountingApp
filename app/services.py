from typing import Optional, Dict
from domain.currency import CurrencyService as DomainCurrencyService
from pathlib import Path
import json
import re


class CurrencyService:
    """Адаптер сервиса валют для приложения.

    По умолчанию использует локальные дефолтные курсы (совместимо с тестами).
    Если требуется — можно разрешить попытку получить актуальные курсы с
    https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut/
    установив `use_online=True` при создании. В этом случае курсы кэшируются
    в `project/currency_rates.json` и будут использованы при отсутствии сети.
    """

    CACHE_FILE = Path(__file__).resolve().parents[1] / "currency_rates.json"

    def __init__(
        self,
        rates: Optional[Dict[str, float]] = None,
        base: str = "KZT",
        use_online: bool = False,
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
        """Попытаться получить курсы с сайта НБРК и сохранить в кеш.

        Возвращает словарь rates или None при ошибке.
        """
        url = "https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut/"
        try:
            import requests
            from bs4 import BeautifulSoup
        except Exception:
            return self._load_cached()

        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            rates: Dict[str, float] = {}

            # 1) Try parsing table rows
            for tr in soup.find_all("tr"):
                cols = [
                    td.get_text(strip=True)
                    for td in tr.find_all(["td", "th"])
                    if td.get_text(strip=True)
                ]
                if not cols:
                    continue
                code = None
                value = None
                for i, col in enumerate(cols):
                    token = col.replace("\u00a0", "").strip()
                    if re.fullmatch(r"[A-Z]{3}", token):
                        code = token
                        # look for numeric value after code
                        for j in range(i + 1, len(cols)):
                            cand = cols[j].replace("\u00a0", "").replace(",", ".")
                            if re.match(r"^[0-9]+(\.[0-9]+)?$", cand):
                                try:
                                    value = float(cand)
                                    break
                                except Exception:
                                    continue
                        break
                if code and value is not None:
                    rates[code] = value

            # 2) Fallback: search whole text for patterns like 'USD 470'
            if not rates:
                text = soup.get_text(" ", strip=True)
                pattern = re.compile(
                    r"\b([A-Z]{3})\b[^0-9\n\r]{0,30}([0-9]+(?:[.,][0-9]+)?)"
                )
                for m in pattern.finditer(text):
                    code = m.group(1)
                    cand = m.group(2).replace("\u00a0", "").replace(",", ".")
                    try:
                        val = float(cand)
                    except Exception:
                        continue
                    rates.setdefault(code, val)

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
