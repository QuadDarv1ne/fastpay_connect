"""Базовый класс для платёжных шлюзов."""

import asyncio
import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from .exceptions import (
    PaymentGatewayAPIError,
    PaymentGatewayConfigError,
    PaymentGatewayConnectionError,
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0


class BasePaymentGateway(ABC):
    """Базовый класс для всех платёжных шлюзов."""

    def __init__(
        self,
        api_key: Optional[str],
        secret_key: Optional[str],
        return_url: str,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key
        self.secret_key = secret_key
        self.return_url = return_url
        self.base_url = base_url
        self.timeout = timeout

    def generate_signature(
        self, params: Dict[str, Any], secret_key: Optional[str] = None
    ) -> str:
        """Генерация HMAC-SHA256 подписи."""
        key = secret_key if secret_key is not None else self.secret_key
        if not key:
            logger.warning(f"{self.__class__.__name__}: secret key not configured")
            return ""

        filtered_params = {
            k: v for k, v in params.items() if v is not None and v != ""
        }
        signature_str = "&".join(
            f"{key}={value}" for key, value in sorted(filtered_params.items())
        )
        return hmac.new(
            key.encode(), signature_str.encode(), hashlib.sha256
        ).hexdigest()

    def verify_signature(
        self, params: Dict[str, Any], provided_signature: str
    ) -> bool:
        """Проверка HMAC подписи."""
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
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Выполнение асинхронного HTTP запроса с retry-логикой."""
        if not self.api_key:
            raise PaymentGatewayConfigError(
                f"{self.__class__.__name__}: API key not configured"
            )

        retry_count = 0
        last_exception: Optional[Exception] = None
        client_timeout = timeout or self.timeout

        while retry_count < MAX_RETRIES:
            try:
                async with httpx.AsyncClient(timeout=client_timeout) as client:
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
                delay = RETRY_DELAY * (2 ** (retry_count - 1))
                logger.warning(
                    f"{self.__class__.__name__} timeout "
                    f"(attempt {retry_count}/{MAX_RETRIES}, retry in {delay:.1f}s)"
                )
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(delay)

            except httpx.RequestError as e:
                retry_count += 1
                last_exception = e
                delay = RETRY_DELAY * (2 ** (retry_count - 1))
                logger.warning(
                    f"{self.__class__.__name__} request error: {e} "
                    f"(attempt {retry_count}/{MAX_RETRIES}, retry in {delay:.1f}s)"
                )
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(delay)

        logger.error(
            f"{self.__class__.__name__} request failed after {MAX_RETRIES} retries"
        )
        if isinstance(last_exception, httpx.TimeoutException):
            raise PaymentGatewayTimeoutError(
                f"{self.__class__.__name__}: request timeout after {MAX_RETRIES} retries"
            ) from last_exception
        raise PaymentGatewayConnectionError(
            f"{self.__class__.__name__}: connection error after {MAX_RETRIES} retries"
        ) from last_exception

    def _parse_error_response(
        self, error: httpx.HTTPStatusError
    ) -> Dict[str, Any]:
        """Парсинг ответа об ошибке от API."""
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
        """Подготовка базового payload для платежа."""
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
        """Проверка конфигурации шлюза."""
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
        """Создание платежа."""
        pass

    @abstractmethod
    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook уведомления."""
        pass
