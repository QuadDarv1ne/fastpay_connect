"""
Tests for multi-currency support.
"""

import pytest
from datetime import datetime, timezone

from app.utils.currency import (
    Currency,
    CurrencyService,
    CURRENCY_SYMBOLS,
    DEFAULT_RATES,
    currency_service,
    get_currency_service,
)


class TestCurrencyEnum:
    """Тесты Enum валют."""

    def test_currency_values(self):
        """Проверка значений валют."""
        assert Currency.RUB.value == "RUB"
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.KZT.value == "KZT"
        assert Currency.BYN.value == "BYN"
        assert Currency.CNY.value == "CNY"
        assert Currency.TRY.value == "TRY"
        assert Currency.AED.value == "AED"
        assert Currency.GBP.value == "GBP"
        assert Currency.JPY.value == "JPY"

    def test_currency_count(self):
        """Проверка количества валют."""
        assert len(Currency) == 10


class TestCurrencySymbols:
    """Тесты символов валют."""

    def test_rub_symbol(self):
        """Проверка символа рубля."""
        assert CURRENCY_SYMBOLS[Currency.RUB] == "₽"

    def test_usd_symbol(self):
        """Проверка символа доллара."""
        assert CURRENCY_SYMBOLS[Currency.USD] == "$"

    def test_eur_symbol(self):
        """Проверка символа евро."""
        assert CURRENCY_SYMBOLS[Currency.EUR] == "€"

    def test_all_currencies_have_symbols(self):
        """Проверка наличия символов для всех валют."""
        for currency in Currency:
            assert currency in CURRENCY_SYMBOLS


class TestDefaultRates:
    """Тесты курсов валют по умолчанию."""

    def test_rub_rate_is_one(self):
        """Проверка курса RUB к самому себе."""
        assert DEFAULT_RATES[Currency.RUB] == 1.0

    def test_usd_rate(self):
        """Проверка курса USD."""
        assert DEFAULT_RATES[Currency.USD] == 92.5

    def test_eur_rate(self):
        """Проверка курса EUR."""
        assert DEFAULT_RATES[Currency.EUR] == 100.0

    def test_all_currencies_have_rates(self):
        """Проверка наличия курсов для всех валют."""
        for currency in Currency:
            assert currency in DEFAULT_RATES


class TestCurrencyService:
    """Тесты CurrencyService."""

    def test_init_with_default_rates(self):
        """Проверка инициализации с курсами по умолчанию."""
        service = CurrencyService()
        assert service.get_rate(Currency.RUB) == 1.0
        assert service.get_rate(Currency.USD) == 92.5

    def test_init_with_custom_rates(self):
        """Проверка инициализации с кастомными курсами."""
        custom_rates = {Currency.USD: 100.0}
        service = CurrencyService(rates=custom_rates)
        assert service.get_rate(Currency.USD) == 100.0

    def test_set_rate(self):
        """Проверка установки курса."""
        service = CurrencyService()
        service.set_rate(Currency.USD, 95.0)
        assert service.get_rate(Currency.USD) == 95.0

    def test_set_rate_invalid(self):
        """Проверка установки некорректного курса."""
        service = CurrencyService()
        with pytest.raises(ValueError, match="Rate must be positive"):
            service.set_rate(Currency.USD, -1.0)

    def test_convert_same_currency(self):
        """Проверка конвертации в ту же валюту."""
        service = CurrencyService()
        result = service.convert(100.0, Currency.RUB, Currency.RUB)
        assert result == 100.0

    def test_convert_rub_to_usd(self):
        """Проверка конвертации RUB в USD."""
        service = CurrencyService()
        # 1000 RUB / 92.5 = 10.81 USD
        result = service.convert(1000.0, Currency.RUB, Currency.USD)
        assert result == 10.81

    def test_convert_usd_to_rub(self):
        """Проверка конвертации USD в RUB."""
        service = CurrencyService()
        # 10 USD * 92.5 = 925.0 RUB
        result = service.convert(10.0, Currency.USD, Currency.RUB)
        assert result == 925.0

    def test_convert_eur_to_usd(self):
        """Проверка конвертации EUR в USD через RUB."""
        service = CurrencyService()
        # 10 EUR * 100.0 (EUR->RUB) / 92.5 (USD->RUB) = 10.81 USD
        result = service.convert(10.0, Currency.EUR, Currency.USD)
        assert result == 10.81

    def test_convert_rounding(self):
        """Проверка округления результата."""
        service = CurrencyService()
        result = service.convert(1.0, Currency.RUB, Currency.JPY)
        # Должно быть округлено до 2 знаков
        assert result == round(result, 2)

    def test_format_amount(self):
        """Проверка форматирования суммы."""
        service = CurrencyService()
        formatted = service.format_amount(1000.50, Currency.RUB)
        assert formatted == "1,000.50 ₽"

    def test_format_amount_usd(self):
        """Проверка форматирования суммы USD."""
        service = CurrencyService()
        formatted = service.format_amount(500.0, Currency.USD)
        assert formatted == "500.00 $"

    def test_get_all_rates(self):
        """Проверка получения всех курсов."""
        service = CurrencyService()
        rates = service.get_all_rates()

        assert isinstance(rates, dict)
        assert "RUB" in rates
        assert "USD" in rates
        assert "EUR" in rates
        assert rates["RUB"] == 1.0

    def test_get_last_updated(self):
        """Проверка времени последнего обновления."""
        service = CurrencyService()
        assert service.get_last_updated() is None

        service.set_rate(Currency.USD, 95.0)
        assert isinstance(service.get_last_updated(), datetime)

    def test_is_supported(self):
        """Проверка проверки поддержки валюты."""
        service = CurrencyService()

        assert service.is_supported("RUB") is True
        assert service.is_supported("USD") is True
        assert service.is_supported("INVALID") is False
        assert service.is_supported("XXX") is False


