"""Интеграция с платёжной системой Robokassa."""

import logging
from typing import Any, Dict

from app.settings import settings

from .base import BasePaymentGateway
from .exceptions import PaymentGatewayError

logger = logging.getLogger(__name__)


class RobokassaGateway(BasePaymentGateway):
    """Robokassa платёжный шлюз.

    Документация: https://docs.robokassa.ru/
    """

    def __init__(self):
        super().__init__(
            api_key=settings.robokassa_api_key,
            secret_key=settings.robokassa_secret_key,
            return_url=settings.robokassa_return_url,
            base_url="https://api.robokassa.ru",
        )

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через Robokassa.

        Args:
            amount: Сумма платежа.
            description: Описание платежа.
            order_id: ID заказа.

        Returns:
            Ответ API с данными платежа.

        Raises:
            PaymentGatewayError: Ошибка создания платежа.
        """
        payload = self._prepare_payment_payload(
            amount=amount,
            description=description,
            order_id=order_id,
            extra_fields={
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
            url=f"{self.base_url}/payment",
            headers=headers,
            json_data=payload,
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook уведомления от Robokassa.

        Args:
            payload: Тело webhook.
            signature: Подпись webhook.

        Returns:
            Статус обработки webhook.
        """
        if not self.verify_signature(payload, signature):
            logger.warning(f"{self.__class__.__name__}: invalid webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

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


gateway = RobokassaGateway()


async def create_payment(
    amount: float, description: str, order_id: str
) -> Dict[str, Any]:
    """Создание платежа через Robokassa.

    Args:
        amount: Сумма платежа.
        description: Описание платежа.
        order_id: ID заказа.

    Returns:
        Ответ API с данными платежа.
    """
    return await gateway.create_payment(amount, description, order_id)


def verify_signature(params: Dict[str, Any], signature: str) -> bool:
    """Проверка подписи webhook.

    Args:
        params: Параметры запроса.
        signature: Подпись.

    Returns:
        True если подпись валидна.
    """
    return gateway.verify_signature(params, signature)


async def handle_robokassa_webhook(
    payload: Dict[str, Any], signature: str
) -> Dict[str, str]:
    """Обработка webhook уведомления от Robokassa.

    Args:
        payload: Тело webhook.
        signature: Подпись webhook.

    Returns:
        Статус обработки webhook.
    """
    return await gateway.handle_webhook(payload, signature)
