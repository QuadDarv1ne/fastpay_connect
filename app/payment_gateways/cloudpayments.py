"""Интеграция с платёжной системой CloudPayments."""

import hashlib
import hmac
import logging
from typing import Any, Dict

from app.settings import settings
from app.payment_gateways.base import BasePaymentGateway

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """Исключение платёжного шлюза."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CloudPaymentsGateway(BasePaymentGateway):
    """CloudPayments платёжный шлюз.

    Документация: https://developers.cloudpayments.ru/
    """

    def __init__(self):
        super().__init__(
            api_key=settings.cloudpayments_api_key,
            secret_key=settings.cloudpayments_secret_key,
            return_url=settings.cloudpayments_return_url,
            base_url="https://api.cloudpayments.ru",
        )

    def generate_token(self, order_id: str) -> str:
        """Генерация токена для платежа.

        Создаёт HMAC-SHA256 подпись на основе order_id и секретного ключа.

        Args:
            order_id: ID заказа.

        Returns:
            HEX-строка токена.

        Raises:
            PaymentGatewayError: Если секретный ключ не настроен.
        """
        if not self.secret_key:
            raise PaymentGatewayError(
                "CloudPayments: secret key not configured",
                details={"order_id": order_id},
            )

        message = f"{order_id}{self.secret_key}"
        return hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_token(self, order_id: str, token: str) -> bool:
        """Проверка токена webhook.

        Args:
            order_id: ID заказа.
            token: Токен для проверки.

        Returns:
            True если токен валиден.

        Raises:
            PaymentGatewayError: Если секретный ключ не настроен.
        """
        if not self.secret_key:
            logger.warning(
                f"{self.__class__.__name__}: secret key not configured, "
                "skipping token verification"
            )
            raise PaymentGatewayError("Secret key not configured")

        expected_token = self.generate_token(order_id)
        return hmac.compare_digest(expected_token, token)

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через CloudPayments.

        Args:
            amount: Сумма платежа.
            description: Описание платежа.
            order_id: ID заказа.

        Returns:
            Ответ API с данными платежа.

        Raises:
            PaymentGatewayError: Ошибка создания платежа.
        """
        try:
            token = self.generate_token(order_id)
        except PaymentGatewayError:
            logger.error(f"{self.__class__.__name__}: cannot generate token")
            raise

        payload = self._prepare_payment_payload(
            amount=amount,
            description=description,
            order_id=order_id,
            extra_fields={
                "return_url": f"{self.return_url}?token={token}",
                "invoice_id": f"inv_{order_id}",
                "payment_type": "BANK_CARD",
            },
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        return await self._request(
            method="POST",
            url=f"{self.base_url}/payments",
            headers=headers,
            json_data=payload,
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], token: str
    ) -> Dict[str, str]:
        """Обработка webhook уведомления от CloudPayments.

        Args:
            payload: Тело webhook.
            token: Токен для проверки.

        Returns:
            Статус обработки webhook.
        """
        order_id = payload.get("order_id", "")

        try:
            if not self.verify_token(order_id, token):
                logger.warning(f"{self.__class__.__name__}: invalid webhook token")
                return {"status": "failed", "message": "Invalid token"}
        except PaymentGatewayError as e:
            logger.error(f"{self.__class__.__name__}: token verification error: {e}")
            return {"status": "failed", "message": "Token verification failed"}

        event = payload.get("event", "")
        logger.info(f"{self.__class__.__name__} webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.debug(f"{self.__class__.__name__}: ignored event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}


gateway = CloudPaymentsGateway()


async def create_payment(
    amount: float, description: str, order_id: str
) -> Dict[str, Any]:
    """Создание платежа через CloudPayments.

    Args:
        amount: Сумма платежа.
        description: Описание платежа.
        order_id: ID заказа.

    Returns:
        Ответ API с данными платежа.
    """
    return await gateway.create_payment(amount, description, order_id)


def verify_token(order_id: str, token: str) -> bool:
    """Проверка токена webhook.

    Args:
        order_id: ID заказа.
        token: Токен для проверки.

    Returns:
        True если токен валиден.
    """
    return gateway.verify_token(order_id, token)


async def handle_cloudpayments_webhook(
    payload: Dict[str, Any], token: str
) -> Dict[str, str]:
    """Обработка webhook уведомления от CloudPayments.

    Args:
        payload: Тело webhook.
        token: Токен для проверки.

    Returns:
        Статус обработки webhook.
    """
    return await gateway.handle_webhook(payload, token)
