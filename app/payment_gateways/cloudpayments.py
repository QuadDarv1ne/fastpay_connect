"""Интеграция с платёжной системой CloudPayments."""

import hashlib
import hmac
import logging
from typing import Any, Dict
from app.payment_gateways.base import BasePaymentGateway
from app.settings import settings

logger = logging.getLogger(__name__)


class CloudPaymentsGateway(BasePaymentGateway):
    """CloudPayments платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=settings.cloudpayments_api_key,
            secret_key=settings.secret_key,
            return_url=settings.cloudpayments_return_url,
            base_url="https://api.cloudpayments.ru",
        )

    def generate_token(self, order_id: str) -> str:
        """Генерация токена для платежа."""
        if not settings.secret_key:
            logger.warning("SECRET_KEY not configured")
            return ""

        message = f"{order_id}{settings.secret_key}"
        return hmac.new(
            settings.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    def verify_token(self, order_id: str, token: str) -> bool:
        """Проверка токена."""
        if not settings.secret_key:
            logger.warning("SECRET_KEY not configured, skipping token verification")
            return True

        expected_token = self.generate_token(order_id)
        return hmac.compare_digest(expected_token, token)

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через CloudPayments."""
        payload = self._prepare_payment_payload(amount, description, order_id)

        token = self.generate_token(order_id)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        cloudpayments_payload = {
            "amount": amount,
            "currency": "RUB",
            "description": description[:250],
            "order_id": order_id,
            "return_url": f"{self.return_url}?token={token}",
            "invoice_id": f"inv_{order_id}",
            "payment_type": "BANK_CARD",
        }

        return await self._request(
            "POST", f"{self.base_url}/payments", headers=headers, json_data=cloudpayments_payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], token: str
    ) -> Dict[str, str]:
        """Обработка webhook от CloudPayments."""
        order_id = payload.get("order_id", "")
        if not self.verify_token(order_id, token):
            logger.warning("Invalid CloudPayments webhook token")
            return {"status": "failed", "message": "Invalid token"}

        event = payload.get("event", "")
        logger.info(f"Processing CloudPayments webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored CloudPayments event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}


gateway = CloudPaymentsGateway()
create_payment = gateway.create_payment
verify_token = gateway.verify_token
handle_cloudpayments_webhook = gateway.handle_webhook
