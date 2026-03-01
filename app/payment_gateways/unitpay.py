"""Интеграция с платёжной системой UnitPay."""

import logging
from typing import Any, Dict
from app.payment_gateways.base import BasePaymentGateway
from app.config import UNITPAY_API_KEY, UNITPAY_SECRET_KEY, UNITPAY_RETURN_URL

logger = logging.getLogger(__name__)


class UnitPayGateway(BasePaymentGateway):
    """UnitPay платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=UNITPAY_API_KEY,
            secret_key=UNITPAY_SECRET_KEY,
            return_url=UNITPAY_RETURN_URL,
            base_url="https://unitpay.ru/api",
        )

    def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через UnitPay."""
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
        }

        return self._request(
            "POST", f"{self.base_url}/payment", headers=headers, json_data=payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook от UnitPay."""
        if not self.verify_signature(payload, signature):
            logger.warning("Invalid UnitPay webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event = payload.get("event", "")
        logger.info(f"Processing UnitPay webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored UnitPay event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}


gateway = UnitPayGateway()
create_payment = gateway.create_payment
verify_signature = gateway.verify_signature
handle_unitpay_webhook = gateway.handle_webhook
