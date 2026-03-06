"""Базовый класс для платёжных шлюзов."""

import asyncio
import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .exceptions import (
    PaymentGatewayAPIError,
    PaymentGatewayConfigError,
    PaymentGatewayConnectionError,
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
)

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


class BasePaymentGateway(ABC):
    """Базовый класс для всех платёжных шлюзов.

    Attributes:
        api_key: API ключ для аутентификации.
        secret_key: Секретный ключ для подписи запросов.
        return_url: URL для возврата после оплаты.
        base_url: Базовый URL API платёжной системы.
        timeout: Таймаут запросов в секундах.
        max_retries: Максимальное количество попыток при ошибке.
        retry_delay: Базовая задержка между попытками (сек).
    """

    def __init__(
        self,
        api_key: Optional[str],
        secret_key: Optional[str],
        return_url: str,
        base_url: str,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        proxy: Optional[str] = None,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.return_url = return_url
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.proxy = proxy

    def generate_signature(
        self, params: Dict[str, Any], secret_key: Optional[str] = None
    ) -> str:
        """Генерация HMAC-SHA256 подписи.

        Args:
            params: Параметры для подписи.
            secret_key: Секретный ключ (по умолчанию используется self.secret_key).

        Returns:
            HEX-строка подписи.
        """
        key = secret_key if secret_key is not None else self.secret_key
        if not key:
            logger.debug(f"{self.__class__.__name__}: secret key not configured")
            return ""

        filtered_params = {
            k: v for k, v in params.items()
            if v is not None and v != ""
        }
        signature_str = "&".join(
            f"{key}={value}" for key, value in sorted(filtered_params.items())
        )
        return hmac.new(
            key.encode(),
            signature_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(
        self, params: Dict[str, Any], provided_signature: str
    ) -> bool:
        """Проверка HMAC подписи.

        Args:
            params: Параметры запроса.
            provided_signature: Предоставленная подпись.

        Returns:
            True если подпись валидна, False иначе.
        """
        if not self.secret_key:
            logger.warning(
                f"{self.__class__.__name__}: secret key not configured, "
                "skipping signature verification"
            )
            return True

        expected_signature = self.generate_signature(params)
        return hmac.compare_digest(expected_signature, provided_signature)

    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Выполнение асинхронного HTTP запроса с retry-логикой.

        Args:
            method: HTTP метод (GET, POST, etc.).
            url: URL запроса.
            headers: HTTP заголовки.
            json_data: JSON тело запроса.
            params: Query параметры.
            timeout: Таймаут запроса (переопределяет self.timeout).

        Returns:
            JSON ответ API.

        Raises:
            PaymentGatewayConfigError: Ошибка конфигурации.
            PaymentGatewayTimeoutError: Таймаут запроса.
            PaymentGatewayConnectionError: Ошибка соединения.
            PaymentGatewayAPIError: Ошибка API.
        """
        if not self.api_key:
            raise PaymentGatewayConfigError(
                f"{self.__class__.__name__}: API key not configured"
            )

        retry_count = 0
        last_exception: Optional[Exception] = None
        client_timeout = timeout or self.timeout

        while retry_count < self.max_retries:
            try:
                async with httpx.AsyncClient(
                    timeout=client_timeout,
                    proxy=self.proxy,
                ) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        json=json_data,
                        params=params,
                    )
                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"{self.__class__.__name__} HTTP {e.response.status_code}: {e}"
                )
                error_detail = self._parse_error_response(e)
                raise PaymentGatewayAPIError(
                    message=f"Payment gateway API error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_body=error_detail,
                ) from e

            except httpx.TimeoutException as e:
                retry_count += 1
                last_exception = e
                delay = self.retry_delay * (2 ** (retry_count - 1))
                logger.warning(
                    f"{self.__class__.__name__} timeout (attempt {retry_count}/{self.max_retries}, "
                    f"retry in {delay:.1f}s)"
                )
                if retry_count < self.max_retries:
                    await asyncio.sleep(delay)

            except httpx.RequestError as e:
                retry_count += 1
                last_exception = e
                delay = self.retry_delay * (2 ** (retry_count - 1))
                logger.warning(
                    f"{self.__class__.__name__} request error: {e} "
                    f"(attempt {retry_count}/{self.max_retries}, retry in {delay:.1f}s)"
                )
                if retry_count < self.max_retries:
                    await asyncio.sleep(delay)

        logger.error(
            f"{self.__class__.__name__} request failed after {self.max_retries} retries"
        )
        if isinstance(last_exception, httpx.TimeoutException):
            raise PaymentGatewayTimeoutError(
                f"{self.__class__.__name__}: request timeout after {self.max_retries} retries"
            ) from last_exception
        raise PaymentGatewayConnectionError(
            f"{self.__class__.__name__}: connection error after {self.max_retries} retries"
        ) from last_exception

    def _parse_error_response(
        self, error: httpx.HTTPStatusError
    ) -> Dict[str, Any]:
        """Парсинг ответа об ошибке от API.

        Args:
            error: Исключение HTTP ошибки.

        Returns:
            Словарь с деталями ошибки.
        """
        try:
            return error.response.json()
        except Exception:
            return {"raw_response": error.response.text or str(error)}

    def _prepare_payment_payload(
        self,
        amount: float,
        description: str,
        order_id: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Подготовка базового payload для платежа.

        Args:
            amount: Сумма платежа.
            description: Описание.
            order_id: ID заказа.
            extra_fields: Дополнительные поля.

        Returns:
            Словарь с параметрами платежа.

        Raises:
            PaymentGatewayConfigError: Шлюз не настроен.
            PaymentGatewayError: Некорректная сумма.
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError(
                f"{self.__class__.__name__}: gateway not configured"
            )

        if amount <= 0:
            raise PaymentGatewayError(
                "Invalid amount",
                details={"amount": amount, "reason": "Amount must be positive"},
            )

        payload = {
            "amount": amount,
            "currency": "RUB",
            "description": description[:250],
            "order_id": order_id,
            "return_url": self.return_url,
        }

        if extra_fields:
            payload.update(extra_fields)

        return payload

    def validate_config(self) -> bool:
        """Проверка конфигурации шлюза.

        Returns:
            True если конфигурация валидна.
        """
        if not self.api_key:
            logger.error(f"{self.__class__.__name__}: API key not configured")
            return False
        if not self.secret_key:
            logger.warning(f"{self.__class__.__name__}: secret key not configured")
        return True

    @abstractmethod
    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа.

        Args:
            amount: Сумма платежа.
            description: Описание платежа.
            order_id: ID заказа.

        Returns:
            Ответ от API платёжной системы.
        """
        pass

    @abstractmethod
    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook уведомления.

        Args:
            payload: Тело webhook.
            signature: Подпись webhook.

        Returns:
            Статус обработки.
        """
        pass
