"""Базовый класс для платёжных шлюзов."""

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30.0


class BasePaymentGateway(ABC):
    """Базовый класс для всех платёжных шлюзов."""

    def __init__(
        self,
        api_key: Optional[str],
        secret_key: Optional[str],
        return_url: str,
        base_url: str,
    ) -> None:
        self.api_key = api_key
        self.secret_key = secret_key
        self.return_url = return_url
        self.base_url = base_url
        self._client = httpx.Client(timeout=REQUEST_TIMEOUT)

    def generate_signature(self, params: Dict[str, Any]) -> str:
        """Генерация HMAC-SHA256 подписи."""
        if not self.secret_key:
            logger.warning(f"{self.__class__.__name__}: secret key not configured")
            return ""

        signature_str = "&".join(
            f"{key}={value}" for key, value in sorted(params.items())
        )
        signature_str += f"&secret={self.secret_key}"
        return hmac.new(
            self.secret_key.encode(),
            signature_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(
        self, params: Dict[str, Any], provided_signature: str
    ) -> bool:
        """Проверка подписи."""
        if not self.secret_key:
            logger.warning(
                f"{self.__class__.__name__}: secret key not configured, "
                "skipping signature verification"
            )
            return True

        expected_signature = self.generate_signature(params)
        return hmac.compare_digest(expected_signature, provided_signature)

    def _request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса."""
        try:
            response = self._client.request(
                method,
                url,
                headers=headers,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"{self.__class__.__name__} HTTP error: {e}")
            try:
                error_detail = e.response.json()
            except Exception:
                error_detail = e.response.text if e.response.text else str(e)
            return {"error": "Payment request failed", "details": error_detail}

        except httpx.TimeoutException:
            logger.error(f"{self.__class__.__name__} request timeout")
            return {"error": "Payment gateway timeout"}

        except httpx.RequestError as e:
            logger.error(f"{self.__class__.__name__} request failed: {e}")
            return {"error": "Payment request failed", "details": str(e)}

    @abstractmethod
    def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа."""
        pass

    @abstractmethod
    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook."""
        pass

    def validate_config(self) -> bool:
        """Проверка конфигурации."""
        if not self.api_key:
            logger.error(f"{self.__class__.__name__}: API key not configured")
            return False
        if not self.secret_key:
            logger.warning(f"{self.__class__.__name__}: secret key not configured")
        return True

    def close(self) -> None:
        """Закрытие HTTP клиента."""
        self._client.close()