class TestCurrencyServiceDependency:
    """Тесты dependency injection."""

    def test_get_currency_service(self):
        """Проверка получения сервиса через dependency."""
        service = get_currency_service()
        assert isinstance(service, CurrencyService)
        assert service is currency_service  # Должен возвращать глобальный экземпляр


class TestCurrencyConversionEdgeCases:
    """Тесты граничных случаев конвертации."""

    def test_convert_zero_amount(self):
        """Проверка конвертации нулевой суммы."""
        service = CurrencyService()
        result = service.convert(0.0, Currency.RUB, Currency.USD)
        assert result == 0.0

    def test_convert_very_small_amount(self):
        """Проверка конвертации очень маленькой суммы."""
        service = CurrencyService()
        result = service.convert(0.01, Currency.RUB, Currency.USD)
        assert result >= 0.0
        assert result <= 0.01

    def test_convert_very_large_amount(self):
        """Проверка конвертации очень большой суммы."""
        service = CurrencyService()
        result = service.convert(1000000.0, Currency.USD, Currency.RUB)
        assert result == 92500000.0

    def test_convert_precision(self):
        """Проверка точности конвертации."""
        service = CurrencyService()
        # Конвертация должна сохранять 2 знака после запятой
        result = service.convert(100.00, Currency.RUB, Currency.USD)
        assert result == round(result, 2)


class TestCurrencyChainConversion:
    """Тесты цепочки конвертаций."""

    def test_round_trip_conversion(self):
        """Проверка конвертации туда и обратно."""
        service = CurrencyService()
        original_amount = 1000.0

        # RUB -> USD -> RUB
        usd = service.convert(original_amount, Currency.RUB, Currency.USD)
        back_to_rub = service.convert(usd, Currency.USD, Currency.RUB)

        # Из-за округления может быть небольшая разница
        assert abs(back_to_rub - original_amount) < 1.0

    def test_multi_step_conversion(self):
        """Проверка многоступенчатой конвертации."""
        service = CurrencyService()

        # EUR -> GBP -> JPY
        eur_amount = 100.0
        gbp = service.convert(eur_amount, Currency.EUR, Currency.GBP)
        jpy = service.convert(gbp, Currency.GBP, Currency.JPY)

        # Прямая конвертация EUR -> JPY
        direct_jpy = service.convert(eur_amount, Currency.EUR, Currency.JPY)

        # Результаты должны быть близки (с учётом округления)
        assert abs(jpy - direct_jpy) < 1.0
