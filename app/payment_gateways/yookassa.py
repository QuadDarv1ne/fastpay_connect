"""Интеграция с платёжной системой YooKassa."""

import logging
from typing import Any, Dict, Optional
from app.payment_gateways.base import BasePaymentGateway
from app.config import YOOKASSA_API_KEY, YOOKASSA_SECRET_KEY, YOOKASSA_RETURN_URL

logger = logging.getLogger(__name__)


class YooKassaGateway(BasePaymentGateway):
    """YooKassa платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=YOOKASSA_API_KEY,
            secret_key=YOOKASSA_SECRET_KEY,
            return_url=YOOKASSA_RETURN_URL,
            base_url="https://api.yookassa.ru/v3",
        )

    def create_payment(
        self, amount: float, description: str, order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Создание платежа через YooKassa."""
        if not self.validate_config():
            return {"error": "Payment gateway not configured"}

        if amount <= 0:
            return {"error": "Invalid amount", "details": "Amount must be positive"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotence-Key": order_id or f"req_{hash(f'{amount}{description}')}",
        }

        payload = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "capture_mode": "AUTOMATIC",
            "confirmation": {
                "type": "redirect",
                "return_url": self.return_url,
            },
            "description": description[:250],
        }

        if order_id:
            payload["order_id"] = order_id

        return self._request(
            "POST", f"{self.base_url}/payment", headers=headers, json_data=payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook от YooKassa."""
        if not self.verify_signature(payload, signature):
            logger.warning("Invalid YooKassa webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event = payload.get("event", "")
        logger.info(f"Processing YooKassa webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.waiting_for_capture":
            return {"status": "processed", "message": "Payment waiting for capture"}
        else:
            logger.info(f"Ignored YooKassa event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}


gateway = YooKassaGateway()
create_payment = gateway.create_payment
verify_signature = gateway.verify_signature
handle_yookassa_webhook = gateway.handle_webhook
