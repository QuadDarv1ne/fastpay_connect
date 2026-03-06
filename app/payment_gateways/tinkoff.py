"""Интеграция с платёжной системой Tinkoff."""

import logging
from typing import Any, Dict
from app.payment_gateways.base import BasePaymentGateway
from app.settings import settings

logger = logging.getLogger(__name__)


class TinkoffGateway(BasePaymentGateway):
    """Tinkoff платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=settings.tinkoff_api_key,
            secret_key=settings.tinkoff_secret_key,
            return_url=settings.tinkoff_return_url,
            base_url="https://api.tinkoff.ru/v2",
        )

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через Tinkoff."""
        if not self.validate_config():
            return {"error": "Payment gateway not configured"}

        if amount <= 0:
            return {"error": "Invalid amount", "details": "Amount must be positive"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "amount": amount,
            "currency": "RUB",
            "description": description[:250],
            "order_id": order_id,
            "return_url": self.return_url,
            "payment_type": "BANK_CARD",
        }

        return await self._request(
            "POST", f"{self.base_url}/payments", headers=headers, json_data=payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook от Tinkoff."""
        if not self.verify_signature(payload, signature):
            logger.warning("Invalid Tinkoff webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event = payload.get("event", "")
        logger.info(f"Processing Tinkoff webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored Tinkoff event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}


gateway = TinkoffGateway()


async def create_payment(amount: float, description: str, order_id: str) -> Dict[str, Any]:
    """Создание платежа через Tinkoff."""
    return await gateway.create_payment(amount, description, order_id)


def verify_signature(params: Dict[str, Any], signature: str) -> bool:
    """Проверка подписи."""
    return gateway.verify_signature(params, signature)


async def handle_tinkoff_webhook(payload: Dict[str, Any], signature: str) -> Dict[str, str]:
    """Обработка webhook от Tinkoff."""
    return await gateway.handle_webhook(payload, signature)
