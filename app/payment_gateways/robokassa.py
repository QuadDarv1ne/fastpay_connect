"""Интеграция с платёжной системой Robokassa."""

import logging
from typing import Any, Dict
from app.payment_gateways.base import BasePaymentGateway
from app.settings import settings

logger = logging.getLogger(__name__)


class RobokassaGateway(BasePaymentGateway):
    """Robokassa платёжный шлюз."""

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
        """Создание платежа через Robokassa."""
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
            "invoice_id": f"inv_{order_id}",
            "payment_type": "BANK_CARD",
        }

        return await self._request(
            "POST", f"{self.base_url}/payment", headers=headers, json_data=payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook от Robokassa."""
        if not self.verify_signature(payload, signature):
            logger.warning("Invalid Robokassa webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event = payload.get("event", "")
        logger.info(f"Processing Robokassa webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored Robokassa event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}


gateway = RobokassaGateway()


async def create_payment(amount: float, description: str, order_id: str) -> Dict[str, Any]:
    """Создание платежа через Robokassa."""
    return await gateway.create_payment(amount, description, order_id)


def verify_signature(params: Dict[str, Any], signature: str) -> bool:
    """Проверка подписи."""
    return gateway.verify_signature(params, signature)


async def handle_robokassa_webhook(payload: Dict[str, Any], signature: str) -> Dict[str, str]:
    """Обработка webhook от Robokassa."""
    return await gateway.handle_webhook(payload, signature)
