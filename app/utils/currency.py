"""
Currency models and utilities for multi-currency support.
"""

from enum import Enum
from typing import Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class Currency(str, Enum):
    """Поддерживаемые валюты (ISO 4217)."""

    RUB = "RUB"  # Российский рубль
    USD = "USD"  # Доллар США
    EUR = "EUR"  # Евро
    KZT = "KZT"  # Казахстанский тенге
    BYN = "BYN"  # Белорусский рубль
    CNY = "CNY"  # Китайский юань
    TRY = "TRY"  # Турецкая лира
    AED = "AED"  # Дирхам ОАЭ
    GBP = "GBP"  # Британский фунт
    JPY = "JPY"  # Японская иена


# Символы валют
CURRENCY_SYMBOLS: Dict[Currency, str] = {
    Currency.RUB: "₽",
    Currency.USD: "$",
    Currency.EUR: "€",
    Currency.KZT: "₸",
    Currency.BYN: "Br",
    Currency.CNY: "¥",
    Currency.TRY: "₺",
    Currency.AED: "د.إ",
    Currency.GBP: "£",
    Currency.JPY: "¥",
}


# Курсы валют по умолчанию (к RUB)
# В продакшене следует использовать API ЦБ РФ или другой источник
DEFAULT_RATES: Dict[Currency, float] = {
    Currency.RUB: 1.0,
    Currency.USD: 92.5,
    Currency.EUR: 100.0,
    Currency.KZT: 0.20,
    Currency.BYN: 28.5,
    Currency.CNY: 12.8,
    Currency.TRY: 2.7,
    Currency.AED: 25.2,
    Currency.GBP: 117.0,
    Currency.JPY: 0.62,
}


class CurrencyService:
    """Сервис для работы с валютами."""

    def __init__(self, rates: Optional[Dict[Currency, float]] = None):
        """
        Инициализация сервиса валют.

        Args:
            rates: Словарь курсов валют (к RUB). Если не указан, используются дефолтные.
        """
        self._rates = rates or DEFAULT_RATES.copy()
        self._last_updated: Optional[datetime] = None

    def get_rate(self, currency: Currency) -> float:
        """
        Получить курс валюты к RUB.

        Args:
            currency: Валюта

        Returns:
            Курс валюты к RUB
        """
        return self._rates.get(currency, 1.0)

    def set_rate(self, currency: Currency, rate: float) -> None:
        """
        Установить курс валюты.

        Args:
            currency: Валюта
            rate: Курс к RUB
        """
        if rate <= 0:
            raise ValueError("Rate must be positive")
        self._rates[currency] = rate
        self._last_updated = datetime.now(timezone.utc)

    def convert(
        self,
        amount: float,
        from_currency: Currency,
        to_currency: Currency,
    ) -> float:
        """
        Конвертировать сумму из одной валюты в другую.

        Args:
            amount: Сумма
            from_currency: Исходная валюта
            to_currency: Целевая валюта

        Returns:
            Конвертированная сумма
        """
        if from_currency == to_currency:
            return round(amount, 2)

        # Конвертируем в RUB, затем в целевую валюту
        amount_in_rub = amount * self.get_rate(from_currency)
        result = amount_in_rub / self.get_rate(to_currency)

        return round(result, 2)

    def format_amount(self, amount: float, currency: Currency) -> str:
        """
        Форматировать сумму с символом валюты.

        Args:
            amount: Сумма
            currency: Валюта

        Returns:
            Форматированная строка
        """
        symbol = CURRENCY_SYMBOLS.get(currency, currency.value)
        return f"{amount:,.2f} {symbol}"

    def get_all_rates(self) -> Dict[str, float]:
        """
        Получить все курсы валют.

        Returns:
            Словарь курсов {currency_code: rate}
        """
        return {c.value: r for c, r in self._rates.items()}

    def get_last_updated(self) -> Optional[datetime]:
        """Получить время последнего обновления курсов."""
        return self._last_updated

    def is_supported(self, currency: str) -> bool:
        """
        Проверить поддержку валюты.

        Args:
            currency: Код валюты

        Returns:
            True если валюта поддерживается
        """
        try:
            Currency(currency)
            return True
        except ValueError:
            return False


# Глобальный экземпляр сервиса
currency_service = CurrencyService()


def get_currency_service() -> CurrencyService:
    """Dependency для получения CurrencyService."""
    return currency_service
